import UserDict
import collections
import itertools


def _default(value, fallback, not_set=None):
    return fallback if value == not_set else value


def _merge(*dicts, **kwargs):
    result = {}
    for d in dicts:
        if d is not None:
            result.update(d)
    result.update(kwargs)
    return result


class MusicPort(UserDict.UserDict):
    """A MusicPort represents the local proxy for an either incoming or outgoing MUSIC connection.

    :param name: The absolute path of this port, e.g. "node.in".
    :param params: MUSIC parameters for mapping the port.

    :Example:

    port = MusicPort("node.in", {'accLatency': 0, 'width': 10})
    print("name = ".format(port.name))
    print("parameters: {}".format(port.data)
    assert 'accLatency' in port
    assert port['width'] == 10

    """

    CONT_IN = collections.namedtuple('CONT_IN', ['maxBuffered', 'perm', 'base', 'interpolate', 'delay'])
    CONT_OUT = collections.namedtuple('CONT_OUT', ['maxBuffered', 'perm', 'base'])
    EVENT_IN = collections.namedtuple('EVENT_IN', ['maxBuffered', 'perm', 'base', 'index_type', 'size', 'accLatency'])
    EVENT_OUT = collections.namedtuple('EVENT_OUT', ['maxBuffered', 'perm', 'base', 'index_type', 'size'])

    def __init__(self, name, params=None):
        UserDict.UserDict.__init__(self, dict=params)
        self.name = name

    def __repr__(self):
        return self.name

    def subset(self, keys, strict=True):
        result = dict([(k, self[k]) for k in keys if k in self.keys()])
        assert not strict or len(result) == len(keys), "Missing parameters: {}".format([k for k in self.keys()
                                                                                        if k not in keys])
        return result


class Node(object):
    """A Node represents a named MPI process group managed by MUSIC.

    :param name: The name of the node, e.g. "reward_generator".
    :param binary: The executable file which is run by all processes, e.g. "reward_gen.py".
    :param host: The host to run the processes on, e.g. "localhost".
    :param node_params: The node parameters supplied via the MUSIC configuration file.
    :param port_params: Mapping of port names to corresponding parameter sets, e.g. {'in': {'width': 10}}.

    :Example:

    node = Node('reward_generator', 'reward_gen.py', 'node15', {'music_timestep': 0.01}, {'in': {'width': 10}})
    print("name = ".format(node.name))
    print("host = ".format(port.host))
    print("node parameters = ".format(node.params()))

    in_port = node.port('in')
    assert in_port['width'] == 10
    assert in_port.name == "reward_generator.in"

    """

    def __init__(self, name, binary, host, n_processes, node_params, port_params):
        self.name = name
        self.host = host
        self.n_processes = n_processes
        self._node_params = _merge(node_params, binary=binary, np=n_processes)
        self._port_params = port_params
        self._ports = {}

    def _create_port(self, port_name):
        port = self._ports.get(port_name, None)
        if port is None:
            port = MusicPort("{}.{}".format(self.name, port_name), params=self._port_params[port_name])
            self._ports[port_name] = port
        return port

    def params(self):
        return self._node_params

    def ports(self):
        return self._ports

    def port(self, port_name):
        return self._create_port(port_name)

    def __getitem__(self, port_name):
        return self.port(port_name)


class MUSICConfig(object):
    def __init__(self, default_host='localhost', global_params=None, port_defaults=None):
        self._default_host = default_host
        self._global_params = _default(global_params, {})
        self._port_defaults = _default(port_defaults, {})
        self._nodes = {}
        self._connections = []

        self._unresolved_port_groups = []

    def _add_node(self, node):
        assert node.name not in self._nodes
        self._nodes[node.name] = node
        return node

    def _port_params(self, port_defaults, *port_param_dicts):
        port_defaults = _merge(self._port_defaults, port_defaults)
        port_params = collections.defaultdict(lambda: port_defaults.copy())
        for port_param_dict in port_param_dicts:
            if port_param_dict is not None:
                assert isinstance(port_param_dict, dict)
                for name, params in port_param_dict.items():
                    port_params[name].update(params)
        return port_params

    def add_node(self, name, binary, host=None, n_processes=1, node_params=None, port_defaults=None, port_params=None):
        return self._add_node(Node(name, binary, _default(host, self._default_host), n_processes, node_params,
                                   self._port_params(port_defaults, port_params)))

    def add_nest_node(self, name, binary, host=None, n_processes=1, node_params=None, port_defaults=None,
                      port_params=None, pop_sizes=None):
        port_widths = dict([(port, {'width': int(width)}) for port, width in _default(pop_sizes, {}).items()])
        port_params = self._port_params(port_defaults, port_params, port_widths)
        return self.add_node(name, binary, host, n_processes, node_params, port_defaults=None, port_params=port_params)

    def add_connection(self, src_node, trg_node, src_port='out', trg_port='in', width=None):
        src_port = src_node.port(src_port)
        trg_port = trg_node.port(trg_port)

        ports = {src_port.name, trg_port.name}

        widths = set(w for w in [width, src_port.get('width', None), trg_port.get('width', None)] if w is not None)
        assert len(widths) <= 1, "Inconsistent widths for ports {}: {}".format(ports, widths)
        if widths:
            width = widths.pop()

        if width is not None:
            for port in ports:
                assert 'width' not in port or port['width'] == width
                src_port['width'] = width
            for pg in [pg for pg in self._unresolved_port_groups if pg.intersection(ports)]:
                self._unresolved_port_groups.remove(pg)
                for port in pg:
                    assert 'width' not in port
                    port['width'] = width
        else:
            port_groups = [pg for pg in self._unresolved_port_groups if pg.intersection(ports)]
            for pg in port_groups:
                self._unresolved_port_groups.remove(pg)
            self._unresolved_port_groups.append(set.union(ports, *port_groups))

        self._connections.append((src_port, trg_port))

    def __getitem__(self, node_name):
        assert node_name in self._nodes
        return self._nodes[node_name]

    def nodes(self):
        return self._nodes

    def nodes_sizes(self):
        return dict([(name, node.n_processes) for name, node in self._nodes.items()])

    def connections(self):
        if self._unresolved_port_groups:
            raise ValueError("The width of the following connected port groups could not be resolved:\n{}"
                             .format("\n".join(["  - [{}]".format(", ".join(map(str, pg)))
                                                for pg in self._unresolved_port_groups])))
        return [(p1, p2, p1['width']) for p1, p2 in self._connections]

    def globals(self):
        return self._global_params


def gen_socket_ports(node_sizes, base_port):
    port_gen = itertools.count(base_port)
    result = {}
    for node, size in node_sizes.items():
        assert size > 0
        for rank in range(size):
            result[(node, rank)] = next(port_gen)
        if size == 1:
            result[node] = result[(node, 0)]
    return result

