from app.data.skill_components import SkillComponent
from app.data.components import Type

from app.engine import equations, action, item_funcs
from app.engine.game_state import game

# status plugins
class Unselectable(SkillComponent):
    nid = 'unselectable'
    desc = "Unit cannot be selected"
    tag = 'base'

    def can_select(self, unit) -> bool:
        return False

class CannotUseItems(SkillComponent):
    nid = 'cannot_use_items'
    desc = "Unit cannot use or equip any items"
    tag = 'base'

    def available(self, unit, item) -> bool:
        return False

class CannotUseMagicItems(SkillComponent):
    nid = 'cannot_use_magic_items'
    desc = "Unit cannot use or equip magic items"
    tag = 'base'

    def available(self, unit, item) -> bool:
        return not item_funcs.is_magic(unit, item)

class IgnoreAlliances(SkillComponent):
    nid = 'ignore_alliances'
    desc = "Unit will treat all units as enemies"
    tag = 'base'

    def check_ally(self, unit1, unit2) -> bool:
        return unit1 is unit2

    def check_enemy(self, unit1, unit2) -> bool:
        return unit1 is not unit2

class ChangeAI(SkillComponent):
    nid = 'change_ai'
    desc = "Unit's AI is forcibly changed"
    tag = 'base'

    expose = Type.AI

    def on_add(self, unit, skill):
        self.prev_ai = unit.ai
        unit.ai = self.value

    def on_remove(self, unit, skill):
        unit.ai = self.prev_ai

class ChangeBuyPrice(SkillComponent):
    nid = 'change_buy_price'
    desc = "Unit's buy price for items is changed"
    tag = 'base'

    expose = Type.Float

    def modify_buy_price(self, unit):
        return self.value

class ExpMultiplier(SkillComponent):
    nid = 'exp_multiplier'
    desc = "Unit receives a multiplier on exp gained"
    tag = 'base'

    expose = Type.Float

    def exp_multiplier(self, unit1, unit2):
        return self.value

class EnemyExpMultiplier(SkillComponent):
    nid = 'enemy_exp_multiplier'
    desc = "Unit gives a multiplier to the exp gained by others in combat"
    tag = 'base'

    expose = Type.Float

    def enemy_exp_multiplier(self, unit1, unit2):
        return self.value

class Locktouch(SkillComponent):
    nid = 'locktouch'
    desc = "Unit is able to unlock automatically"
    tag = 'base'

    def can_unlock(self, unit, region):
        return True

class SightRangeBonus(SkillComponent):
    nid = 'sight_range_bonus'
    desc = "Unit gains a bonus to sight range"
    tag = 'base'

    expose = Type.Int
    value = 3

    def sight_range(self, unit):
        return self.value

class DecreasingSightRangeBonus(SkillComponent):
    nid = 'decreasing_sight_range_bonus'
    desc = "Unit gains a bonus to sight range that decreases by 1 each turn"
    tag = 'base'

    expose = Type.Int
    value = 3

    def init(self):
        self.skill.data['torch_counter'] = 0

    def sight_range(self, unit):
        return max(0, self.value - self.skill.data['torch_counter'])

    def on_upkeep(self, actions, playback, unit):
        val = self.skill.data['torch_counter'] - 1
        action.do(action.SetObjData(self.skill, 'torch_counter', val))
