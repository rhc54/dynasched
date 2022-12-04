#!/usr/bin/env python3
#
# Copyright (c) 2022      Nanook Consulting. All rights reserved
#

from server_upcalls import *
from pmix import PMIxTool

allocation = []
topologies = []


def main():
    global allocation
    global topologies
    try:
        dsched = PMIxTool()
    except NameError:
        print("Class PMIxTool is not defined")
        exit(1)
    print("Testing version ", dsched.get_version())
    args = [{'key': PMIX_SERVER_SCHEDULER,
             'value': 'T', 'val_type': PMIX_BOOL},
            {'key': PMIX_CONNECT_TO_SYSTEM,
             'value': 'T', 'val_type': PMIX_BOOL},
            {'key': PMIX_TOOL_CONNECT_OPTIONAL,
             'value': 'T', 'val_type': PMIX_BOOL}]
    rc, myproc = dsched.init(args)
    print("Init", dsched.error_string(rc), myproc)
    map = {'clientconnected': clientconnected,
           'clientfinalized': clientfinalized,
           'fencenb': clientfence,
           'publish': clientpublish,
           'unpublish': clientunpublish,
           'lookup': clientlookup,
           'query': clientquery}
    rc = dsched.set_server_module(map)
    if PMIX_SUCCESS != rc:
        print("Failed to set server module")
        exit(1)

    rc = dsched.is_connected()
    if not rc:
        print("Not connected")
        exit(1)

    pyq = [{'keys': [PMIX_QUERY_ALLOCATION], 'qualifiers':[]}]
    rc, pyresults = dsched.query(pyq)
    if rc != PMIX_SUCCESS and rc != PMIX_OPERATION_SUCCEEDED:
        print("QUERY ALLOCATION FAILED: ", dsched.error_string(rc))
        exit(1)
    darray = pyresults[0]['value']['array']
    for d in darray:
        if PMIX_NODE_INFO.decode() == d['key']:
            n = d['value']['array']
            allocation.append(n)
        elif (PMIX_HWLOC_XML_V2.decode() == d['key'] or
              PMIX_HWLOC_XML_V1.decode() == d['key']):
            t = d['value']
            topologies.append(t)
        else:
            print("ALLOCATION CONTAINS UNEXPECTED DATA", d['key'])

    print("ALLOCATION", allocation)
    print("TOPOLOGIES", topologies)
    print("FINALIZING")
    dsched.finalize()


if __name__ == '__main__':
    global killer
    killer = GracefulKiller()
    main()
