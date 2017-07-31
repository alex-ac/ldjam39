import random

import dice

class Location(object):
    def __init__(self, messages, state=None):
        super(Location, self).__init__()
        self._messages = messages
        if state is None:
            state = self.initial_state()
            state['objects'] = self.objects()

        self.state = state

    def initial_state(self):
        return {}

    @property
    def messages(self):
        return self._messages['locations'][self.key]

    @property
    def key(self):
        return None

    def objects(self):
        return []

    def actions(self, user):
        return [
            self.messages['go_to'][location]
            for location in self.nearby_locations()
        ]

    def handle_action(self, action, user):
        for location in self.nearby_locations():
            if self.messages['go_to'][location] == action:
                return location, ''
        return None, self._messages['wrong_action']

    def nearby_locations(self):
        return []

    def npcs(self, user):
        return []


class HomeSweetHome(Location):
    @property
    def key(self):
        return 'home_sweet_home'

    def initial_state(self):
        return {
            'gas_on': True,
            'table_inspected': False,
        }

    def objects(self):
        return ['kettle']

    def nearby_locations(self):
        return ['street']

    def actions(self, user):
        actions = Location.actions(self, user)
        if self.state['gas_on']:
            actions.append(self.messages['turn_off_gas'])
        else:
            actions.append(self.messages['turn_on_gas'])
        if all(good in user.inventory for good in [
                'pipes', 'kettle', 'pot']):
            actions.append(self.messages['build_alcohol_machine'])

        if not self.state.get('generator_installed') and 'generator' in user.inventory:
            actions.append(self.messages['install_generator'])
        if not self.state.get('alcohol_machine_installed') and 'alcohol_machine' in user.inventory:
            actions.append(self.messages['install_alcohol_machine'])
        if self.is_alcohol_requirements_satisfied(user):
            actions.append(self.messages['make_booze'])

        actions.append(self.messages['look_at_window'])
        actions.append(self.messages['inspect_table'])
        return actions

    def is_alcohol_machine_requirements_satisfied(self, user):
        return all(good in user.inventory for good in ('kettle', 'pot', 'pipes'))

    def is_alcohol_requirements_satisfied(self, user):
        return (
            all(good in user.inventory for good in ('sugar', 'barm', 'bottle')) and
            self.state.get('alcohol_machine_installed') and
            self.state.get('gas_on'))

    def handle_action(self, action, user):
        if self.state['gas_on'] and self.messages['turn_off_gas'] == action:
            self.state['gas_on'] = False
            return None, self.messages['gas_turned_off']
        if not self.state['gas_on'] and self.messages['turn_on_gas'] == action:
            self.state['gas_on'] = True
            if self.state.get('generator_installed'):
                user.win = True
            return None, self.messages['gas_turned_on']
        if self.messages['look_at_window'] == action:
            return None, self.messages['at_street']
        if not self.state['table_inspected'] and self.messages['inspect_table'] == action:
            self.state['table_inspected'] = True
            user.inventory.append('electric_company_reciepts')
            return None, self.messages['got_electric_company_receipts']
        if self.state['table_inspected'] and self.messages['inspect_table'] == action:
            return None, self.messages['nothing_found']
        if not self.state.get('generator_installed') and 'generator' in user.inventory and action == self.messages['install_generator']:
            if user.burned:
                return None, self.messages['burnt'].format(self._messages['objects']['generator'])
            if self.state['gas_on']:
                user.burned = True
                return None, self.messages['hot'].format(self._messages['objects']['generator'])
            self.state['generator_installed'] = True
            user.remove_one('generator')
            return None, self.messages['generator_installed']
        if self.is_alcohol_machine_requirements_satisfied(user) and action == self.messages['build_alcohol_machine']:
            user.remove_one('alcohol_machine_parts_list')
            user.remove_one('kettle')
            user.remove_one('pot')
            user.remove_one('pipes')
            user.inventory.append('alcohol_machine')
            return None, self.messages['alcohol_machine_built']
        if not self.state.get('alcohol_machine_installed') and 'alcohol_machine' in user.inventory and action == self.messages['install_alcohol_machine']:
            if user.burned:
                return None, self.messages['burnt'].format(self._messages['objects']['alcohol_machine'])
            if self.state['gas_on']:
                user.burned = True
                return None, self.messages['hot'].format(self._messages['objects']['alcohol_machine'])
            self.state['alcohol_machine_installed'] = True
            user.remove_one('alcohol_machine')
            return None, self.messages['alcohol_machine_installed']
        if self.is_alcohol_requirements_satisfied(user) and action == self.messages['make_booze']:
            user.remove_one('sugar')
            user.remove_one('barm')
            user.remove_one('bottle')
            user.inventory.append('booze')
            return None, self.messages['made_booze']
        return super(HomeSweetHome, self).handle_action(action, user)

    def description(self, user):
        text = self.messages['description']
        if self.state.get('generator_installed'):
            if self.state['gas_on']:
                text += ' ' + self.messages['generator_works'] + ' ' + self.messages['light']
            else:
                text += ' ' + self.messages['generator_stopped'] + ' ' + self.messages['no_light']
        else:
            text += ' ' + self.messages['no_light']
        if 'kettle' in self.state['objects']:
            text += ' ' + self.messages['kettle_on_gas']
        text += ' ' + self.messages['gas_on' if self.state['gas_on'] else 'gas_off']
        return text


