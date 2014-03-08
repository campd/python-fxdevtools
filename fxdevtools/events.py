class Event():
    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def emit(self, *args, **kwargs):
        for handler in self.__handlers:
            handler(*args, **kwargs)

    def forget(self, obj):
        for handler in self.__handlers:
            if handler.__self__ == obj:
                self -= handler
