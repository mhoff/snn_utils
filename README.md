# *snn_utils*: Utilities for Spiking Neural Networks

## MUSIC

This package contains utilities for quick music node development.
Wrappers like `publish_cont_output` allow for port creation & mapping in one line,
while also returning a stub buffer in case of the port being unconnected.

### Example

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from snn_utils.music.node import PyMusicNode


class SignalNode(PyMusicNode):
    def __init__(self):
        PyMusicNode.__init__(self, time_step=0.02, total_time=100)

    def _setup(self, music_setup):
        self._signal_out = self.publish_cont_output('signal_out', fallback_width=1)

    def _run_single_cycle(self, curr_time):
        self._signal_out[0] = curr_time % 1.0

    def _post_cycle(self, curr_time, measured_cycle_time):
        print("[{}] sending {}".format(curr_time, self._signal_out[0]))

if __name__ == '__main__':
    SignalNode().main()
```
