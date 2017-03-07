import numpy as np

import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap


class EmptyPlot(object):
    def __init__(self, spine_left=False, spine_right=False, spine_top=None, spine_bottom=None, label=None, hline=False):
        self._spine_top = spine_top
        self._spine_bottom = spine_bottom
        self._spine_left = spine_left
        self._spine_right = spine_right
        self._label = label
        self._hline = hline

    def build(self, ax, col_header=False, col_footer=False, **kwargs):
        ax.spines['top'].set_visible(self._spine_top if self._spine_top is not None else col_header)
        ax.spines['bottom'].set_visible(self._spine_top if self._spine_top is not None else col_footer)
        ax.spines['left'].set_visible(self._spine_left)
        ax.spines['right'].set_visible(self._spine_right)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_ticks([])
        if self._label is not None:
            ax.set_ylabel(self._label)
        if self._hline:
            ax.set_ylim(-1, 1)
            ax.set_xlim(-1, 1)
            ax.hlines(0, -1, 1, lw=2, alpha=0.25, color='grey')
        return self

    def update_axis(self, *x_lim):
        pass

    def update(self, data_provider):
        pass

    def draw(self):
        pass


class Plot(object):
    def __init__(self, keys, label, legend, legend_loc, colors):
        self._keys = keys
        self._label = label
        self._legend = legend
        self._legend_loc = legend_loc
        self._ax = None

        self._colors = colors

        if isinstance(colors, LinearSegmentedColormap):
            self._colors = self._gen_colors_with_colormap(colors)
        elif isinstance(colors, list):
            self._colors = colors
        else:
            # also handles None
            self._colors = self._gen_colors_with_atom(colors)

    def _gen_colors_with_colormap(self, colormap):
        return colormap(np.linspace(0, 1, len(self._keys)))

    def _gen_colors_with_atom(self, atom):
        return [atom] * len(self._keys)

    def build(self, ax, show_x=False, col_header=False, col_footer=False):
        self._ax = ax
        self._create_primitives()
        self._configure_axis()
        if show_x:
            self._ax.set_xlabel("Simulation time [s]")
            self._ax.xaxis.tick_top()
            self._ax.xaxis.set_label_position('top')
            self._ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))  # fixes an evil formatting bug
        else:
            self._ax.xaxis.set_visible(False)
        self._ax.spines['top'].set_visible(col_header or show_x)
        self._ax.spines['bottom'].set_visible(col_footer)
        return self

    def _configure_axis(self):
        if self._label is not None:
            self._ax.set_ylabel(self._label)
        if self._legend:
            loc = self._legend_loc
            if loc is None:
                loc = 'upper right'
            self._ax.legend(self._legend, prop={'size': 12}, loc=loc, ncol=len(self._legend))

    def _create_primitive(self, color):
        return None

    def _create_primitives(self):
        self._ps = dict(zip(self._keys, map(lambda c: self._create_primitive(c), self._colors)))

    def update(self, data_provider):
        pass

    def get_artists(self):
        return self._ps.values()

    def update_axis(self, *x_lim):
        self._ax.set_xlim(*x_lim)

    def draw(self):
        for artist in self.get_artists():
            assert not isinstance(artist, list)
            self._ax.draw_artist(artist)


class TimePlotDual(object):
    def __init__(self):
        self._plots = []
        self._dynamic_plots = []

    def build(self, ax, show_x=False, **kwargs):
        assert self._plots
        self._dynamic_plots.append(self._plots[0].build(ax, show_x, **kwargs))
        if len(self._plots) > 1:
            twinx = ax.twinx()
            self._dynamic_plots.append(self._plots[1].build(twinx, show_x=False))
            twinx.spines['top'].set_visible(False)
            twinx.spines['bottom'].set_visible(False)
            twinx.spines['left'].set_visible(False)
            twinx.spines['right'].set_visible(False)
        return self

    def update(self, data_provider):
        for plot in self._dynamic_plots:
            plot.update(data_provider)

    def add_plot(self, plot):
        assert len(self._plots) < 2
        self._plots.append(plot)


