from twisted.internet import reactor

from fxdevtools.protocol import connect

def done(packet):
  print packet

def connected(client):
  d = client.root.echo("hello")
  d.addCallback(done)

d = connect()
d.addCallback(connected)
reactor.run()
