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
            methodParts = parts[2].split(',')
            # 0 full calss: java.lang.ref.ReferenceQueue
            # 1 function: remove
            # 2 line: 143
            identifierParts = methodParts[0].split('.')
            tags.append("identifier" + ":" + methodParts[0])

            clazz = identifierParts[identifierParts.__len__() - 1]
            tags.append("class" + ":" + clazz)

            package = '.'.join(identifierParts[0:(identifierParts.__len__() - 1)])
            tags.append("package" + ":" + package)

            tags.append("line" + ":" + methodParts[2])

            self.agentCheck.gauge(parts[1] + "_count", parts[3], tags)
            self.agentCheck.gauge(parts[1] + "_value", parts[4], tags)
            #    elif (parts[0] == 'C'):
            #        print("C")

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
        log.info("Starting Torando")
        tornado.ioloop.IOLoop.instance().start()
        log.info("Tornado finished")

    def stop(self):
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.add_callback(ioloop.stop)
        log.info("Asked Tornado to exit")

    def check(self, instance):
        log.debug("Check loop, nothing to do here. Running as httpserver.")
