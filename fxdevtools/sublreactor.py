"""Install a twisted reactor that posts events to the sublimetext main loop."""
import sublime
from twisted.internet.error import ReactorAlreadyInstalledError, ReactorAlreadyRunning, ReactorNotRestartable

reactorAlreadyInstalled = False
try:
    from twisted.internet import _threadedselect
    _threadedselect.install()
except ReactorAlreadyInstalledError:
    print "reactor already installed"
    reactorAlreadyInstalled = True

from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint

try:
    print "installing reactor"
    reactor.interleave(lambda f: sublime.set_timeout(f, 0), installSignalHandlers=False)
except ReactorAlreadyRunning:
    print "reactor already running"
    reactorAlreadyInstalled = True
except ReactorNotRestartable:
    print "reactor not restartable"
    reactorAlreadyInstalled = True
