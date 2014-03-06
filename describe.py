from twisted.internet import reactor, defer
from fxdevtools.protocol import connect

import pprint
import sys

@defer.deferredGenerator
def connected(client):
  d = defer.waitForDeferred(client.root.actorDescriptions())
  yield d
  data = d.getResult()

  print "\"\"\"Pre-prepared actor descriptions for the protocol, for when autodiscovery fails.\"\"\""
  print ""
  print "actorDescriptions = %s" % (pprint.pformat(data),)
  reactor.stop()

d = connect()
d.addCallback(connected)

def errback(e):
  sys.stderr.write("ERROR: %s" % (e,))

d.addErrback(errback)

reactor.run()

