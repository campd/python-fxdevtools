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
        self.recv_buffer = ""
        self.send_buffer = ""
        self.on_connect = Event()
        self.on_packet = Event()

    def handle_connect(self):
        self.on_connect.emit()
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        self.recv_buffer += self.recv(8192)

        try:
            length, remaining = self.recv_buffer.split(":", 1)
        except ValueError:
            return

        length = int(length)
        if len(remaining) < length:
            return

        packet = remaining[0:length]
        self.recv_buffer = remaining[length:]
        print "got " + packet
        self.on_packet.emit(json.loads(packet))

    def writable(self):
        return len(self.send_buffer) > 0

    def handle_write(self):
        sent = self.send(self.send_buffer)
        self.send_buffer = self.send_buffer[sent:]

    def send_packet(self, packet):
        data = json.dumps(packet)
        print "sending " + data
        self.send_buffer += str(len(data)) + ":" + data

def connect(hostname="localhost", port=6080):
    d = defer.Deferred()
    protocol = FirefoxDevtoolsProtocol()
    protocol.on_connect += lambda: d.callback(protocol)
    protocol.connect((hostname, port))
    return d

def loop():
    from async import MainLoop
    l = MainLoop(protocol_map)
    l.start()
    l.block()

