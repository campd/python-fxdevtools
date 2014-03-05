from twisted.internet import reactor

from fxdevtools.protocol import connect

def done(packet):
  print packet

def gotRoot(client):
  print "Got a root client"
  d = client.root.echo("hello")
  d.addCallback(done)

def connected(client):
  client.onConnected += gotRoot

d = connect()
d.addCallback(connected)
reactor.run()
