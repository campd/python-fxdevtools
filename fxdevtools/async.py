# -*- Mode: Python -*-

# Based on some code from asyncore.py:

#   Id: asyncore.py,v 2.51 2000/09/07 22:29:26 rushing Exp
#   Author: Sam Rushing <rushing@nightmare.com>

# ======================================================================
# Copyright 1996 by Sam Rushing
#
#                         All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of Sam
# Rushing not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# SAM RUSHING DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN
# NO EVENT SHALL SAM RUSHING BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# ======================================================================


import asyncore
import threading
import select
import time

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

# A version of asyncore loop that uses another thread for selecting


def ignore(): pass

class MainLoop(object):
    """A main loop that can optionally be integrated into an existing loop."""
    def __init__(self, map, poke=ignore):
        self.map = map
        self.queue = Queue()
        self.poke = poke
        self.running = False
        self.selectthread = None


    def start(self):
        """Starts async polling"""
        if self.running:
            print "already running"
            return
        self.running = True
        self.poll_once()

    def stop(self):
        """Stops async polling"""
        self.running = False
        # XXX: we could cancel the current thread too...

    def process(self):
        try:
            msg = self.queue.get(True, 1)
            self.selectthread = None
            if self.running:
                self.handle_poll_results(msg)
                self.poll_once()
            self.queue.task_done()
        except Empty:
            pass

    def block(self):
        while self.running:
            self.process()

    def poll_once(self):
        print "polling"
        if  self.selectthread != None:
            raise ValueError("Already running!")

        r = []; w = []; e = []
        for fd, obj in self.map.items():
            is_r = obj.readable()
            is_w = obj.writable()
            if is_r:
                r.append(fd)
            # accepting sockets should not be writable
            if is_w and not obj.accepting:
                w.append(fd)
            if is_r or is_w:
                e.append(fd)
        if [] == r == w == e:
            print "UNHANDLED CONDITION DEAL WITH THIS"

        self.selectthread = threading.Thread(target=thread_poll, args=[r, w, e, self.queue, self.poke])
        self.selectthread.daemon = True
        self.selectthread.start()

    def handle_poll_results(self, msg):
        if "error" in msg:
            print "I don't know how we handle errors: %s" % (msg["error"],)
            return

        r, w, e = msg["fds"]

        map = self.map

        for fd in r:
            obj = map.get(fd)
            if obj is None:
                continue
            asyncore.read(obj)

        for fd in w:
            obj = map.get(fd)
            if obj is None:
                continue
            asyncore.write(obj)

        for fd in e:
            obj = map.get(fd)
            if obj is None:
                continue
            asyncore._exception(obj)


def thread_poll(r, w, e, queue, poke):
    print "in a thread"
    try:
        r, w, e = select.select(r, w, e)
        print "done selecting!"
        queue.put({"fds": (r, w, e)})
    except select.error, err:
        if err.args[0] != EINTR:
            queue.put({"error": err})
        else:
            queue.put({"fds": (r, w, e)})
    poke()
