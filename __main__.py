from twisted.internet import reactor, defer
from twisted.internet.defer import setDebugging

from fxdevtools.protocol import connect

setDebugging(True)

def done(packet):
  print packet

def connected(client):
  d = client.root.echo("hello")
  d.addCallback(done)

d = connect()
d.addCallback(connected)

def errback(e):
  print "ERRBACK: %s" % (e,)
d.addErrback(errback)

reactor.run()
