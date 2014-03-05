
registeredTypes = {}

class Request(object):
  """Constructs a request packet given a request template."""

  def __init__(self, name, template):
    self.name = name
    self.template = template
    if not "type" in self.template:
      self.template["type"] = self.name

  def __call__(self, *args, **kwargs):
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

  raise Error("Oops I haven't finished implementing getType")

def identityWrite(v):
  if v == None:
    raise Error("None passed where a value is required")
  return v

class ProtocolType(object):
  def __init__(self, name, read=None, write=None):
    self.name = name
    self.primitive = read == None and write == None
    self.read = read or identityWrite
    self.write = write or identityWrite

def addType(name, read=None, write=None):
  t = ProtocolType(name, read, write)
  registeredTypes[name] = t
  return t

Primitive = addType("primitive")
String = addType("string")
Number = addType("number")
Boolean = addType("boolean")
JSON = addType("json")

