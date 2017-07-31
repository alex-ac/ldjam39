import dice


class NPC(object):
    def __init__(self, messages, state=None):
        super(NPC, self).__init__()
        self._messages = messages
        if state is None:
            state = self.initial_state()
        self.state = state

    def initial_state(self):
        return {}

    @property
    def key(self):
        return None

    @property
    def name(self):
        return self.messages['name']

    @property
    def messages(self):
        return self._messages['npcs'][self.key]

    def greeting(self, user):
        return 'What?', None

    def talk(self, text, user):
        return 'What have you said?', None

class Electrician(NPC):
    @property
    def key(self):
        return 'electrician'

    def initial_state(self):
        return {
            'sleeping': True,
        }

    def make_phrases(self, user):
        if not user.filled_request:
            return None

        phrases = []
        phrases.append(self.messages['check_blackout'])

        phrases.append(self.messages['nothing'])
        return phrases

    def greeting(self, user):
        return self.messages['greeting'], self.make_phrases(user)

    def talk(self, text, user):
        if 'booze' not in user.inventory and text == self.messages['check_blackout']:
            return self.messages['check_requirements'], self.make_phrases(user)
        if 'booze' in user.inventory and text == self.messages['check_blackout']:
            user.remove_one('booze')
            user.electrician_went_check = True
            return self.messages['will_check'], None
        if text == self.messages['nothing']:
            return 'Ouh-mn-mn...', None
        return super(Electrician, self).talk(text, user)


class ElectricCompanyAdministrator(NPC):
    @property
    def key(self):
        return 'electric_company_administrator'

    def initial_state(self):
        return {
            'asked': False,
            'request_accepted': False,
        }

    def make_phrases(self):
        phrases = []
        phrases.append(self.messages['ask_whats_a_reason'])
        if self.state['asked']:
            phrases.append(self.messages['try_fill_request'])
        phrases.append(self.messages['nothing'])
        return phrases

    def greeting(self, user):
        return self.messages['greeting'], self.make_phrases()

    def talk(self, text, user):
        if text == self.messages['ask_whats_a_reason']:
            self.state['asked'] = True
            return self.messages['no_info'], self.make_phrases()
        if ('electric_company_reciepts' not in user.inventory and
                text == self.messages['try_fill_request']):
            return self.messages['request_prerequesties'], self.make_phrases()
        if ('electric_company_reciepts' in user.inventory and
                text == self.messages['try_fill_request']):
            self.state['request_accepted'] = True
            user.remove_one('electric_company_reciepts')
            user.filled_request = True
            return self.messages['request_accepted'], self.make_phrases()
        if text == self.messages['nothing']:
            return self.messages['go_out'], None
        return super(ElectricCompanyAdministrator, self).talk(text, user)

class Doctor(NPC):
    @property
    def key(self):
        return 'doctor'

    def make_phrases(self, user):
        phrases = []
        phrases.append(self.messages['ask_about_light'])
        if user.burned:
            phrases.append(self.messages['heal_me'])
        phrases.append(self.messages['nothing'])
        return phrases

    def greeting(self, user):
        return self.messages['greeting'], self.make_phrases(user)

    def talk(self, text, user):
        if text == self.messages['ask_about_light']:
            user.know_about_generator = True
            return self.messages['backup_generator'], self.make_phrases(user)
        if text == self.messages['nothing']:
            return self.messages['be_careful'], None
        if user.burned and text == self.messages['heal_me']:
            user.burned = False
            return self.messages['healed'], self.make_phrases(user)
        return super(Doctor, self).talk(text, user)


class Mechanic(NPC):
    @property
    def key(self):
        return 'mechanic'

    def make_phrases(self, user):
        phrases = []
        if user.know_about_generator and not self.state.get('generator_builded'):
            phrases.append(self.messages['can_you_build_generator'])
            if self.is_generator_requirements_satisfied(user):
                phrases.append(self.messages['build_generator'])
        phrases.append(self.messages['nothing'])
        return phrases

    def greeting(self, user):
        return self.messages['greeting'], self.make_phrases(user)

    def is_generator_requirements_satisfied(self, user):
        return (all(good in user.inventory
                for good in [
                    'generator_requirments_list',
                    'magnet',
                    'valve',
                    'piston',
                    'kettle']
                ) and user.money >= 50)

    def talk(self, text, user):
        if user.know_about_generator and not self.state.get('generator_builded'):
            if text == self.messages['can_you_build_generator']:
                if 'generator_requirments_list' not in user.inventory:
                    user.inventory.append('generator_requirments_list')
                return self.messages['generator'], self.make_phrases(user)
            if (text == self.messages['build_generator'] and
                    self.is_generator_requirements_satisfied(user)):
                user.remove_one('magnet')
                user.remove_one('piston')
                user.remove_one('valve')
                user.remove_one('kettle')
                user.remove_one('generator_requirments_list')
                user.money -= 50
                user.inventory.append('generator')
                self.state['generator_builded'] = True
                return self.messages['generator_builded'], self.make_phrases(user)
        if text == self.messages['nothing']:
            return self.messages['bye'], None
        return super(Mechanic, self).talk(text, user)


