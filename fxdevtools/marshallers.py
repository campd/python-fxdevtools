"""Protocol types helper classes for reading and writing packets."""


registered_types = {}


class Request(object):
    """Constructs a request packet given a request template."""

    def __init__(self, name, template):
        self.name = name
        self.template = template
        if not "type" in self.template:
            self.template["type"] = self.name

    def __call__(self, ctx, *args, **kwargs):
        print "calling %s" % (self.name,)
        return self.__convert(self.template, ctx, args, kwargs)

    def __convert(self, template, ctx, args, kwargs):
        if isinstance(template, dict) and "_arg" in template:
            t = get_type(template["type"])
            return t.write(args[template["_arg"]], ctx)
        elif isinstance(template, dict):
            ret = {}
            for name in template:
                ret[name] = self.__convert(template[name], ctx, args, kwargs)
            return ret
        elif isinstance(template, list) or isinstance(template, tuple):
            return [self.__convert(item, ctx, args, kwargs)
                    for item in template]

        return template


class ProtocolEvent(object):
    def __init__(self, name, template):
        self.name = name

        self.template = template
        self.arg_paths = {}
        self.kwarg_paths = {}

        # Pretty sure there's a better way to do this but I'm tired.
        self.__find_args(self.template, [])

    def __call__(self, ctx, packet):
        args = []
        i = 0
        while i in self.arg_paths:
            readpath = self.arg_paths[i]
            args.append(readpath(ctx, packet))
            i += 1

        kwargs = {}
        for key in self.kwarg_paths:
            kwargs[key] = self.kwarg_paths[key](ctx, packet)

        getattr(ctx, self.name).emit(*args, **kwargs)

    def __find_args(self, template, path):
        if isinstance(template, dict) and "_arg" in template:
            self.arg_paths[template["_arg"]] = ReadPath(path, template["type"])
            return

        if isinstance(template, dict) and "_option" in template:
            self.kwarg_paths[template["_option"]] = \
                ReadPath(path, "nullable:" + template["type"])
            return

        if isinstance(template, dict):
            print "it's a dict"
            iterable = template.iterkeys()
        elif isinstance(template, list):
            iterable = range(0, len(template))
        else:
            return

        for key in iterable:
            print "looking for %s" % (key,)
            path.append(key)
            ret = self.__find_args(template[key], path)
            if ret:
                return ret
            path.pop()


class Response(object):
    """Reads a response packet given a response template."""

    def __init__(self, template):
        self.readpath = self.__find_response(template, []) or ReadPath()

    def __call__(self, ctx, packet):
        return self.readpath(ctx, packet)
        if self.path == None:
            return None

    def __find_response(self, template, path):
        if isinstance(template, dict) and "_retval" in template:
            return ReadPath(path, template["_retval"])
        elif isinstance(template, dict):
            iterable = template.iterkeys()
        elif isinstance(template, list):
            iterable = range(0, len(template))
        else:
            return None

        for key in iterable:
            path.append(key)
            ret = self.__find_response(template[key], path)
            if ret:
                return ret
            path.pop()
        return None


class ReadPath(object):
    """ Stores a template location for reading from packets."""
    def __init__(self, path=None, t=None):
        if path != None:
            self.path = [p for p in path]
        self.type = get_type(t)

    def __call__(self, ctx, packet):
        if self.path == None:
            return None
        for p in self.path:
            packet = packet[p]
        return self.type.read(packet, ctx)


###
# Type registration and management.
###


def get_type(t) :
    if t == None:
        return Primitive

    if not isinstance(t, str) and not isinstance(t, unicode):
        return t

    if t in registered_types:
        return registered_types[t]

    pieces = t.split(":", 1)

    if len(pieces) > 1:
        collection, subtype = pieces
        if collection == "nullable":
            return add_type(NullableType(subtype))
        if collection == "array":
            return add_type(ArrayType(subtype))

        raise ValueError("Unknown collection type: " + collection)

    pieces = t.split("#", 1)
    if len(pieces) > 1:
        return add_type(ActorDetailType(t, pieces[0], pieces[1]))

    # If this type hasn't been registered yet, add a placeholder type
    # assuming that the type will be filled in later.  If the type
    # is actually used before it is registered, it will raise an error.
    return add_type(PlaceholderType(t))


