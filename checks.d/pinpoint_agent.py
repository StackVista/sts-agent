# stdlib
import socket
import logging
import threading

from thrift.protocol import TCompactProtocol

from checks import AgentCheck
from checks import check_status

from checks.pinpoint.Trace.ttypes import *
from checks.pinpoint.Command.ttypes import *

log = logging.getLogger(__name__)

class SimpleTraceServer(AgentCheck):
#    isRunning = True
    isRunning = False

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.tcpport = instances[0]['tcpport']
        self.statport = instances[0]['statport']
        self.spanport = instances[0]['spanport']

    def run(self):
        if(not self.isRunning):
            t = threading.Thread(target=self.start_tornado)
            t.start()
            self._roll_up_instance_metadata()

        return [check_status.InstanceStatus(1, check_status.STATUS_OK)]

    def start_tornado(self):
        self.isRunning = True
        #self.tcpServer = SocketServer.TCPServer(('localhost', self.tcpport), TCPHandler)
        #self.tcpServer.serve_forever()
        #io_loop = ioloop.IOLoop.instance()
        #io_loop.start() #This Thread will block here till the stop is called!
        #logging.getLogger("tornado.access").setLevel(logging.ERROR)

        sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM);
        sock.bind(('localhost', self.spanport))
        while self.isRunning:
            try:
                data, addr = sock.recvfrom(50000)
                header = data[:4]
                body = data[4:]
                self.handleUdpSpan(header,body,addr)
            except Exception as e:
                log.debug(e)

        log.info("Simple trace server stopped")

    def stop(self):
        #ioloop = tornado.ioloop.IOLoop.instance()
        #ioloop.add_callback(ioloop.stop)
        #self.tcpServer.shutdown()
        self.isRunning = False
        log.info("Asked Tornado to exit")

    def check(self, instance):
        log.debug("Check loop, nothing to do here. Running as httpserver.")

    def handleUdpSpan(self, header, body, addr):
        try:
            type = ord(header[3]) + (int(ord(header[2])) << 8)
            print "type: %s" % type
            if(type == 40):
                transportIn = TTransport.TMemoryBuffer(body)
                protocolIn = TCompactProtocol.TCompactProtocol(transportIn)
                tSpan = TSpan()
                tSpan.read(protocolIn)
                #print tSpan
                fromIdentifier = tSpan.endPoint.replace(":","_")

                log.info("from: " +fromIdentifier)
                if(tSpan.spanEventList[0].destinationId != None):
                    toIdentifier = tSpan.spanEventList[0].destinationId.replace(":", "_")
                    log.info(toIdentifier)

                self.component({"type": "notYetSet", "url": "http://localhost/"}, fromIdentifier , {"name": fromIdentifier },{ "identifier": fromIdentifier } )
                #self.component({"type": "notYetSet", "url": "http://localhost/"}, toIdentifier, {"name": fromIdentifier}, { "identifier": toIdentifier })
                #self.relation({"type": "traceAgent", "url": "http://localhost/"}, fromIdentifier, toIdentifier, "calls", { "identifier": fromIdentifier +"_"+toIdentifier })
                #tags = []
                #tags.append("from" + ":" + fromIdentifier)
                #tags.append("to" + ":" + toIdentifier)
                #self.gauge("responseTime", tSpan.elapsed, tags)
            if(type == 70):
                transportIn = TTransport.TMemoryBuffer(body)
                protocolIn = TCompactProtocol.TCompactProtocol(transportIn)
                tSpanChunk = TSpanChunk()
                tSpanChunk.read(protocolIn)
                print tSpanChunk
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print "Exception: " + e.message
            exc_traceback.print_exc()

