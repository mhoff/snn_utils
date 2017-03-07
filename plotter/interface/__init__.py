import sys
import time

import zmq


class Communicator(object):
    def __init__(self, context=None, poll_timeout=0.000000001):
        self._context = zmq.Context() if context is None else context
        self._poller = zmq.Poller()
        self._handler = {}
        self._poll_timeout = poll_timeout
        self._external_context = context is not None

    def add_subscriber(self, host, port, callback, transport="tcp", prefix=""):
        address = "{}://{}:{}".format(transport, host, port)
        print("Subscribing to {}".format(address))
        sock = self._context.socket(zmq.SUB)
        sock.connect(address)
        sock.setsockopt(zmq.SUBSCRIBE, prefix)
        self._handler[sock] = callback
        self._poller.register(sock, zmq.POLLIN)

    def tick(self):
        # exhaustive poll
        polled = []
        exhausted = False
        while not exhausted:
            for sock, kind in polled:
                assert kind is zmq.POLLIN
                self._handler[sock](sock.recv(zmq.NOBLOCK))
            polled = self._poller.poll(self._poll_timeout)
            exhausted = not polled

    def terminate(self):
        print("Closing {} sockets.".format(len(self._handler.keys())))
        for sock in self._handler.keys():
            sock.close()
        if not self._external_context:
            self._context.term()


class SimpleTaskScheduler(object):
    def __init__(self):
        self._handles = []

    def add_handle(self, func, interval):
        self._handles.append([func, interval, 0])

    def tick(self, sim_time):
        for handle in self._handles:
            func, interval, last_tick = handle
            if (sim_time - last_tick) > interval:
                func()
                handle[2] = sim_time


class Master(object):
    def __init__(self, time_source=lambda: time.time() * 1000.0):
        self._comm = Communicator()
        self._scheduler = SimpleTaskScheduler()
        self._time_source = time_source

    def communicator(self):
        return self._comm

    def scheduler(self):
        return self._scheduler

    def mainloop(self):
        try:
            print("Entering mainloop. Abort with CTRL+C.")
            while True:
                # networking
                self._comm.tick()
                # ui and other secondary stuff
                self._scheduler.tick(self._time_source())
        except KeyboardInterrupt:
            print(" -- CTRL+C received. Shutting down.")
            self._comm.terminate()
            sys.exit(0)