class Genry(NPC):
    @property
    def key(self):
        return 'genry'

    def make_phrases(self, user):
        phrases = []
        phrases.append(self.messages['ask_about_machine'])
        phrases.append(self.messages['nothing'])
        return phrases

    def greeting(self, user):
        return self.messages['greeting'].format(user.name.replace('*', r'\*').replace('_', '\_')), self.make_phrases(user)

    def talk(self, text, user):
        if text == self.messages['ask_about_machine']:
            if 'alcohol_machine_parts_list' not in user.inventory:
                user.inventory.append('alcohol_machine_parts_list')
            return self.messages['machine'], self.make_phrases(user)
        if text == self.messages['nothing']:
            return self.messages['bye'], None
        return super(Genry, self).talk(text, user)


class Merchant(NPC):
    baseline = {
        'magnet': 1000,
        'copper_wire': 300,
        'piston': 750,
        'valve': 200,
        'booze': 100,
        'bottle': 20,
        'sugar': 20,
        'barm': 20,
        'kettle': 100,
        'pipes': 50,
        'pot': 100,
    }

    @property
    def key(self):
        return 'merchant'

    def sell_price(self, good):
        d = self.state['goods'][good]
        if d < 7: # Nothing to sell
            return None

        return int(11 * self.baseline[good] / d)

    def buy_price(self, good):
        if good not in self.baseline:
            # Merchant will not buy/sell this.
            return None

        d = self.state['goods'][good]
        if d < 7: # Use x1.5 as a limit
            return int(self.baseline[good] * 1.2)

        # Get a 0.8 of sell price.
        return int(self.sell_price(good) * 0.8)

    def make_phrases(self, user):
        phrases = []
        if self.state.get('buying'):
            for good in self.baseline:
                price = self.sell_price(good)
                if price is None:
                    continue

                phrases.append(
                    self.messages['buy'].format(
                        self._messages['objects'][good], price))

        elif self.state.get('selling'):
            for good in user.inventory:
                price = self.buy_price(good)
                if price is None:
                    continue

                phrases.append(
                    self.messages['sell'].format(
                        self._messages['objects'][good], price))
        else:
            phrases.append(self.messages['wanna_buy'])
            phrases.append(self.messages['wanna_sell'])
        phrases.append(self.messages['nothing'])
        return phrases

    def make_goods(self):
        goods = {
            good: dice.run_3d6()
            for good in self.baseline
        }

        return goods

    def greeting(self, user):
        if self.state.get('goods_changed_turn', -50) + 50 < user.turn:
            self.state['goods_changed_turn'] = user.turn
            self.state['goods'] = self.make_goods()

        return self.messages['greeting'], self.make_phrases(user)

    def talk(self, text, user):
        if self.state.get('buying'):
            if text == self.messages['nothing']:
                self.state['buying'] = False
                return self.messages['something_more'], self.make_phrases(user)

            for good in self.baseline:
                price = self.sell_price(good)
                if good is None:
                    continue

                if text != self.messages['buy'].format(
                        self._messages['objects'][good], price):
                    continue

                if user.money >= price:
                    user.money -= price
                    user.inventory.append(good)
                    self.state['goods'][good] -= 1
                    self.state['goods_changed_turn'] = user.turn
                    return self.messages['bought'].format(
                        self._messages['objects'][good], price), self.make_phrases(user)
                else:
                    return self.messages['not_enought_money'].format(
                        self._messages['objects'][good], price), self.make_phrases(user)
        elif self.state.get('selling'):
            if text == self.messages['nothing']:
                self.state['selling'] = False
                return self.messages['something_more'], self.make_phrases(user)

            for good in user.inventory:
                price = self.buy_price(good)
                if price is None:
                    continue

                if text != self.messages['sell'].format(self._messages['objects'][good], price):
                    continue

                user.remove_one(good)
                user.money += price
                self.state['goods'][good] += 1
                self.state['goods_changed_turn'] = user.turn
                return self.messages['sold'].format(self._messages['objects'][good], price), self.make_phrases(user)
        else:
            if text == self.messages['wanna_buy']:
                self.state['buying'] = True
                return self.messages['what'], self.make_phrases(user)

            if text == self.messages['wanna_sell']:
                self.state['selling'] = True
                return self.messages['what'], self.make_phrases(user)

            if text == self.messages['nothing']:
                del self.state['goods']
                return self.messages['come_again'], None

        return super(Merchant, self).talk(text, user)

NPCS = {
    'electrician': Electrician,
    'electric_company_administrator': ElectricCompanyAdministrator,
    'doctor': Doctor,
    'mechanic': Mechanic,
    'merchant': Merchant,
    'genry': Genry,
}
