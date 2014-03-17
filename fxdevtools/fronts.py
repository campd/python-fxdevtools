"""
Front specializations
"""

from protocol import Front, Request
from marshallers import getType, addType, DictType

addType(DictType("tablist", {
  "selected": "number",
  "tabs": "array:tab"
}))


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
            "response": { "_retval": "tablist" }
        },
        {
            "name": "actorDescriptions",
            "request": {},
            "response": { "_retval": "json" }
        }],
        "events": {
            "tabListChanged": {}
        }
    }

    def __init__(self, conn, packet):
        self.actorID = "root"
        self.hello = packet
        super(RootFront, self).__init__(conn)


print "ABOUT TO CREATE TABFRONT"
class TabFront(Front):
    typeName = "tab"
    actorDesc = {
        "typename": "tab",
        "methods": [],
    }

    def __init__(self, conn):
        self.conn = conn

    def form(self, form, detail=None):
        self.actorID = form["actor"]
        self.inspector = getType("inspector").read(form["inspectorActor"], self)
        for name in form.keys():
            setattr(self, name, form[name])

    def formData(key):
        return self._form[key]
