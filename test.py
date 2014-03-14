from twisted.internet import defer
from twisted.internet.defer import setDebugging

from fxdevtools.protocol import connect
from fxdevtools import fxconnection
import json

setDebugging(True)

def done(packet):
    print packet

def tabListChanged():
    print "tab list changed!"

@defer.deferredGenerator
def connected(client):
    client.root.onTabListChanged += tabListChanged

    d = defer.waitForDeferred(client.root.echo("hello"))
    yield d
    print "echo result: " + d.getResult()
    d = defer.waitForDeferred(client.root.listTabs())
    yield d

    tabs = d.getResult()

    d = defer.waitForDeferred(tabs["tabs"][tabs["selected"]].inspector.getWalker())
    yield d
    print "walker: %s" % (d.getResult(),)


d = connect()
d.addCallback(connected)

def errback(e):
    print "ERROR: %s" % (e,)
d.addErrback(errback)

fxconnection.loop()

