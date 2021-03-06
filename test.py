from twisted.internet import defer
from twisted.internet.defer import setDebugging

from fxdevtools.protocol import connect
from fxdevtools import fxconnection
import json

setDebugging(True)

def done(packet):
    print packet

def tab_list_changed():
    print "tab list changed!"

@defer.deferredGenerator
def connected(client):
    client.root.on_tab_list_changed += tab_list_changed

    d = defer.waitForDeferred(client.root.echo("hello"))
    yield d
    print "echo result: " + d.getResult()
    d = defer.waitForDeferred(client.root.list_tabs())
    yield d

    tabs = d.getResult()

    d = defer.waitForDeferred(tabs["tabs"][tabs["selected"]].inspector.get_walker())
    yield d
    print "walker: %s" % (d.getResult(),)


d = connect()
d.addCallback(connected)

def errback(e):
    print "ERROR: %s" % (e,)
d.addErrback(errback)

fxconnection.loop()

