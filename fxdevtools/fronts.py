from protocol import Front, Request


class RootFront(Front):
  typeName = "root"
  actorDesc = {
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
    },
    {
      "name": "actorDescriptions",
      "request": {},
      "response": { "_retval": "json" }
    }
    ]
  }

  def __init__(self, conn, packet):
    self.actorID = "root"
    self.hello = packet
    super(RootFront, self).__init__(conn)


class TabFront(Front):
  typeName = "tab"
  actorDesc = {
    "typename": "tab",
    "methods": []
  }

  def __init__(self, conn):
    self.conn = conn

  def form(self, form, detail=None):
    self.actorID = form.actor

class InspectorFront(Front):
  typeName = "inspector"

  def __init__(self, conn):
    self.conn = conn

  def form(self, form, detail=None):
    self.actorID = form

