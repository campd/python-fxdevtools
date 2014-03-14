import asyncore
import socket
from twisted.internet import defer
from events import Event
import json

protocol_map = {}

class FirefoxDevtoolsProtocol(asyncore.dispatcher):
    def __init__(self):
        asyncore.dispatcher.__init__(self, map=protocol_map)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.recvBuffer = ""
        self.sendBuffer = ""
        self.onConnect = Event()
        self.onPacket = Event()

    def handle_connect(self):
        self.onConnect.emit()
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        self.recvBuffer += self.recv(8192)

        try:
            length, remaining = self.recvBuffer.split(":", 1)
        except ValueError:
            return

        length = int(length)
        if len(remaining) < length:
            return

        packet = remaining[0:length]
        self.recvBuffer = remaining[length:]
        print "got " + packet
        self.onPacket.emit(json.loads(packet))

    def writable(self):
        return len(self.sendBuffer) > 0

    def handle_write(self):
        sent = self.send(self.sendBuffer)
        self.sendBuffer = self.sendBuffer[sent:]

    def sendPacket(self, packet):
        data = json.dumps(packet)
        print "sending " + data
        self.sendBuffer += str(len(data)) + ":" + data

def connect(hostname="localhost", port=6080):
    d = defer.Deferred()
    protocol = FirefoxDevtoolsProtocol()
    protocol.onConnect += lambda: d.callback(protocol)
    protocol.connect((hostname, port))
    return d

def loop():
    from async import MainLoop
    l = MainLoop(protocol_map)
    l.start()
    l.block()

