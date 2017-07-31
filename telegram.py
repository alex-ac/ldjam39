import datetime
import logging

import marshmallow
import requests
import transport


logger = logging.getLogger(__name__)


class Response(object):
    def __init__(self, ok, result=None, description=None):
        super(Response, self).__init__()
        self.ok = ok
        self.result = result
        self.description = description

    def __repr__(self):
        return '<Response ok={} description={} result={}>'.format(
            self.ok, self.description, self.result)


class ResponseSchema(marshmallow.Schema):
    ok = marshmallow.fields.Boolean(required=True)
    result = marshmallow.fields.Raw()
    description = marshmallow.fields.String()

    @marshmallow.post_load
    def make_response(self, data):
        return Response(**data)


class User(transport.User):
    def __init__(self, language_code=None, **kwargs):
        super(User, self).__init__(transport='telegram', **kwargs)
        self.language_code = language_code

    def __repr__(self):
        return '<User id={} first_name={} last_name={} username={} language_code={}'.format(
            self.id, self.first_name, self.last_name, self.username, self.language_code)


class UserSchema(marshmallow.Schema):
    id = marshmallow.fields.Integer(required=True)
    first_name = marshmallow.fields.String(required=True)
    last_name = marshmallow.fields.String()
    username = marshmallow.fields.String()
    language_code = marshmallow.fields.String()

    @marshmallow.post_load
    def make_user(self, data):
        return User(**data)


class Chat(transport.Chat):
    def __init__(self, id, type):
        super(Chat, self).__init__()
        self.id = id
        self.type = type

    def __repr__(self):
        return '<Chat id={} type={}>'.format(
            self.id, self.type)


class ChatSchema(marshmallow.Schema):
    id = marshmallow.fields.Integer(required=True)
    type = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.OneOf(
            ('private', 'group', 'supergroup', 'channel')))

    @marshmallow.post_load
    def make_chat(self, data):
        return Chat(**data)


class Message(transport.Message):
    def __init__(self, message_id, date, **kwargs):
        super(Message, self).__init__(**kwargs)
        self.message_id = message_id
        self.date = date

    def __repr__(self):
        return '<Message message_id={} date={} chat={} user={} text={}>'.format(
            self.message_id, self.date, self.chat, self.user, self.text)


class TimestampField(marshmallow.fields.Integer):
    def _serialize(self, value, attr, data):
        value = (value - datetime.datetime.utcfromtimestamp(0)).total_seconds()
        value = time.mktime(value.timetuple())
        return super(TimestampField, self)._serialize(value, attr, data)

    def _deserialize(self, value, attr, data):
        value = super(TimestampField, self)._serialize(value, attr, data)
        return datetime.datetime.utcfromtimestamp(value)


class MessageSchema(marshmallow.Schema):
    message_id = marshmallow.fields.Integer(required=True)
    date = TimestampField(required=True)
    chat = marshmallow.fields.Nested(ChatSchema, required=True)
    user = marshmallow.fields.Nested(
        UserSchema, load_from='from', dump_to='from')
    text = marshmallow.fields.String()

    @marshmallow.post_load
    def make_message(self, data):
        return Message(**data)


class Update(object):
    def __init__(self, update_id, message=None):
        super(Update, self).__init__()
        self.update_id = update_id
        self.message = message

    def __repr__(self):
        return '<Update update_id={} message={}>'.format(
            self.update_id,
            self.message)


class UpdateSchema(marshmallow.Schema):
    update_id = marshmallow.fields.Integer(required=True)
    message = marshmallow.fields.Nested(MessageSchema)

    @marshmallow.post_load
    def make_update(self, data):
        return Update(**data)


class Error(Exception):
    pass

class Formatter(transport.Formatter):
    def bold(self, text):
        return '*' + text.strip() + '*'


class Transport(transport.Transport):
    def __init__(self, handler, token):
        super(Transport, self).__init__(handler)
        self.session = requests.Session()
        self.token = token
        self.response_schema = ResponseSchema(strict=True)
        self.update_schema = UpdateSchema(strict=True)
        self.message_schema = MessageSchema(strict=True)
        self.last_update = None

    def keyboard_as_dict(self, keyboard):
        return [
            [ button ]
            for button in keyboard
        ]

    def request(self, endpoint, params=None):
        url = 'https://api.telegram.org/bot{}/{}'.format(self.token, endpoint)
        method = 'POST' if params else 'GET'
        logger.info('%s %s', method, url)
        return self.response_schema.load(
            self.session.request(
                method, url, json=params)
            .json()).data

    def get_updates(self):
        params = None
        if self.last_update:
            params = { 'offset': self.last_update + 1 }
        response = self.request('getUpdates', params=params)
        if not response.ok:
            raise Error(response.description)
        return self.update_schema.load(response.result, many=True).data

    def send_message(self, chat, text, disable_notification=True, keyboard=None):
        params = {
            'chat_id': chat.id,
            'text': text,
            'disable_notification': disable_notification,
            'parse_mode': 'Markdown',
        }
        if keyboard:
            params['reply_markup'] = {
                'one_time_keyboard': True,
                'keyboard': self.keyboard_as_dict(keyboard),
            }
        response = self.request('sendMessage', params=params)
        if not response.ok:
            raise Error(response.description)

        return self.message_schema.load(response.result).data

    def run(self):
        for update in self.get_updates():
            self.handle(update)
            self.last_update = update.update_id

    @property
    def formatter(self):
        return Formatter()

    def handle(self, update):
        if update.message:
            self.handler.on_message(self, update.message)
        else:
            logger.info('Unhandled update: %s', update)
