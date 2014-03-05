
registeredTypes = {}

class Request(object):
  """Constructs a request packet given a request template."""

  def __init__(self, name, template):
    self.name = name
    self.template = template
    if not "type" in self.template:
      self.template["type"] = self.name

  def __call__(self, *args, **kwargs):
    print "calling..."
    return self.__convert(self.template, args, kwargs)

  def __convert(self, template, args, kwargs):
    if isinstance(template, dict) and "_arg" in template:
      t = getType(template["type"])
      return t.write(args[template["_arg"]])
    elif isinstance(template, dict):
      return {name: self.__convert(template[name], args, kwargs) for name in template}
    elif isinstance(template, list) or isinstance(template, tuple):
      return [self.__convert(item, args, kwargs) for item in template]

    return template

class Response(object):
  """Reads a response packet given a response template."""

  def __init__(self, template):
    self.path, t = self.__findResponse(template, [])
    self.type = getType(t)

  def __call__(self, packet):
    for p in self.path:
      packet = packet[p]
    return self.type.read(packet)

  def __findResponse(self, template, path):
    if isinstance(template, dict) and "_retval" in template:
      return (path, template["_retval"])
    elif isinstance(template, dict):
      iterable = template.iterkeys()
    elif isinstance(template, list):
      iterable = range(0, len(template))
    else:
      return None

    for key in iterable:
      path.append(key)
      ret = self.__findResponse(template[key], path)
      if ret:
        return ret
      path.pop()
    return None

def getType(t) :
  if t == None:
    return Primitive

  if not isinstance(t, str):
    return t

  if t in registeredTypes:
    return registeredTypes[t]

  pieces = t.split(":", 1)

  if pieces.len > 1:
    collection, subtype = pieces
    if collection == "nullable":
      return addType(NullableType(subtype))

    raise ValueError("Unknown collection type: " + collection)

  raise ValueError("Unknown type: " + type)


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
    self.subtype = getType(subtype)
    self.name = "nullable:" + name

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
    self.subtype = getType(subtype)
    self.name = "array:" + subtype.name

  def read(self, v, ctx=None, detail=None):
    if isinstance(self.subtype, PrimitiveType):
      return v
    return [subtype.read(i, ctx, detail) for i in v]

  def write(self, v, ctx=None, detail=None):
    if isinstance(self.subtype, PrimitiveType):
      return v
    return [subtype.write(i, ctx, detail) for i in v]

class DictType(ProtocolType):
  def __init__(self, name, specializations):
    self.name = name
    self.specializations = specializations

  def read(self, v, ctx=None, detail=None):
    ret = {}
    for prop in v.keys():
      if prop in self.specializations:
        ret[prop] = getType(self.specializations[prop]).read(v[prop], ctx, detail)
      else:
        ret[prop] = v[prop]
    return ret

  def write(self, v, ctx=None, detail=None):
    ret = {}
    for prop in v.keys():
      if prop in self.specializations:
        ret[prop] = getType(self.specializations[prop]).write(v[prop], ctx, detail)
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
    if isinstance(v, str):
      actorID = v
    else:
      actorID = v.actorID

    front = ctx.conn.getFront(actorID)
    if not front:
      front = cls(ctx.conn)
      front.actorID = actorID
      front.form(v, detail)
      ctx.marshallPool().manage(front)

    front.form(v, detail, ctx)

    return front

  def write(self, v, ctx=None, detail=None):
    return v.actorID

def addType(t):
  registeredTypes[t.name] = t
  return t

String = addType(PrimitiveType("string"))
Number = addType(PrimitiveType("number"))
Boolean = addType(PrimitiveType("boolean"))
JSON = addType(PrimitiveType("json"))

