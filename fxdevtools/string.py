"""
Long string types.
"""

from twisted.internet import defer

class LongStringFront(Front):
    def __init__(self, conn):
        self.conn = conn

    def destroy(self):
        self.initial = None
        self.length = None
        super(LongStringFront, self).destroy()

    def form(self, form):
        if isinstance(form, str) or isinstance(form, unicode):
            self.initial = form
            self.length = len(form)
            self.full = form
        else:
            self.initial = form.initial
            self.length = form.length

    def string(self, form):
        if self.full:
            return defer.succeed(self.full)

        d = this.substring(0, self.length)
        d.addCallback(self._cache)
        return d

    def _cache(self, full):
        self.full = full



