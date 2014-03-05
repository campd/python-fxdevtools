from protocol import Front, Request


class RootFront(Front):
  actorDesc = {
    "methods": [{
      "name": "echo",
      "request": {
        "string": { "_arg": 0, "type": "string" }
      },
      "response": {
        "string": { "_retval": "string" }
      }
    }]
  }

  def __init__(self, conn, packet):
    self.actorID = "root"
    self.hello = packet
    self.conn = conn
    super(RootFront, self).__init__(conn)

