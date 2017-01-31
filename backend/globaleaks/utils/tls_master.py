import json
import multiprocessing
import os
import signal
import socket
import sys
import signal

from sys import executable

from twisted.internet import reactor, task, protocol, defer
from twisted.internet.defer import inlineCallbacks

from globaleaks.models.config import PrivateFactory
from globaleaks.orm import transact
from globaleaks.utils import sock as socket_util
from globaleaks.utils import ssl
from globaleaks.utils.utility import log, datetime_now, datetime_to_ISO8601


class TLSProcProtocol(protocol.ProcessProtocol):
    def __init__(self, supervisor, bin_path, cfg, cfg_fd=42):
        self.supervisor = supervisor
        self.cfg = json.dumps(cfg)
        self.cfg_fd = cfg_fd

        fd_map = {0:0, 1:1, 2:2}
        fd_map[cfg_fd] = 'w'

        tls_socket_fd = cfg['tls_socket_fd']
        fd_map[tls_socket_fd] = tls_socket_fd

        log.debug('subproc fd_map:%s, tls_socket_fd:%d, os_fstat=%s' % (fd_map,
                  tls_socket_fd, os.fstat(tls_socket_fd)))

        reactor.spawnProcess(self, executable, [executable, bin_path], childFDs=fd_map, env=os.environ)

    def connectionMade(self):
        log.info("Parent writing to: %d" % self.cfg_fd)
        self.transport.writeToChild(self.cfg_fd, self.cfg)
        self.transport.closeChildFD(self.cfg_fd)
        # TODO self.cfg has a copy of TLS priv_key
        del self.cfg

    def processEnded(self, reason):
        self.supervisor.handle_worker_death(self, reason)

    def __repr__(self):
        return "<TLSProcProtocol: %s:%s>" % (id(self), self.transport)


class ProcessSupervisor(object):
    '''
    A Supervisor for all subprocesses that the main globaleaks process can launch
    '''

    # TODO One child process death every 5 minutes is acceptable. Four every minute
    # is excessive.
    MAX_MORTALITY_RATE = 4 # 0.2

    def __init__(self, net_sockets, proxy_ip, proxy_port, bin_dir):
        log.info("Starting process monitor")

        self.shutting_down = False

        self.start_time = datetime_now()
        self.tls_process_pool = []
        self.tls_process_state = {
            'deaths': 0,
            'last_death': datetime_now(),
            'target_proc_num': multiprocessing.cpu_count(),
        }

        self.bin_path = os.path.abspath(os.path.join(bin_dir, 'gl-tls-worker.py'))

        self.tls_cfg = {
          'proxy_ip': proxy_ip,
          'proxy_port': proxy_port,
          # TODO bind on all sockets
          'tls_socket_fd': net_sockets[0].fileno(),
        }

    @transact
    def maybe_launch_https_workers(self, store):
        self.db_maybe_launch_https_workers(store)

    def db_maybe_launch_https_workers(self, store):
        privFact = PrivateFactory(store)

        db_cfg = ssl.load_db_cfg(store)
        self.tls_cfg.update(db_cfg)

        on = privFact.get_val('https_enabled')

        if on:
            log.info("Decided to launch https workers")
            self.launch_https_workers()
        else:
            log.info("Not launching https workers")

    def launch_https_workers(self):
        for i in range(self.tls_process_state['target_proc_num']):
            self.launch_worker()

    def launch_worker(self):
        pp = TLSProcProtocol(self, self.bin_path, self.tls_cfg)
        self.tls_process_pool.append(pp)
        log.info('Launched: %s' % (pp))

    def handle_worker_death(self, pp, reason):
        '''
        handle_worker_death accounts the worker's death and creates a new process
        in its place if the reason for death is reasonable and we haven't
        restarted the child an unreasonable number of times.
        '''
        log.info("Subprocess: %s exited with: %s" % (pp, reason))
        mortatility_rate = self.account_death()
        self.tls_process_pool.pop(self.tls_process_pool.index(pp))
        del pp

        if (self.should_spawn_child(mortatility_rate)):
            log.info('Decided to respawn a child')
            self.launch_worker()
        elif self.last_one_out():
            self.shutting_down = False
            log.err("Supervisor has turned off all children")
        else:
            log.err("Not relaunching child process")

    def should_spawn_child(self, mort_rate):
        # TODO add logging based on condition hit

        if self.shutting_down:
            return False

        nrml_deaths = 3*self.tls_process_state['target_proc_num']

        max_deaths = nrml_deaths*50

        num_deaths = self.tls_process_state['deaths']

        return len(self.tls_process_pool) < self.tls_process_state['target_proc_num'] and \
               num_deaths < max_deaths and \
               (mort_rate < self.MAX_MORTALITY_RATE or num_deaths < nrml_deaths)

    def last_one_out(self):
        '''
        last_one_out captures the condition of the last shutdown process before
        the process supervisor has closed all children.
        '''
        return self.shutting_down and len(self.tls_process_pool) == 0

    def calc_mort_rate(self):
        d = self.tls_process_state['deaths']
        window = (datetime_now() - self.start_time).total_seconds()
        r = d / (window / 60.0) # deaths per minute
        log.debug('process death accountant: r=%3f, d=%2f, window=%2f' % (r, d, window))
        return r

    def account_death(self):
        self.tls_process_state['deaths'] += 1
        r = self.calc_mort_rate()
        return r

    def is_running(self):
        return len(self.tls_process_pool) > 0

    def get_status(self):
        s = {
            'msg': '',
            'timestamp': datetime_to_ISO8601(datetime_now()),
            'type': 'info'
        }
        if self.is_running():
            r = self.calc_mort_rate()
            if not self.should_spawn_child(r):
                m = "The supervisor is no longer trying to spawn children. r=%3f" % r
            else:
                m = "Processes are serving https"
        else:
            m = "Nothing is being served"
        s['msg'] = m
        return s

    def shutdown(self):
        self.shutting_down = True

        log.info('Starting shutdown of %d children' % len(self.tls_process_pool))
        for pp in self.tls_process_pool:
            try:
                os.kill(pp.transport.pid, signal.SIGUSR1)
                os.kill(pp.transport.pid, signal.SIGINT)
            except OSError as e:
                log.info('Tried to signal: %d got: %s' % (pp.transport.pid, e))