class PhasePlot(Plot):
    def __init__(self, key, n_values, zero_is_value=False, y_pos=0, common_line_style=None, individual_line_styles=None,
                 label=None, legend=None, legend_loc=None, colors=None):
        self._n_values = n_values
        Plot.__init__(self, [key], label, legend, legend_loc, colors)
        assert legend is None or len(legend) == n_values
        assert len(self._colors) == n_values
        assert y_pos == 0 or np.abs(y_pos) >= 1
        self._drop_zero = not zero_is_value
        self._y_pos = y_pos
        self._line_styles = self._gen_line_styles(common_line_style if common_line_style else {},
                                                  individual_line_styles if individual_line_styles else [{}] * n_values)

    def _gen_line_styles(self, shared_ls, specific_lss):
        for specific_ls, color in zip(specific_lss, self._colors):
            ls = shared_ls.copy()
            if 'color' not in ls:
                ls['color'] = color
            ls.update(specific_ls)
            yield ls

    def _gen_colors_with_colormap(self, colormap):
        return colormap(np.linspace(0, 1, self._n_values))

    def _gen_colors_with_atom(self, atom):
        return [atom] * self._n_values

    def _configure_axis(self):
        Plot._configure_axis(self)
        self._ax.set_ylim(min(-1, self._y_pos), max(1, self._y_pos))
        self._ax.yaxis.set_ticks([])

    def _create_primitives(self):
        self._ps = {self._keys[0]: map(lambda ls: self._ax.plot([], [], **ls)[0], self._line_styles)}

    def get_artists(self):
        return self._ps[self._keys[0]]

    def update(self, data_provider):
        Plot.update(self, data_provider)
        key = self._keys[0]
        signal = data_provider.get_cont_data(self._keys, self._ax.get_xlim())[key]
        times, values = np.rollaxis(signal, 1)
        for value_id, ps in enumerate(self._ps[key], start=self._drop_zero):
            transformed_values = values.copy()
            transformed_values[np.where(values != value_id)] = np.NaN
            transformed_values[np.where(values == value_id)] = 0
            ps.set_data(np.array([times, transformed_values]))


class AnalogSignalPlot(Plot):
    def __init__(self, keys, label=None, legend=None, legend_loc=None, colors=None, y_lim=None, y_ticks=None,
                 y_ticks_right=True):
        Plot.__init__(self, keys, label, legend, legend_loc, colors)
        self._y_lim = y_lim
        self._y_ticks = y_ticks
        self._y_ticks_right = y_ticks_right

    def _configure_axis(self):
        Plot._configure_axis(self)
        if self._y_lim:
            assert len(self._y_lim) == 2
            self._ax.set_ylim(*self._y_lim)
        if self._y_ticks is not None:
            if isinstance(self._y_ticks, dict):
                self._ax.yaxis.set_ticks(self._y_ticks.keys())
                # TODO test this. Presumable map onto values is needed to retain order
                self._ax.set_yticklabels(self._y_ticks.values())
            else:
                assert isinstance(self._y_ticks, list)
                self._ax.yaxis.set_ticks(self._y_ticks)
        if self._y_ticks_right:
            self._ax.yaxis.tick_right()

    def _create_primitive(self, color):
        return self._ax.plot([], [], color=color)[0]

    def update(self, data_provider):
        Plot.update(self, data_provider)
        for key, signal in zip(self._keys, data_provider.get_cont_data(self._keys, self._ax.get_xlim())):
            self._ps[key].set_data(np.rollaxis(np.array(signal), 1))
        if not self._y_lim:
            self._ax.relim()
            self._ax.autoscale_view(True, True, True)


class SpikeTrainPlot(Plot):
    def __init__(self, keys, label=None, legend=None, legend_loc=None, colors=None, y_tick_filter=lambda ids: [],
                 y_tick_labels=lambda ids: map(str, ids), y_ticks_right=True):
        Plot.__init__(self, keys, label, legend, legend_loc, colors)
        self._y_tick_filter = y_tick_filter
        self._y_tick_labels = y_tick_labels
        self._y_ticks_right = y_ticks_right

    def _configure_axis(self):
        Plot._configure_axis(self)
        self._ax.set_ylim(-1, len(self._keys))

        y_ticks = self._y_tick_filter(range(len(self._keys)))
        if y_ticks:
            self._ax.yaxis.set_ticks(y_ticks)
            self._ax.set_yticklabels(self._y_tick_labels(y_ticks))
            if self._y_ticks_right:
                self._ax.yaxis.tick_right()
        else:
            self._ax.yaxis.set_ticks([])

    def _create_primitive(self, color):
        return self._ax.scatter([], [], color=color, marker='|', linewidth='1.5', s=20)

    def update(self, data_provider):
        Plot.update(self, data_provider)
        for key, times in zip(self._keys, data_provider.get_event_data(self._keys, self._ax.get_xlim())):
            # FIXME inefficient
            offsets = np.rollaxis(np.array([times, np.ones_like(times) * self._keys.index(key)]), 1)
            self._ps[key].set_offsets(offsets)