class Street(Location):
    @property
    def key(self):
        return 'street'

    def description(self, user):
        return self.messages['description']

    def nearby_locations(self):
        return [
            'home_sweet_home',
            'electry_company',
            'hospital',
            'garage',
            'shop',
            'junkyard',
        ]

    def npcs(self, user):
        return [ 'genry' ]

class ElectricCompany(Location):
    @property
    def key(self):
        return 'electry_company'

    def description(self, user):
        text = self.messages['description']
        if not user.electrician_went_check:
            text += ' ' + self.messages['electrician']
        return text

    def nearby_locations(self):
        return ['street']

    def npcs(self, user):
        npcs = [
            'electric_company_administrator',
        ]
        if not user.electrician_went_check:
            npcs.append('electrician')
        return npcs

class Hospital(Location):
    @property
    def key(self):
        return 'hospital'

    def description(self, user):
        return self.messages['description']

    def nearby_locations(self):
        return ['street']

    def npcs(self, user):
        return ['doctor']


class Garage(Location):
    @property
    def key(self):
        return 'garage'

    def description(self, user):
        return self.messages['description']

    def nearby_locations(self):
        return ['street']

    def npcs(self, user):
        return ['mechanic']


class Shop(Location):
    @property
    def key(self):
        return 'shop'

    def description(self, user):
        return self.messages['description']

    def nearby_locations(self):
        return ['street']

    def npcs(self, user):
        return ['merchant']


class Junkyard(Location):
    @property
    def key(self):
        return 'junkyard'

    def description(self, user):
        return self.messages['description']

    def find_something(self):
        baseline = {
            'magnet': 1000,
            'copper_wire': 300,
            'piston': 750,
            'valve': 200,
            'bottle': 5,
            'pipes': 30,
            'kettle': 70,
            'pot': 50,
        }

        goods = {}
        for good, baseprice in baseline.iteritems():
            d = dice.run_3d6()
            if d < 7:
                continue

            price = int(11 * baseprice / d)

            goods[good] = price

        basevalue = 300
        d = dice.run_3d6()
        if d < 7:
            return None

        value = int(11 * basevalue / d)

        goodlist = goods.items()
        random.shuffle(goodlist)
        for good, price in goodlist:
            if value >= price:
                return good

        return None

    def actions(self, user):
        actions = Location.actions(self, user)
        actions.append(self.messages['try_find_something'])
        return actions

    def handle_action(self, action, user):
        if action == self.messages['try_find_something']:
            if self.state.get('last_lottery_turn', -11) + 10 < user.turn:
                self.state['last_lottery_turn'] = user.turn
                good = self.find_something()
                if good is None:
                    return None, self.messages['nothing_found']
                user.inventory.append(good)
                return None, self.messages['found'].format(good)
            else:
                return None, self.messages['already_searched']
        return super(Junkyard, self).handle_action(action, user)

    def nearby_locations(self):
        return ['street']


LOCATIONS = {
    'home_sweet_home': HomeSweetHome,
    'street': Street,
    'electry_company': ElectricCompany,
    'hospital': Hospital,
    'garage': Garage,
    'shop': Shop,
    'junkyard': Junkyard,
}