def add_type(t):
    if t.name in registered_types:
        registered = registered_types[t.name]
        if not isinstance(registered, PlaceholderType) or registered.concrete:
            raise ValueError("Type %s registered twice!" % (t.name,))
        registered.concrete = t
        return registered

    registered_types[t.name] = t
    return t


def type_exists(name):
    return name in registered_types


###
# Individual types
###


class ProtocolType(object):
    pass


class PrimitiveType(ProtocolType):
    def __init__(self, name, read=None, write=None):
        self.name = name

    def read(self, v, ctx=None, detail=None):
        if v == None:
            raise Error("None passed where a value is required")
        return v

    def write(self, v, ctx=None, detail=None):
        if v == None:
            raise Error("None passed where a value is required")
        return v


class NullableType(ProtocolType):
    def __init__(self, subtype):
        self.subtype = get_type(subtype)
        self.name = "nullable:" + self.subtype.name

    def read(self, v, ctx=None, detail=None):
        if v == None:
            return v
        return self.subtype.read(v, ctx)

    def write(self, v, ctx=None, detail=None):
        if v == None:
            return v
        return self.subtype.write(v, ctx)


class ArrayType(ProtocolType):
    def __init__(self, subtype):
        self.subtype = get_type(subtype)
        self.name = "array:" + self.subtype.name

    def read(self, v, ctx=None, detail=None):
        if isinstance(self.subtype, PrimitiveType):
            return v
        return [self.subtype.read(i, ctx, detail) for i in v]

    def write(self, v, ctx=None, detail=None):
        if isinstance(self.subtype, PrimitiveType):
            return v
        return [self.subtype.write(i, ctx, detail) for i in v]


class DictType(ProtocolType):
    def __init__(self, name, specializations):
        self.name = name
        self.specializations = specializations

    def read(self, v, ctx=None, detail=None):
        ret = {}
        for prop in v.keys():
            if prop in self.specializations:
                specialization = self.specializations[prop]
                ret[prop] = get_type(specialization).read(v[prop], ctx, detail)
            else:
                ret[prop] = v[prop]
        return ret

    def write(self, v, ctx=None, detail=None):
        ret = {}
        for prop in v.keys():
            if prop in self.specializations:
                specialization = self.specializations[prop]
                ret[prop] = get_type(specialization).write(v[prop], ctx, detail)
            else:
                ret[prop] = v[prop]
        return ret

    def write(self, v, ctx=None, detail=None):
        pass


class ActorType(ProtocolType):
    def __init__(self, name, cls):
        self.name = name
        self.cls = cls

    def read(self, v, ctx=None, detail=None):
        if isinstance(v, str) or isinstance(v, unicode):
            actor_id = v
        else:
            actor_id = v["actor"]

        front = ctx.conn.get_front(actor_id)
        if not front:
            front = self.cls(ctx.conn)
            front.actor_id = actor_id
            ctx.marshall_pool().manage(front)

        front.form(v, detail)

        return front

    def write(self, v, ctx=None, detail=None):
        return v.actor_id


class ActorDetailType(ProtocolType):
    def __init__(self, ActorType, detail):
        self.subtype = get_type(ActorType)
        self.detail = detail

    def read(self, v, ctx=None):
        return self.subtype.read(v, ctx, self.detail)

    def write(self, v, ctx=None):
        return self.subtype.write(v, ctx, self.detail)


class PlaceholderType(ProtocolType):
    def __init__(self, name):
        self.name = name
        self.concrete = None

    def __getattr__(self, name):
        if not self.concrete:
            raise ValueError(
                "No concrete type registered for %s!" % (self.name,))
        return getattr(self.concrete, name)

Primitive = add_type(PrimitiveType("primitive"))
String = add_type(PrimitiveType("string"))
Number = add_type(PrimitiveType("number"))
Boolean = add_type(PrimitiveType("boolean"))
JSON = add_type(PrimitiveType("json"))


