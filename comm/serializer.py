import ast

SERIALIZERS = {}


class Serializer(object):
    def serialize(self, obj):
        pass

    def deserialize(self, msg):
        pass


class ReprSerializer(Serializer):
    def serialize(self, obj):
        return repr(obj)

    def deserialize(self, msg):
        return ast.literal_eval(msg)


SERIALIZERS['repr'] = ReprSerializer()

try:
    import ujson


    class UJsonSerializer(Serializer):
        def serialize(self, obj):
            return ujson.encode(obj)

        def deserialize(self, msg):
            return ujson.decode(msg)


    # WARNING: json will transform tuples to strings; this can lead to errors depending on the sent data structures
    SERIALIZERS['ujson'] = UJsonSerializer()

except ImportError:
    pass
