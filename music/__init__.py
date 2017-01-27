import logging

import music
import numpy as np

from snn_utils import buffer

logger = logging.getLogger(__name__)


class PortUtility(object):
    def __init__(self, music_setup=None, fail_on_unconnected=False):
        self._music_setup = music_setup
        self._fail_on_unconnected = fail_on_unconnected

    def _set_music_setup(self, music_setup):
        self._music_setup = music_setup

    @staticmethod
    def _init_buffer(proxy, initial_value=None, fallback_width=0):
        width = proxy.width() if proxy.isConnected() else fallback_width
        assert width is not None
        if initial_value is not None:
            assert len(initial_value) == width
            return np.array(initial_value, dtype=np.double)
        else:
            return np.zeros(width, dtype=np.double)

    def _handle_unconnected_port(self, msg):
        if self._fail_on_unconnected:
            raise music.MUSICError(msg)
        logger.warning(msg)

    def publish_cont_output(self, port_name, initial_value=None, base=0, fallback_width=0):
        assert self._music_setup is not None
        proxy = self._music_setup.publishContOutput(port_name)
        buf = PortUtility._init_buffer(proxy, initial_value, fallback_width)
        if proxy.isConnected():
            proxy.map(buf, base=base)
        else:
            self._handle_unconnected_port("Output port {} is not connected".format(port_name))
        return buf

    def publish_cont_input(self, port_name, initial_value=None, base=0, maxBuffered=1, delay=0,
                           interpolate=False, fallback_width=0):
        assert self._music_setup is not None
        proxy = self._music_setup.publishContInput(port_name)
        buf = PortUtility._init_buffer(proxy, initial_value, fallback_width)
        if proxy.isConnected():
            proxy.map(buf, base=base, maxBuffered=maxBuffered, delay=delay, interpolate=False)
        else:
            self._handle_unconnected_port("Input port {} is not connected".format(port_name))
        return buf

    def publish_event_input(self, port_name, maxBuffered, accLatency, base, spike_callback):
        assert self._music_setup is not None
        proxy = self._music_setup.publishEventInput(port_name)
        if proxy.isConnected():
            proxy.map(spike_callback, music.Index.GLOBAL, size=proxy.width(), base=base, maxBuffered=maxBuffered,
                      accLatency=accLatency)
        else:
            self._handle_unconnected_port("Input port {} is not connected".format(port_name))


    def open_buffering_event_in_proxy(self, buffer, port_name, maxBuffered, accLatency, base,
                                      width_to_n_buffers=lambda size: size, idx_to_buffer=lambda idx: idx,
                                      fallback_width=0):
        proxy = self._music_setup.publishEventInput(port_name)
        width = proxy.width() if proxy.isConnected() else fallback_width
        spike_buffers = buffer.buffer_event_input(width_to_n_buffers(width))
        if proxy.isConnected():
            proxy.map(lambda time, _, index: spike_buffers[idx_to_buffer(index)].append_spike(time),
                      music.Index.GLOBAL,
                      size=width,
                      base=base,
                      maxBuffered=maxBuffered,
                      accLatency=accLatency)
        else:
            self._handle_unconnected_port("Input port {} is not connected".format(port_name))
        return spike_buffers

    def publish_event_output(self, port_name, base=0):
        proxy = self._music_setup.publishEventOutput(port_name)
        if proxy.isConnected():
            proxy.map(
                music.Index.GLOBAL,
                base=base,
                size=proxy.width()
            )
        else:
            self._handle_unconnected_port("Output port {} is not connected".format(port_name))
            proxy = DummyEventOutput()
        return proxy


class DummyEventOutput(object):
    def insertEvent(self, time, index, mapping):
        pass


class Buffer(object):
    def __init__(self, time_window):
        self._time_window = time_window
        self._cont_array_buffers = []
        self._timed_buffers = []

    def buffer_cont_input(self, array_buffer):
        timed_buffer = buffer.ValueBuffer(self._time_window)
        self._cont_array_buffers.append((timed_buffer, array_buffer))
        self._timed_buffers.append(timed_buffer)
        return timed_buffer

    def buffer_event_input(self, n_buffers):
        timed_buffers = map(lambda _: buffer.SpikeBuffer(self._time_window), range(n_buffers))
        self._timed_buffers.extend(timed_buffers)
        return timed_buffers

    def update(self, current_time):
        for timed_buffer, array_buffer in self._cont_array_buffers:
            timed_buffer.append_value(current_time, *array_buffer)
        # propagate update to clear buffers
        for timed_buffer in self._timed_buffers:
            timed_buffer.update(current_time)
