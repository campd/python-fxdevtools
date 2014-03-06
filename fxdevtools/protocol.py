from twisted.internet.protocol import Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor, defer

from events import Event
from marshallers import addType, getType, typeExists, Request, Response, ActorType, DictType, PlaceholderType

import json

class FirefoxDevtoolsProtocol(Protocol):
  def __init__(self):
    self.buffer = ""
    self.onPacket = Event()

  def dataReceived(self, data):
    self.buffer += data

    try:
      length, remaining = self.buffer.split(':', 1)
    except ValueError:
      return

    length = int(length)
    if len(remaining) < length:
      return

    packet = remaining[0:length]
    self.buffer = remaining[length:]
    self.onPacket.emit(json.loads(packet))

  def sendPacket(self, packet):
    data = json.dumps(packet)
    self.transport.write(str(len(data)) + ":" + data)


class FirefoxDevtoolsClient(object):
  def __init__(self, conn):
    self.root = None
    self.conn = conn
    self.conn.onPacket += self.onPacket
    self.onConnected = Event()
    self.pools = set()

  def addPool(self, pool):
    self.pools.add(pool)

  def removePool(self, pool):
    self.pools.discard(pool)

  def poolFor(self, actorID):
    for pool in self.pools:
      if pool.hasFront(actorID):
        return pool
    return None

  def getFront(self, actorID):
    pool = self.poolFor(actorID)
    if not pool:
      return None
    return pool.getFront(actorID)

  def onPacket(self, packet):
    if not self.root:
      # Yeah these should be runtime errors.
      assert packet["from"] == "root"
      assert "applicationType" in packet

      from fronts import RootFront
      self.root = RootFront(self, packet)
      d = self.root.actorDescriptions()
      d.addCallback(self.registerActorDescriptions)
      d.addErrback(self.describeFailed)
      return

    if packet["from"] == "root":
      front = self.root
    else:
      front = self.getFront(packet["from"])

    front.onPacket(packet)

  def describeFailed(self, e):
    print "Error listing actor descriptions: %s" % (e,)
    import protodesc
    self.registerActorDescriptions(protodesc.actorDescriptions)

  def registerActorDescriptions(self, descriptions):
    for desc in descriptions["types"].values():
      typeName = desc["typeName"]
      category = desc["category"]
      if category == "actor":
        t = getType(desc["typeName"])

        if isinstance(t, ActorType):
          concrete = t.cls
        elif isinstance(t, PlaceholderType) and t.concrete:
          concrete = t.concrete.cls
        else:
          concrete = type(str(typeName), (Front,), { "typeName": typeName })

        concrete.implementActor(desc)
        continue

      if typeExists(typeName):
        continue

      if category == "dict":
        addType(DictType(typeName, desc["specializations"]))

    self.onConnected.emit(self)

  def sendPacket(self, packet):
    self.conn.sendPacket(packet)

class Pool(object):
  def __init__(conn):
    self.conn = conn

  def parent():
    return self.conn.poolFor(self.actorID)

  def marshallPool(self):
    return self

  @property
  def fronts(self):
    try:
      return self._fronts
    except AttributeError:
      self._fronts = {}
      self.conn.addPool(self)
      return self._fronts

  def manage(self, front):
    """Add an actor as a child of this pool."""
    self.fronts[front.actorID] = front

  def unmanage(self, front):
    """Remove an actor as a child of this pool"""
    del self.fronts[front.actorID]

  def hasFront(self, actorID):
    return actorID in self.fronts

  def isEmpty(self):
    return len(self.fronts) == 0

  def getFront(self, actorID):
    return self.fronts[actorID]

  def destroy(self):
    if hasattr(self, "destroyed"):
      return

    self.destroyed = True
    parent = self.parent()
    if parent:
      parent.unmanage(self)
    if not self._fronts:
      return

    for actor in self.fronts.values():
      actor.destroy()

    self.conn.removePool(self)
    del self._fronts

class Method(object):
  def __init__(self, name, methodDesc):
    self.name = name
    self.methodDesc = methodDesc
    self.request = Request(name, methodDesc["request"])
    self.response = Response(methodDesc["response"])

class FrontMeta(type):
  def __init__(cls, name, parents, dct):
    if "typeName" in dct:
      addType(ActorType(dct["typeName"], cls))

    if "actorDesc" in dct:
      cls.implementActor(dct["actorDesc"])

    return super(FrontMeta, cls).__init__(name, parents, dct)

class Front(Pool):
  __metaclass__ = FrontMeta

  @classmethod
  def implementActor(cls, actorDesc):
    if isinstance(actorDesc, str) or isinstance(actorDesc, unicode):
      actorDesc = json.loads(s)

    for method in actorDesc["methods"]:
      cls.implementMethod(method)

  @classmethod
  def implementMethod(cls, method):
    name = method["name"]
    m = Method(name, method)
    setattr(cls, "method_%s" % (name,), m)
    setattr(cls, "impl_%s" % (name,),
      lambda self, *args, **kwargs: self.request(m, *args, **kwargs))

  def __init__(self, conn):
    self.conn = conn
    self.requests = []

  def __getattr__(self, name):
    # By default we put implementations in impl_, but
    # if there's no override defined, forward the bare name
    # to the impl.
    if not name.startswith("impl_"):
      impl = "impl_%s" % (name,)
      if hasattr(self, impl):
        return getattr(self, impl)

    raise AttributeError("'%s' object has no attribute named '%s'" % (self.__class__.__name__, name))

  def form(self, form, detail=None):
    pass

  def request(self, method, *args, **kwargs):
    packet = method.request(self, *args, **kwargs)
    packet["to"] = self.actorID
    self.conn.sendPacket(packet)

    d = defer.Deferred()
    def finish(responsePacket):
      if "error" in responsePacket:
        d.errback(responsePacket)
        return

      d.callback(method.response(self, responsePacket))
    self.requests.append(finish)

    return d

  def onPacket(self, packet):
    # XXX: pick off event packets

    if len(self.requests) == 0:
      return

    cb = self.requests.pop(0)
    cb(packet)

def gotProtocol(p):
  d = defer.Deferred()
  client = FirefoxDevtoolsClient(p)
  client.onConnected += lambda _: d.callback(client)
  return d

def connect(hostname="localhost", port=6080):
  point = TCP4ClientEndpoint(reactor, hostname, port)
  d = connectProtocol(point, FirefoxDevtoolsProtocol())
  d.addCallback(gotProtocol)
  return d
