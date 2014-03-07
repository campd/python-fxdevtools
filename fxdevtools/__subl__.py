"""
I didn't want to deal with loading semantics and sublreactor needs to
be imported first, hence the strange naming here.
"""

import sublreactor

import sublime
import sublime_plugin
from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol, Factory, ClientCreator
from protocol import connect, FirefoxDevtoolsProtocol, FirefoxDevtoolsClient


from twisted.python import log
import sys
log.startLogging(sys.stdout)


class FirefoxConnection(object):
  def __init__(self):
    self.connected = None

  def connect(self):
    return defer.maybeDeferred(self._connect)

  def _connect(self):
    if self.connected:
      return self.connected

    # XXX: grab port and hostname from settings maybe?
    self.connected = connect()
    self.connected.addCallback(self._connected)
    return self.connected

  def _connected(self, client):
    self.client = client
    self.connected = client

  @defer.deferredGenerator
  def chooseTab(self, *args):
    d = defer.waitForDeferred(self.client.root.listTabs())
    yield d
    tabs = d.getResult()
    yield tabs["tabs"][tabs["selected"]]

connection = FirefoxConnection()


class FirefoxConnectCommand(sublime_plugin.ApplicationCommand):
  def run(self):
    d = connection.connect()
    d.addCallback(connection.chooseTab)
    d.addCallback(self.connected)

  def connected(self, tab):
    sublime.status_message("Connected to '%s'" % (tab.title,))


class FirefoxCssCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    d = connect()
    d.addCallback(self.dump)

  def dump(self, s):
    print "%s" % (s,)
