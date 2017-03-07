from __future__ import absolute_import

import Queue

import zmq

import snn_utils.comm as comm


class SendServer(comm.AsyncSender):
    def __init__(self, host, port, transport='tcp'):
        self._sock = zmq.Context().socket(zmq.PUB)
        self._sock.bind("{}://{}:{}".format(transport, host, port))

    def send(self, data):
        self._sock.send(data)

    @staticmethod
    def start(host, port):
        return SendServer(host, port)


class ReceiveClient(comm.AsyncReceiver):
    def __init__(self, host, port, transport='tcp'):
        self._sock = zmq.Context().socket(zmq.SUB)
        self._sock.setsockopt(zmq.SUBSCRIBE, "")
        self._sock.connect("{}://{}:{}".format(transport, host, port))

        self._buffer = Queue.Queue()

    def _recv(self):
        try:
            self._buffer.put(self._sock.recv(zmq.NOBLOCK))
        except zmq.ZMQError as e:
            pass

    def has_data(self):
        self._recv()
        return not self._buffer.empty()

    def get_data(self):
        return self._buffer.get_nowait()

    @staticmethod
    def start(host, port):
        return ReceiveClient(host, port)
