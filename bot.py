#!/usr/bin/env python

import argparse
import datetime
import logging
import os
import sys
import time

import mongoengine
import yaml

import hotreload
import telegram
import transport
import locations
import npcs

logger = logging.getLogger(__name__)

class Score(mongoengine.Document):
    name = mongoengine.StringField()
    turns = mongoengine.LongField()
    money = mongoengine.LongField()
    score = mongoengine.LongField()


class User(mongoengine.Document):
    user_id = mongoengine.LongField()
    turn = mongoengine.LongField()
    in_intro = mongoengine.BooleanField()
    name = mongoengine.StringField()
    locations = mongoengine.DictField()
    inventory = mongoengine.ListField(mongoengine.StringField())
    current_npc = mongoengine.StringField()
    npcs = mongoengine.DictField()
    current_location = mongoengine.StringField()
    know_about_generator = mongoengine.BooleanField()
    filled_request = mongoengine.BooleanField()
    electrician_went_check = mongoengine.BooleanField()
    burned = mongoengine.BooleanField()
    money = mongoengine.IntField()
    win = mongoengine.BooleanField()

    def remove_one(self, obj_to_remove):
        for i, obj in enumerate(self.inventory):
            if obj == obj_to_remove:
                del self.inventory[i]
                break

class Bot(transport.Handler):
    def reset(self, user):
        user.turn = 0
        user.in_intro = True
        user.name = None
        user.locations =  {}
        user.current_location = 'home_sweet_home'
        user.inventory = []
        user.current_npc = None
        user.know_about_generator = False
        user.filled_request = False
        user.electrician_went_check = False
        user.burned = False
        user.win = False
        user.money = 100

    def on_start(self, transport, chat, user):
        user.turn = 0
        user.in_intro = True
        user.locations = {}
        user.current_location = 'home_sweet_home'
        user.inventory = []
        user.current_npc = None
        user.know_about_generator = False
        user.filled_request = False
        user.electrician_went_check = False
        user.burned = False
        user.win = False
        user.money = 100
        user.save()
        transport.send_message(
            chat, self.messages['intro'], keyboard=self.keyboards['intro'])

    def handle_intro(self, transport, message, user):
        user.in_intro = False
        user.save()
        if not user.name:
            buttons = []
            buttons.append(message.user.first_name)
            if message.user.username:
                buttons.append(message.user.username)
            transport.send_message(
                message.chat, self.messages['ask_name'],
                keyboard=buttons)
        else:
            self.start(transport, message.chat, user)

    def set_name(self, transport, message, user):
        user.name = message.text
        self.start(transport, message.chat, user)

    def load_npc(self, user):
        npc = npcs.NPCS[user.current_npc](
            self.messages, user.npcs.get(user.current_npc))
        user.npcs[user.current_npc] = npc.state
        return npc

    def load_location(self, user):
        location = locations.LOCATIONS[user.current_location](
            self.messages, user.locations.get(user.current_location))
        user.locations[user.current_location] = location.state
        return location

    def make_location_keyboard(self, user, location):
        buttons = []
        buttons.append(self.messages['show_inventory'])
        for o in location.state['objects']:
            buttons.append(self.messages['take'].format(o))
        buttons.extend(location.actions(user))
        for npc_id in location.npcs(user):
            npc = npcs.NPCS[npc_id](self.messages)
            buttons.append(self.messages['talk'].format(npc.name))
        return buttons

    def start(self, transport, chat, user):
        user.current_location = 'home_sweet_home'
        location = self.load_location(user)
        user.save()
        transport.send_message(
            chat,
            self.messages['story'] + ' ' + location.description(user),
            keyboard=self.make_location_keyboard(user, location))

    def show_inventory(self, transport, user):
        if user.inventory:
            return self.messages['inventory'].format(
                '\n'.join(
                    transport.formatter.bold(self.messages['objects'][obj]) + ': ' +
                    self.messages['objects_descriptions'][obj]
                    for obj in user.inventory) +
                    '\n' + transport.formatter.bold(self.messages['money']) + ': ' + str(user.money))
        return self.messages['inventory_money'].format(user.money)

    def on_turn(self, transport, chat, text, user):
        user.turn += 1
        action_result = None
        if user.current_npc is not None:
            npc = self.load_npc(user)
            npc_phrase, phrases = npc.talk(text, user)
            action_result = '*{}:* {}'.format(npc.name, npc_phrase)
            if phrases is None:
                user.current_npc = None
                action_result += '\n\n'
            else:
                user.save()
                return transport.send_message(chat,
                    action_result,
                    keyboard=phrases)
        location = self.load_location(user)
        new_location = None
        if action_result is None and self.messages['show_inventory'] == text:
            action_result = self.show_inventory(transport, user)
        if action_result is None:
            for npc_id in location.npcs(user):
                npc = npcs.NPCS[npc_id](self.messages)
                if self.messages['talk'].format(npc.name) == text:
                    user.current_npc = npc.key
                    npc = self.load_npc(user)
                    npc_phrase, phrases = npc.greeting(user)
                    action_result = '*{}:* {}'.format(npc.name, npc_phrase)
                    if phrases is None:
                        user.current_npc = None
                        action_result += '\n\n'
                    else:
                        user.save()
                        return transport.send_message(chat,
                            action_result,
                            keyboard=phrases)
                    break
        if action_result is None:
            for i, o in enumerate(location.state['objects']):
                if self.messages['take'].format(o) == text:
                    action_result = self.messages['took'].format(o)
                    user.inventory.append(o)
                    del location.state['objects'][i]
                    break
        if action_result is None:
            new_location, action_result = location.handle_action(text, user)
        user.locations[location.key] = location.state
        if new_location:
            user.current_location = new_location
            location = self.load_location(user)
        user.save()
        transport.send_message(
            chat, action_result + ' ' + location.description(user),
            keyboard=self.make_location_keyboard(user, location))

    def on_help(self, transport, chat):
        transport.send_message(
            chat, self.messages['help'])

    def on_win(self, transport, chat, user):
        Score(name=user.name, turns=user.turn,
              money=user.money, score=50*user.turn + user.money).save()
        transport.send_message(
            chat, self.messages['you_won'].format(
                user.turn, user.money, 50*user.turn + user.money))
        self.highscores(transport, chat)

    def highscores(self, transport, chat):
        highscores = Score.objects.order_by('-score')[:10]
        transport.send_message(
            chat, self.messages['highscores'].format(
                '\n'.join(
                    self.messages['highscore'].format(
                        i,
                        transport.formatter.bold(score.name.replace('*', r'\*').replace('_', r'\_')),
                        score.turns, score.money, score.score)
                    for i, score in enumerate(highscores))))

    def on_message(self, transport, message):
        logger.info('%s: %s', message.user.pretty(), message.text)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(script_dir, 'messages.yaml')) as f:
            self.messages = yaml.load(f)
        with open(os.path.join(script_dir, 'keyboards.yaml')) as f:
            self.keyboards = yaml.load(f)

        user = User.objects(user_id=message.user.id).first()
        if user is None:
            user = User(user_id=message.user.id, turn=0, in_intro=True)
            return self.on_start(transport, message.chat, user)
        if message.text == '/help':
            return self.on_help(transport, message.chat)
        if message.text == '/start':
            return self.on_start(transport, message.chat, user)
        if message.text == '/highscores':
            return self.highscores(transport, message.chat)

        # development cheats {
        if message.text == '/reset':
            self.reset(user)
            return self.on_start(transport, message.chat, user)
        if message.text.startswith('/pleasegiveme '):
            good = message.text[len('/pleasegiveme '):]
            if good in self.messages['objects']:
                user.inventory.append(good)
        if message.text.startswith('/drop '):
            good = message.text[len('/drop '):]
            user.remove_one(good)
        if message.text.startswith('/pleasegivememoney'):
            user.money += 100
        # } cheats

        if user.win:
            return

        if user.in_intro:
            return self.handle_intro(transport, message, user)
        if not user.name:
            return self.set_name(transport, message, user)

        self.on_turn(transport, message.chat, message.text, user)
        if user.win:
            self.on_win(transport, message.chat, user)


def run():
    logging.basicConfig(level='INFO')
    parser = argparse.ArgumentParser()
    token = os.environ.get('TOKEN')
    db_url = os.environ.get('DB_URL')
    if not token:
        parser.add_argument('token')
    if not db_url:
        parser.add_argument('dburl')
    parser.add_argument('--hotreload', default=False, action='store_true')
    parser.add_argument('--hotreload-internal', default=False, action='store_true')
    args = parser.parse_args()
    if not token:
        token = args.token
    if not db_url:
        db_url = args.dburl

    if args.hotreload:
        command = [sys.executable, sys.argv[0], '--hotreload-internal', args.token, args.dburl]
        return hotreload.run(command)

    db = mongoengine.connect('default', host=db_url)
    bot = Bot()
    transport = telegram.Transport(bot, token)
    if args.hotreload_internal:
        reload_watcher = hotreload.ReloadWatcher()

    try:
        while True:
            transport.run()
            if args.hotreload_internal:
                reload_watcher.reload_if_needed()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.exception('Stopping.')
        if not args.hotreload_internal:
            raise
    except hotreload.NeedReload as e:
        logger.info(e.message)
        return 1

if __name__ == '__main__':
    sys.exit(run())
