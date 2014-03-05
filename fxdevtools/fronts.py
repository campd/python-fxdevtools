from protocol import Front, Request


class RootFront(Front):
  actorDesc = {
    "typename": "root",
    "methods": [{
      "name": "echo",
      "request": {
        "string": { "_arg": 0, "type": "string" }
      },
      "response": {
        "string": { "_retval": "string" }
      }
    },
    {
      "name": "listTabs",
      "request": {},
      "response": {
        "tabs": { "_retval": "json" }
      }
    }]
  }

  def __init__(self, conn, packet):
    self.actorID = "root"
    self.hello = packet
    self.conn = conn
    super(RootFront, self).__init__(conn)

class TabFront(Front):
  actorDesc = {
    "typename": "tab",
    "methods": []
  }

  def __init__(self, conn):
    self.conn = conn

  def form(self, form):
    self.actorID = form.actor

