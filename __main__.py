from twisted.internet import reactor, defer
from twisted.internet.defer import setDebugging

from fxdevtools.protocol import connect
import json

setDebugging(True)

def done(packet):
  print packet

@defer.deferredGenerator
def connected(client):
  d = defer.waitForDeferred(client.root.echo("hello"))
  yield d
  print "echo result: " + d.getResult()

d = connect()
d.addCallback(connected)

def errback(e):
  print "ERRBACK: %s" % (e,)
d.addErrback(errback)

reactor.run()
