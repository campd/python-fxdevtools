"""
I didn't want to deal with loading semantics and sublreactor needs to
be imported first, hence the strange naming here.
"""

import sublime
import sublime_plugin
from twisted.internet import defer
from fxconnection import connect, protocol_map
from async import MainLoop


class FirefoxConnection(object):
    def __init__(self):
        self.connected = None
        self.loop = MainLoop(protocol_map, self.poke)

    def poke(self):
        print "poking!"
        sublime.set_timeout(self.loop.process, 0)

    def connect(self):
        return defer.maybeDeferred(self._connect)

    def _connect(self):
        if self.connected:
            return self.connected

        # XXX: grab port and hostname from settings maybe?
        self.connected = connect()
        self.connected.addCallback(self._connected)

        self.loop.start()

        return self.connected

    def _connected(self, client):
        print "setting connected to %s" % (self.client,)
        self.client = client
        self.connected = client

    @defer.deferredGenerator
    def choose_tab(self, *args):
        print "choosing tab!"
        d = defer.waitForDeferred(self.client.root.list_tabs())
        yield d
        tabs = d.getResult()
        yield tabs["tabs"][tabs["selected"]]

connection = FirefoxConnection()


class FirefoxConnectCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        d = connection.connect()
        d.addCallback(connection.choose_tab)
        d.addCallback(self.connected)


    def connected(self, tab):
        sublime.status_message("Connected to '%s'" % (tab.title,))


class FirefoxCssCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        d = connect()
        d.addCallback(self.dump)

    def dump(self, s):
        print "%s" % (s,)
