#!/usr/bin/env python3
#
# Copyright (c) 2022      Nanook Consulting. All rights reserved
#

from server_upcalls import *
import os
import select
import subprocess

def main():
    try:
        dsched = PMIxTool()
    except:
        print("FAILED TO CREATE TOOL")
        exit(1)
    print("Testing version ", dsched.get_version())
    args = [{'key':PMIX_SERVER_SCHEDULER, 'value':'T', 'val_type':PMIX_BOOL},
            {'key':PMIX_CONNECT_TO_SYSTEM, 'value':'T', 'val_type':PMIX_BOOL},
            {'key':PMIX_TOOL_CONNECT_OPTIONAL, 'value':'T', 'val_type':PMIX_BOOL}]
    rc, myproc = dsched.init(args)
    print("Init", dsched.error_string(rc), myproc)
    map = {'clientconnected': clientconnected,
           'clientfinalized': clientfinalized,
           'fencenb': clientfence,
           'publish': clientpublish,
           'unpublish': clientunpublish,
           'lookup': clientlookup,
           'query': clientquery}
    my_result = dsched.set_server_module(map)

    print("Testing PMIx_tool_is_connected")
    rc = dsched.is_connected()
    print("Connected: ", rc)

    # Register a fabric
    rc,fab = dsched.fabric_register(None)
    print("Fabric registered: ", dsched.error_string(rc))

    pyq = [{'keys':[PMIX_QUERY_ALLOCATION], 'qualifiers':[]}]
    rc, pyresults = dsched.query(pyq)
    if rc != PMIX_SUCCESS and rc != PMIX_OPERATION_SUCCEEDED:
        print("QUERY TEST FAILED: ", dsched.error_string(rc))
    print("QUERY INFO RETURNED: ", pyresults)

    print("FINALIZING")
    dsched.finalize()

if __name__ == '__main__':
    global killer
    killer = GracefulKiller()
    main()
