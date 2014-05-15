from twisted.internet import defer

import json
import re

from events import Event
from marshallers import add_type, get_type, type_exists
from marshallers import Request, Response, ActorType, DictType
from marshallers import PlaceholderType, ProtocolEvent

import fxconnection


# Return a python_style_method_name from a protocolStyleMethodName
def decamel(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s1 = re.sub('\-', '_', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class FirefoxDevtoolsClient(object):
    def __init__(self, conn):
        self.root = None
        self.conn = conn
        self.conn.on_packet += self.on_packet
        self.on_connected = Event()
        self.pools = set()

    def add_pool(self, pool):
        self.pools.add(pool)

    def remove_pool(self, pool):
        self.pools.discard(pool)

    def pool_for(self, actor_id):
        for pool in self.pools:
            if pool.has_front(actor_id):
                return pool
        return None

    def get_front(self, actor_id):
        pool = self.pool_for(actor_id)
        if not pool:
            return None
        return pool.get_front(actor_id)

    def on_packet(self, packet):
        if not self.root:
            # Yeah these should be runtime errors.
            assert packet["from"] == "root"
            assert "applicationType" in packet


            from fronts import RootFront
            self.root = RootFront(self, packet)
            d = self.root.protocol_description()
            d.addCallback(self.register_actor_descriptions)
            d.addErrback(self.describe_failed)
            return

        if packet["from"] == "root":
            front = self.root
        else:
            front = self.get_front(packet["from"])

        front.on_packet(packet)

    def describe_failed(self, e):
        print "Error listing actor descriptions: %s" % (e,)
        import protodesc
        #self.register_actor_descriptions(protodesc.actor_descriptions)

    def register_actor_descriptions(self, descriptions):
        for desc in descriptions["types"].values():
            type_name = desc["typeName"]
            category = desc["category"]
            if category == "actor":
                t = get_type(desc["typeName"])

                if isinstance(t, ActorType):
                    concrete = t.cls
                elif isinstance(t, PlaceholderType) and t.concrete:
                    concrete = t.concrete.cls
                else:
                    concrete = type(
                        str(type_name), (Front,), {"typeName": type_name})

                concrete.implement_actor(desc)
                continue

            if type_exists(type_name):
                continue

            if category == "dict":
                add_type(DictType(type_name, desc["specializations"]))

        self.on_connected.emit(self)

    def send_packet(self, packet):
        self.conn.send_packet(packet)

class Pool(object):
    def __init__(conn):
        self.conn = conn

    def parent():
        return self.conn.pool_for(self.actor_id)

    def marshall_pool(self):
        return self

    @property
    def fronts(self):
        try:
            return self._fronts
        except AttributeError:
            self._fronts = {}
            self.conn.add_pool(self)
            return self._fronts

    def manage(self, front):
        """Add an actor as a child of this pool."""
        self.fronts[front.actor_id] = front

    def unmanage(self, front):
        """Remove an actor as a child of this pool"""
        del self.fronts[front.actor_id]

    def has_front(self, actor_id):
        return actor_id in self.fronts

    def isEmpty(self):
        return len(self.fronts) == 0

    def get_front(self, actor_id):
        return self.fronts[actor_id]

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

        self.conn.remove_pool(self)
        del self._fronts

class Method(object):
    def __init__(self, name, method_desc):
        self.name = name
        self.method_desc = method_desc
        self.request = Request(name, method_desc["request"])
        self.response = Response(method_desc["response"])
        self.oneway = getattr(method_desc, "oneway", False)
        self.release = getattr(method_desc, "release", False)

class FrontMeta(type):
    def __init__(cls, name, parents, dct):
        if "actor_desc" in dct:
            actor_desc = dct["actor_desc"]
            cls.implement_actor(actor_desc)

        return super(FrontMeta, cls).__init__(name, parents, dct)

class Front(Pool):
    __metaclass__ = FrontMeta

    @classmethod
    def implement_actor(cls, actor_desc):
        if isinstance(actor_desc, str) or isinstance(actor_desc, unicode):
            actor_desc = json.loads(s)

        if "typeName" in actor_desc:
            add_type(ActorType(actor_desc["typeName"], cls))

        for method in actor_desc["methods"]:
            cls.implement_method(method)

        if "events" in actor_desc:
            cls.events = {}
            for event_name in actor_desc["events"]:
                cls.implement_event(event_name, actor_desc["events"][event_name])

    @classmethod
    def implement_method(cls, method):
        m = Method(method["name"], method)
        name = decamel(method["name"])

        setattr(cls, "method_%s" % (name,), m)
        setattr(cls, "impl_%s" % (name,),
          lambda self, *args, **kwargs: self.request(m, *args, **kwargs))

    @classmethod
    def implement_event(cls, name, template):
        prop_name = "on_" + decamel(name)
        print "implementing event: %s" % (name,)
        print json.dumps(template)
        print "name: %s" % (prop_name,)
        evt = ProtocolEvent(prop_name, template)
        priv_name = "_" + prop_name
        # Since I'm using event objects, lazily create event objects when they
        # are asked for.  But maybe it'd be better to use string events.
        def event_get(self):
            if not hasattr(self, priv_name):
                setattr(self, priv_name, Event())
            return getattr(self, priv_name)
        def event_set(self, evt):
            setattr(self, priv_name, evt)
        setattr(cls, prop_name, property(event_get, event_set))

        cls.events[name] = evt

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

        raise AttributeError(
            "'%s' object has no attribute named '%s'" %
                (self.__class__.__name__, name))

    def form(self, form, detail=None):
        pass

    def request(self, method, *args, **kwargs):
        packet = method.request(self, *args, **kwargs)
        packet["to"] = self.actor_id
        self.conn.send_packet(packet)

        if method.oneway:
            return

        d = defer.Deferred()
        def finish(response_packet):
            if "error" in response_packet:
                d.errback(response_packet)
                return

            d.callback(method.response(self, response_packet))

            if method.release:
                self.destroy()

        self.requests.append(finish)

        return d

    def on_packet(self, packet):
        if "type" in packet and packet["type"] in self.events:
            self.events[packet["type"]](self, packet)

        # XXX: pick off event packets

        if len(self.requests) == 0:
            return

        cb = self.requests.pop(0)
        cb(packet)

def gotProtocol(p):
    d = defer.Deferred()
    client = FirefoxDevtoolsClient(p)
    client.on_connected += lambda _: d.callback(client)
    return d

def connect(hostname="localhost", port=6080):
    d = fxconnection.connect(hostname, port)
    d.addCallback(gotProtocol)
    return d

import fronts
