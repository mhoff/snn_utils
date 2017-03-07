
class AsyncSender(object):
    def send(self, serialized_data):
        pass

    def close(self):
        pass


class AsyncReceiver(object):
    def has_data(self):
        pass

    def get_data(self):
        pass

    def close(self):
        pass
