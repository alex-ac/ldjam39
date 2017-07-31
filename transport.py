import abc

class Formatter(object):
    __meta__ = abc.ABCMeta

    @abc.abstractmethod
    def bold(self, text):
        pass

class User(object):
    def __init__(self, id, transport, first_name, last_name=None, username=None):
        super(User, self).__init__()
        self.id = id
        self.transport = transport
        self.first_name = first_name
        self.last_name = last_name
        self.username = username

    def pretty(self):
        if self.username:
            return '@' + self.username

        if self.last_name:
            return self.first_name + ' ' + self.last_name

        return self.first_name


class Chat(object):
    pass

class Message(object):
    def __init__(self, text, user, chat):
        super(Message, self).__init__()

        self.text = text
        self.user = user
        self.chat = chat

class Handler(object):
    __meta__ = abc.ABCMeta

    @abc.abstractmethod
    def on_message(self, transport, message):
        pass

class SerializedTransport(object):
    def __init__(self, mod, cls, *args, **kwargs):
        super(SerializedTransport, self).__init__()
        self.mod = mod
        self.cls = cls
        self.args = args
        selg.kwargs = kwargs

    def deserialize(self):
        mod = __import__(self.mod)
        cls = getattr(mod, self.cls)
        return cls(handler=None, *args, **kwargs)

class Transport(object):
    __meta__ = abc.ABCMeta
    def __init__(self, handler, *args, **kwargs):
        super(Transport, self).__init__()
        self.handler = handler
        self._args = args
        self._kwargs = kwargs

    def serialize(self):
        return SerializedTransport(
            self.__module__, self.__class__.__name__, *args, **kwargs)

    @abc.abstractmethod
    def send_message(self, chat, text, keyboard=None):
        pass

    @abc.abstractproperty
    def formatter(self):
        pass

    @abc.abstractmethod
    def keyboard(self, *buttons):
        pass
