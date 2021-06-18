from app.engine.sound import SOUNDTHREAD
from app.engine.state import MapState
from app.engine.game_state import game
from app.engine import action, menus, item_system
from app.engine.objects.item import ItemObject

class TradeState(MapState):
    name = 'trade'

    def has_traded(self):
        action.do(action.HasTraded(self.initiator))

    def start(self):
        game.cursor.hide()
        self.initiator = game.cursor.cur_unit
        self.initiator.sprite.change_state('chosen')
        self.partner = game.cursor.get_hover()

        self.menu = menus.Trade(self.initiator, self.partner, self.initiator.items, self.partner.items)

    def do_trade(self):
        item1 = self.menu.selected_option().get()
        item2 = self.menu.get_current_option().get()

        if self.menu.other_hand[0] == 0:
            self.item1_owner = self.initiator
        else:
            self.item1_owner = self.partner
        if self.menu.selecting_hand[0] == 0:
            self.item2_owner = self.initiator
        else:
            self.item2_owner = self.partner

        if (item1 is item2) or \
                (isinstance(item1, ItemObject) and item_system.locked(self.item1_owner, item1)) or \
                (isinstance(item2, ItemObject) and item_system.locked(self.item2_owner, item2)):
            self.menu.unset_selected_option()
            SOUNDTHREAD.play_sfx('Error')
            return

        if self.menu.other_hand[0] == 0:
            if self.menu.selecting_hand[0] == 0:
                action.do(action.TradeItem(self.initiator, self.initiator, item1, item2))
            else:
                action.do(action.TradeItem(self.initiator, self.partner, item1, item2))
        else:
            if self.menu.selecting_hand[0] == 0:
                action.do(action.TradeItem(self.partner, self.initiator, item1, item2))
            else:
                action.do(action.TradeItem(self.partner, self.partner, item1, item2))
        self.has_traded()

        self.menu.unset_selected_option()
        self.menu.update_options(self.initiator.items, self.partner.items)

    def back(self):
        game.state.back()
        game.state.back()

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')

        if event == 'RIGHT':
            if self.menu.move_right():
                SOUNDTHREAD.play_sfx('TradeRight')
        elif event == 'LEFT':
            if self.menu.move_left():
                SOUNDTHREAD.play_sfx('TradeRight')

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            if self.menu.selected_option():
                self.menu.unset_selected_option()
            else:
                self.back()

        elif event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            if self.menu.selected_option():
                self.do_trade()
            else:
                self.menu.set_selected_option()

        elif event == 'INFO':
            self.menu.toggle_info()

    def update(self):
        super().update()
        self.menu.update()

    def draw(self, surf):
        surf = super().draw(surf)
        self.menu.draw(surf)
        return surf

class CombatTradeState(TradeState):
    name = 'combat_trade'

    def back(self):
        game.state.back()

class PrepTradeState(TradeState):
    name = 'prep_trade'

    def has_traded(self):
        # Prep Trade doesn't use up your turn
        pass

    def start(self):
        self.bg = game.memory['prep_bg']
        self.initiator = game.memory['unit1']
        self.partner = game.memory['unit2']

        self.menu = menus.Trade(self.initiator, self.partner, self.initiator.items, self.partner.items)

        game.state.change('transition_in')
        return 'repeat'

    def back(self):
        game.state.back()

    def update(self):
        self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.menu.draw(surf)
        return surf
