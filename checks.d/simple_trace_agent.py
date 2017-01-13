# stdlib
import cPickle as pickle
import logging
import struct
import time

# 3p
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler
from tornado.web import Application
from tornado.httpserver import HTTPServer
import tornado.gen

# project
from checks import AgentCheck
import threading
from checks import check_status

log = logging.getLogger(__name__)

class SimpleTraceHandler(RequestHandler):
    def initialize(self, agentCheck):
        self.agentCheck = agentCheck

    def post(args):
        for line in args.request.body.splitlines(True):
            args.handle_line(line)

        args.set_header("Content-Type", "text/plain")
        args.write("OK")
        args.finish()

    def handle_line(self, line):
        line = line.rstrip()  # remove newline from line
        parts = line.split('|')
        # 0 ['M',
        # 1 'cpuTimeUsedMs',
        # 2 'java.lang.ref.ReferenceQueue,remove,143',
        # 3 '10',     count
        # 4 '0.0\n']  cpu seconds
        tags = []
        if (parts[0] == 'M'):
            identificationParts = self.getIdentificationPartsFromIdentification(parts[2])

            tags.append("identifier" + ":" + identificationParts["identifier"])
            tags.append("class" + ":" + identificationParts["clazz"])
            tags.append("package" + ":" + identificationParts["package"])
            tags.append("line" + ":" + identificationParts["line"])

            self.agentCheck.gauge(parts[1] + "_count", parts[3], tags)
            self.agentCheck.gauge(parts[1] + "_value", parts[4], tags)
        elif (parts[0] == 'C'):
            #C|sun.nio.ch.KQueueArrayWrapper,poll,198
            identificationParts = self.getIdentificationPartsFromIdentification(parts[1])
            self.agentCheck.component({ "type": "traceAgent", "url": "http://localhost/" }, identificationParts["identifier"], "methodCall", identificationParts)
        elif (parts[0] == 'R'):
            # R|sun.nio.ch.KQueueArrayWrapper,poll,198|isCalledBy|sun.nio.ch.KQueueSelectorImpl,doSelect,103
            # 1 sun.nio.ch.KQueueArrayWrapper,poll,198
            # 2 isCalledBy
            # 3 sun.nio.ch.KQueueSelectorImpl,doSelect,103
            self.agentCheck.relation({ "type": "traceAgent", "url": "http://localhost/" }, parts[1], parts[3], parts[2], {})

    def getIdentificationPartsFromIdentification(self,identification):
        # Example: 'java.lang.ref.ReferenceQueue,remove,143',

        identifier = identification

        methodParts = identification.split(',')
        # 0 full class: java.lang.ref.ReferenceQueue
        # 1 function: remove
        # 2 line: 143
        identifierParts =  methodParts[0].split('.')

        clazz = identifierParts[identifierParts.__len__() - 1]
        package = '.'.join(identifierParts[0:(identifierParts.__len__() - 1)])
        line = methodParts[2]
        return {
            "identifier": identifier,
            "clazz": clazz,
            "line": line,
            "package": package
        };

class SimpleTraceServer(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.port = instances[0]['port']

    def run(self):
        t = threading.Thread(target=self.start_tornado)
        t.start()
        self._roll_up_instance_metadata()
        return [check_status.InstanceStatus(1, check_status.STATUS_OK)]

    def start_tornado(self):
        application = Application([
            (r"/*", SimpleTraceHandler, {"agentCheck" : self}),
        ])
        log.info("Starting simple trace server on port %d" % self.port)
        application.listen(self.port)
        tornado.ioloop.IOLoop.instance().start() #This Thread will block here till the stop is called!
        log.info("Simple trace server on port %s stopped" % self.port)

    def stop(self):
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.add_callback(ioloop.stop)
        log.info("Asked Tornado to exit")

    def check(self, instance):
        log.debug("Check loop, nothing to do here. Running as httpserver.")
