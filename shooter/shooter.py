#!/usr/bin/python

import string
import sys, os
import subprocess
import tempfile
import json

cwd = '/'.join(__file__.split('/')[:-1])
sys.path.insert(0, os.path.join(cwd, '../'))

# U1 `/node/`
# U2 `/submission`
# U3 `/submission/<submission_id>`
# U4 `/submission/<submission_id>/finalize`
# U5 `/submission/<submission_id>/upload_file`

# R1 `/receiver/<string t_id>/overview`
# R2 `/receiver/<string module_name><string t_id>/module`

# A1 `/admin/node/`
# A2 `/admin/contexts/`
# A3 `/admin/receivers/<context_$ID>/`
# A4 `/admin/modules/<context_$ID>/<string module_type>/`

# T1 `/tip/<string auth t_id>`
# T2 `/tip/<uniq_Tip_$ID>/comment`
# T3 `/tip/<uniq_Tip_$ID>/update_file`
# T4 `/tip/<string t_id>/finalize_update`
# T5 `/tip/<string t_id>/download_material`
# T6 `/tip/<string t_id>/pertinence`

schema = {
     '/node': 'GET' , #U1
     '/submission': 'GET', #U2
     '/submission/@SID@/status': 'GET', #U3
     '/submission/@SID@/status': 'POST', #U3
     '/submission/@SID@/finalize': 'POST', #U4
        # file not yet 
     '/tip/@TIP@': 'GET', #T1
     '/tip/@TIP@' : 'POST', #T1
     '/tip/@TIP@/comment': 'POST', #T2
        # "T3" :['/tip/'+tID()+'/files', ['GET','POST','PUT','DELETE']],
     '/tip/@TIP@/finalize': 'POST', #T4
     '/tip/@TIP@/download': 'GET',  #T5
        # /download/ need a folderID insted of Tip ? XXX
     '/tip/@TIP@/pertinence': 'POST', #T6
     '/receiver/@TIP@': 'GET', #R1
     '/receiver/@TIP@/notification': 'GET', #R2
        # /notification or /delivery
     '/receiver/@TIP@/notification': 'POST', #R2
     '/receiver/@TIP@/notification': 'PUT', #R2
     '/receiver/@TIP@/notification': 'DELETE', #R2
        # admin not yet supported, because who knows..
     '/admin/node':'GET', #A1
     '/admin/node':'POST', #A1
     '/admin/contexts/@CID@': 'GET', #A2
     '/admin/contexts/@CID@': 'POST', #A2
     '/admin/contexts/@CID@': 'PUT', #A2
     '/admin/contexts/@CID@': 'DELETE', #A2
     '/admin/receivers/@CID@': 'GET', #A3
     '/admin/receivers/@CID@': 'POST', #A3
     '/admin/receivers/@CID@': 'DELETE', #A3
     '/admin/receivers/@CID@': 'PUT', #A3
     '/admin/modules/@CID@/notification': 'GET', #A4
     '/admin/modules/@CID@/notification': 'POST' #A4
}

URTA = {
    'U1_GET':'GET_/node', #U1
    'U2_GET':'GET_/submission',#U2
    'U3_GET':'GET_/submission/@SID@/status', #U3
    'U3_POST':'POST_/submission/@SID@/status', #U3
    'U4_POST':'POST_/submission/@SID@/finalize', #U4
    # file not yet
    'T1_GET':'GET_/tip/@TIP@', #T1
    'T1_POST':'POST_/tip/@TIP@', #T1
    'T2_POST':'POST_/tip/@TIP@/comment', #T2
    # "T3" :['/tip/'+tID()+'/files', ['GET','POST','PUT','DELETE']],
    'T4_POST':'POST_/tip/@TIP@/finalize', #T4
    'T5_GET':'GET_/tip/@TIP@/download',  #T5
    # /download/ need a folderID insted of Tip ? XXX
    'T6_POST':'POST_/tip/@TIP@/pertinence', #T6
    'R1_GET':'GET_/receiver/@TIP@', #R1
    'R2_GET':'GET_/receiver/@TIP@/notification', #R2
    # /notification or /delivery
    'R2_POST':'POST_/receiver/@TIP@/notification', #R2
    'R2_PUT':'PUT_/receiver/@TIP@/notification', #R2
    'R2_DELETE':'DELETE_/receiver/@TIP@/notification', #R2
    # admin not yet supported, because who knows..
    'A1_GET':'GET_/admin/node', #A1
    'A1_POST':'POST_/admin/node', #A1
    'A2_GET':'GET_/admin/contexts/@CID@', #A2
    'A2_POST':'POST_/admin/contexts/@CID@', #A2
    'A2_PUT':'PUT_/admin/contexts/@CID@', #A2
    'A2_DELETE':'DELETE_/admin/contexts/@CID@', #A2
    'A3_GET':'GET_/admin/receivers/@CID@', #A3
    'A3_POST':'POST_/admin/receivers/@CID@', #A3
    'A3_DELETE':'DELETE_/admin/receivers/@CID@', #A3
    'A3_PUT':'PUT_/admin/receivers/@CID@', #A3
    'A4_GET':'GET_/admin/modules/@CID@/notification', #A4
    'A4_POST':'POST_/admin/modules/@CID@/notification' #A4
}

baseurl = "http://127.0.0.1:8082"



