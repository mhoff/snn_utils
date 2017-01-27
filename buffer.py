import collections
import threading


class TimeBuffer(object):
    def __init__(self, time_window):
        self._time_window = time_window
        self._times = collections.deque()

    def update(self, current_time):
        threshold = current_time - self._time_window
        if self._times:
            time = self._times.popleft()
            while self._times and time < threshold:
                time = self._times.popleft()
            if time >= threshold:
                self._times.appendleft(time)

    def get_times(self):
        return self._times

    def __len__(self):
        return len(self._times)

    def __repr__(self):
        return str(self._times)

    def __getitem__(self, sliced):
        return self._times[sliced]

    def append(self, time):
        # assert(not self._times or time >= self._times[-1])
        self._times.append(time)


class SpikeBuffer(TimeBuffer):
    def __init__(self, time_window):
        TimeBuffer.__init__(self, time_window)

    def append_spike(self, time):
        self.append(time)

    def rate(self):
        return float(len(self)) / self._time_window


class ConcurrentSpikeBuffer(SpikeBuffer):
    def __init__(self, time_window):
        SpikeBuffer.__init__(self, time_window)
        self._lock = threading.Lock()

    def append(self, time):
        with self._lock:
            SpikeBuffer.append(self, time)

    def rate(self):
        with self._lock:
            return SpikeBuffer.rate(self)


class ValueBuffer(TimeBuffer):
    def __init__(self, time_window):
        TimeBuffer.__init__(self, time_window)
        self._values = []

    def append_value(self, time, value):
        self.append(time)
        self._values.append(value)

    def update(self, current_time):
        TimeBuffer.update(self, current_time)
        self._values[:] = self._values[-len(self._times):]

    def get_values(self):
        return self._values

    def get_timed_values(self):
        return zip(self._times, self._values)

    def __repr__(self):
        return str(self.get_timed_values())

    def __getitem__(self, sliced):
        return self.get_timed_values()[sliced]
