import matplotlib.pyplot as plt

import snn_utils.plotter as plotter


def configure_matplotlib():
    plt.ion()  # interactive mode
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.switch_backend('TkAgg')


class MatplotlibWindow(plotter.PlotWindow):
    def __init__(self, plot_builder, data_source, max_time_window=None, enabled=True):
        plotter.PlotWindow.__init__(self, plot_builder, data_source, max_time_window)

        self._enabled = enabled

        self._recording = False
        self._current_recording_session_prefix = None
        self._next_recording_id = 0

        self._layout_on_update = True
        self._fig.canvas.mpl_connect('resize_event', self._on_resize)

        self._fig.canvas.mpl_connect('button_press_event', self._on_click)

        self._update_window_title()

    def _create_figure(self):
        return plt.figure()

    def _draw(self):
        self._fig.canvas.draw()

    def _update_window_title(self):
        self._fig.canvas.set_window_title("Plotter [{}]".format(["disabled", "enabled"][self._enabled]))

    def _on_resize(self, resize_event):
        self._layout_on_update = True

    def _on_click(self, mouse_event):
        if mouse_event.button == 3:
            # left mouse button
            self._enabled = not self._enabled
            self._update_window_title()
            print("Plotter: drawing {}".format(["disabled", "enabled"][self._enabled]))
        elif mouse_event.button == 1000:  # TODO RECORDING CURRENTLY NOT IMPLEMENTED
            # right mouse button
            self._recording = not self._recording
            if self._recording:
                self._current_recording_session_prefix = None
                self._next_recording_id = 0
            print("Plotter: recording {}".format(["stopped", "started"][self._recording]))

    def draw(self):
        self.get_figure().canvas.flush_events()
        if self._layout_on_update:
            self._layout_on_update = False
            self._fig.tight_layout()
            if not self._enabled:
                self._draw()
        if self._enabled:
            plotter.PlotWindow.draw(self)
            # if self._recording:
            #     if self._current_recording_session_prefix is None:
            #         self._current_recording_session_prefix = "{:010d}".format(int(1000 * curr_time))
            #     self._fig.savefig("res/{}_{:05d}.png".format(self._current_recording_session_prefix, self._next_recording_id))
            #     self._next_recording_id += 1

