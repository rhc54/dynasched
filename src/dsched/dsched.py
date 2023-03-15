#!/usr/bin/env python3
#
# Copyright (c) 2022      Nanook Consulting. All rights reserved
#

# system imports
import signal
import os
import threading
import socket

# project imports
from fifo import *
from pmix import *
global killer

terminate_event = threading.Event()

def handler(signum, frame):
    global terminate_event

    # activate the terminate event
    terminate_event.set()

def main():
    global terminate_event

    # get a scheduler object
    try:
        dsched = Scheduler()
    except Exception as error:
        print("EXCEPTION ON INIT")
        exit(1)
    print("Testing version ", dsched.get_version())

    # initialize the queues
    try:
        dsched.queue_init()
    except Exception as error:
        print("QUEUE INIT FAILED");
        exit(1)

    # if we attached to a DVM, then
    # query it for the available resources
    if self.dvmattached:
        try:
            dsched.query_allocation()
        except Exception as error:
            print("QUERY FAILED")
            dsched.finalize()
            exit(1)

    # setup the signal handler - we protect each
    # call in case a particular system doesn't
    # have the specified signal
    try:
        signal.signal(signal.SIGTERM, handler)
    except:
        pass
    try:
        signal.signal(signal.SIGINT, handler)
    except:
        pass
    try:
        signal.signal(signal.SIGABRT, handler)
    except:
        pass
    try:
        signal.signal(signal.SIGBREAK, handler)
    except:
        pass

    # wait for someone to shut us down
    flag = terminate_event.wait(timeout = None)

    print("FINALIZING")
    dsched.finalize()


class Scheduler(PMIxScheduler):
    def __init__(self):
        self.allocation = []
        self.topologies = []
        self.pid = os.getpid()
        self.dvmattached = False
        try:
            self.hname = socket.gethostname()
        except:
            self.hname = "UNKNOWN-HOST"
        self.fifo = None
        args = [
            {
                "key": PMIX_TOOL_NSPACE,
                "value": "DynaSched." + self.hname + '.' + str(self.pid),
                "val_type": PMIX_STRING,
            },
            {
                "key": PMIX_TOOL_RANK,
                "value": 0,
                "val_type": PMIX_PROC_RANK
            },
            {
                "key": PMIX_SERVER_SCHEDULER,
                "value": "T",
                "val_type": PMIX_BOOL
            },
            {
                "key": PMIX_CONNECT_TO_SYSTEM,
                "value": "T",
                "val_type": PMIX_BOOL
            },
            {
                "key": PMIX_TOOL_CONNECT_OPTIONAL,
                "value": "T",
                "val_type": PMIX_BOOL
            },
            {
                "key": PMIX_SERVER_REMOTE_CONNECTIONS,
                "value": "T",
                "val_type": PMIX_BOOL
            },
        ]
        rc, self.myproc = self.init(args)
        print("Init", self.error_string(rc), self.myproc)
        if PMIX_SUCCESS != rc:
            raise Exception('PMIx_tool_init failed: ', self.error_string(rc))
        # check if we found the system server - we assume
        # the system server is the DVM master controller
        self.dvmattached = self.is_connected()
        # set our server module entry points
        map = {
            'toolconnected': self.toolconnected,
            'query': self.clientquery,
            'registerevents': self.client_register_events,
            'allocate': self.allocate,
            'sessioncontrol': self.session_ctrl
        }
        try:
            rc = self.set_server_module(map)
        except Exception as error:
            print("FAILED TO MAP")
            return
        if PMIX_SUCCESS != rc:
            raise Exception('Setting server module failed: ', self.error_string(rc))

    def queue_init(self):
        try:
            self.fifo = FIFO()
            self.fifo.queue_init()
        except Exception as error:
            print('Unable to create FIFO instance')

    def query_allocation(self):
        pyq = [{"keys": [PMIX_QUERY_ALLOCATION], "qualifiers": []}]
        rc, pyresults = self.query(pyq)
        if rc != PMIX_SUCCESS and rc != PMIX_OPERATION_SUCCEEDED:
            raise Exception("QUERY ALLOCATION FAILED: ", self.error_string(rc))
        darray = pyresults[0]["value"]["array"]
        for d in darray:
            if PMIX_NODE_INFO.decode() == d["key"]:
                n = d["value"]["array"]
                self.allocation.append(n)
            elif (
                PMIX_HWLOC_XML_V2.decode() == d["key"]
                or PMIX_HWLOC_XML_V1.decode() == d["key"]
            ):
                t = d["value"]
                self.topologies.append(t)
            else:
                print("ALLOCATION CONTAINS UNEXPECTED DATA", d["key"])

    def toolconnected(self, args:dict is not None):
        if 'nspace' in args:
            ns = args['nspace']
        else:
            ns = "dschedtool"

        results = {'nspace': ns, 'rank': 0}
        return PMIX_OPERATION_SUCCEEDED, results

    def clientquery(self, args:dict is not None):
        print("SERVER: QUERY")
        # return a python info list of dictionaries
        info = {}
        results = []
        rc = PMIX_ERR_NOT_FOUND
        # find key we passed in to client, and
        # if it matches return fake PSET_NAME
        # since RM actually assigns this, we
        # just return arbitrary name if key is
        # found
        find_str = 'pmix.qry.psets'
        for q in args['queries']:
            for k in q['keys']:
                if k == find_str:
                    info = {'key': find_str, 'value': 'PSET_NAME', 'val_type': PMIX_STRING}
                    results.append(info)
                    rc = PMIX_SUCCESS
        return rc, results

    def client_register_events(self, args:dict is not None):
        print("CLIENT REGISTER EVENTS ", args['codes'])
        return PMIX_OPERATION_SUCCEEDED

    def allocate(self, args:dict is not None):
        # see what they want us to allocate
        print("ARGS", args)
        # see what we have
        print("RESOURCES", self.allocation)
        results = []
        return PMIX_ERR_NOT_SUPPORTED, results

    def session_ctrl(self, args:dict is not None):
        print("DSCHED SESSION CTRL")
        return PMIX_ERR_NOT_SUPPORTED


class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True

if __name__ == "__main__":
    global killer
    killer = GracefulKiller()
    main()