def do_httpie(method, url, request_list):
    """
    @param url:
    @param method:
    @param request_list: should not be present, is the value in HTTPie format. ref search_jsonfile
    @return: the dict of the received data, or null
    """
    (tstderr, errfname) = tempfile.mkstemp(suffix="_shootErr")

    if checkOpt('verbose'):
        tstdout = sys.stdout
        outfname = None
    else:
        (tstdout, outfname) = tempfile.mkstemp(suffix="_shoOut")

    # TEMP
    tstderr = sys.stderr
    defurl = baseurl + url

    command_array = ["http", method, defurl ]

    if request_list is not None:
        for request_element in request_list:
            command_array.append(request_element)

    if checkOpt('verbose'):
        command_array.append('--verbose')

    try:
        subprocess.check_call(command_array, stderr=tstderr, stdout=tstdout)
    except subprocess.CalledProcessError:
        print "invalid execution of httpie!"
        print "check the file", errfname
        quit(1)

    if outfname == None:
        # verbose option, do not permit output parsing,
        # good exit code here
        quit(0)

    os.close(tstdout)
    with open(outfname, 'r') as outfstream:
        readed = outfstream.read()

    if len(readed) > 5:
        return json.loads(readed)

    # no output body!, good exit code
    quit(0)



def checkOpt(option):

    if option in sys.argv:
        return True

def getOpt(seekd):

    if seekd in sys.argv:

        retarg = sys.argv[sys.argv.index(seekd) + 1]

        # tip, sid, cid has all the (t|s|c)_(\w+) regexp
        if retarg[1] != '_':
            print "invalied indexed", seekd,"! taken", retarg
            quit(1)

        return retarg

    return None

def fix_varline(inputline):

    for var,argopt in { '@TIP@': 'tip', '@CID@': 'cid', '@SID@':'sid' }.iteritems():
        if inputline.find(var) > 0:
            # it's passed in command line 'tip' 'cid' 'sid'
            user_parm = getOpt(argopt)

            if user_parm is None:
                print "processed line has a variable(", inputline, "), you need to specify", argopt
                quit(1)

            linesplit = inputline.split(var)
            return (linesplit[0] + user_parm + linesplit[1])

    return inputline

# simple utility used in the spelunking_int_*
def getMethIf(argv_index):
    if len(sys.argv) > argv_index:
        if sys.argv[argv_index].upper() in ['GET', 'POST', 'DELETE', 'PUT' ]:
            return sys.argv[argv_index].upper()

    return None

def spelunking_into_schema():

    requested_rest = []

    for rest,method in schema.iteritems():
        if rest.find(sys.argv[1]) > 0:
            requested_rest.append(method + '_' + rest)

    if len(requested_rest) == 0:
        print "not found pattern", sys.argv[1], "in rest list"
        quit(1)

    meth = getMethIf(2)
    if meth:
        unfiltered_rest = requested_rest
        requested_rest = []
        for meth_rest in unfiltered_rest:
            if meth_rest.find(meth) == 0:
                requested_rest.append(meth_rest)

    if len(requested_rest) != 1:
        print "expected only one selected REST, your query match", len(requested_rest)
        for rest in requested_rest:
            print "\t", rest
        quit(1)

    # (url, meth, aggregate)
    splitted_aggr = requested_rest[0].split('_')
    return (splitted_aggr[1], splitted_aggr[0], requested_rest[0])

def spelunking_into_URTA():

    meth = getMethIf(2)
    if not meth:
        meth = 'GET'

    assembled_key = sys.argv[1] + "_" + meth

    if URTA.has_key(assembled_key):
        aggregate = URTA[assembled_key]
    else:
        print "The U|R|T|A code + method requested is invalid", assembled_key
        quit(1)

    # (url, meth, aggregate)
    return (aggregate.split("_")[1], meth, aggregate)



def search_jsonfile(searched_rest):

    fileconv = string.replace(string.replace(searched_rest, '@', ''), '/', '_')
    fname = 'jsonfiles/' + fileconv
    if os.access(fname, os.R_OK):
        retlist = [] # it's a list because every line is a different parm in httpie
        with open(fname, 'r') as f:
            while True:

                line = string.strip(f.readline(), "\n")

                if len(line) <= 1:
                    return retlist

                if line[0] == '#':
                    continue

                expanded_line = fix_varline(line)
                retlist.append(expanded_line)
    else:
        print "input JSON file is missing, searched:", fname
        quit(1)


def outputOptionsApply(theDict):

    if type(theDict) != type({}):
        return False

    for uarg in sys.argv:
        if uarg.startswith('print-'):
            choosen = uarg[6:]

            if theDict.has_key(choosen):
                print theDict[choosen]
                return True

            for key, value in theDict.iteritems():
                # it's a list ?
                if type(value) == type([]):
                    for element in theDict.get(key):
                        if outputOptionsApply(element):
                            break

                # it's a dict ?
                if type(value) == type({}):
                    if outputOptionsApply(value):
                        break


    #print "requested key", choosen, "missing from the received data"

# http://www.youtube.com/watch?v=DaN4LrieCjo - show me your labi-a!
if __name__ == '__main__':

    if len(sys.argv) < 2:
        print sys.argv[0], "[portion of REST]|URTA code", "<method>", "<sid>|<cid>|<tip>"
        quit(1)

    # handle 'shooter.py U1' and 'shooter.py U1 POST'
    if len(sys.argv[1]) == 2:
        (url, meth, aggregate) = spelunking_into_URTA()
    else:
    # handle option 'shooter.py admin/module POST'
        (url, meth, aggregate) = spelunking_into_schema()

    if meth != 'GET':
        request_list = search_jsonfile(aggregate)
    else:
        request_list = None

    url_fixed = fix_varline(url)
    received_data = do_httpie(meth, url_fixed, request_list)

    # If we're received data, mean that 'verbose' option was not present
    outputOptionsApply(received_data)
    quit(0)

