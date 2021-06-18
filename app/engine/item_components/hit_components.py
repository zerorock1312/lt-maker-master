from app.utilities import utils

from app.data.database import DB

from app.data.item_components import ItemComponent
from app.data.components import Type

from app.engine import action, combat_calcs, equations, banner
from app.engine import item_system, skill_system, item_funcs
from app.engine.game_state import game

class PermanentStatChange(ItemComponent):
    nid = 'permanent_stat_change'
    desc = "Item changes target's stats on hit."
    tag = 'special'

    expose = (Type.Dict, Type.Stat)

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Ignore's splash
        defender = game.board.get_unit(def_pos)
        if not defender:
            return False
        klass = DB.classes.get(defender.klass)
        for stat, inc in self.value:
            if inc <= 0 or defender.stats[stat] < klass.max_stats.get(stat, 30):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        stat_changes = {k: v for (k, v) in self.value}
        klass = DB.classes.get(target.klass)
        # clamp stat changes
        stat_changes = {k: utils.clamp(v, -unit.stats[k], klass.max_stats.get(k, 30) - target.stats[k]) for k, v in stat_changes.items()}
        actions.append(action.ApplyStatChanges(target, stat_changes))
        playback.append(('stat_hit', unit, item, target))

    def end_combat(self, playback, unit, item, target, mode):
        # Count number of stat hits
        count = 0
        for p in playback:
            if p[0] == 'stat_hit':
                count += 1
        if count > 0:
            stat_changes = {k: v*count for (k, v) in self.value}
            klass = DB.classes.get(target.klass)
            # clamp stat changes
            stat_changes = {k: utils.clamp(v, -target.stats[k], klass.max_stats.get(k, 30) - target.stats[k]) for k, v in stat_changes.items()}
            game.memory['stat_changes'] = stat_changes
            game.exp_instance.append((target, 0, None, 'stat_booster'))
            game.state.change('exp')

class PermanentGrowthChange(ItemComponent):
    nid = 'permanent_growth_change'
    desc = "Item changes target's growths on hit"
    tag = 'special'

    expose = (Type.Dict, Type.Stat)

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        growth_changes = {k: v for (k, v) in self.value}
        actions.append(action.ApplyGrowthChanges(target, growth_changes))
        playback.append(('stat_hit', unit, item, target))

class WexpChange(ItemComponent):
    nid = 'wexp_change'
    desc = "Item changes target's wexp on hit"
    tag = 'special'

    expose = (Type.Dict, Type.WeaponType)

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        actions.append(action.WexpChange(unit, self.value))
        playback.append(('hit', unit, item, target))

class StatusOnHit(ItemComponent):
    nid = 'status_on_hit'
    desc = "Item gives status to target when it hits"
    tag = 'special'

    expose = Type.Skill  # Nid

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        act = action.AddSkill(target, self.value, unit)
        actions.append(act)
        playback.append(('status_hit', unit, item, target, self.value))

    def ai_priority(self, unit, item, target, move):
        # Do I add a new status to the target
        if target and self.value not in [skill.nid for skill in target.skills]:
            accuracy_term = utils.clamp(combat_calcs.compute_hit(unit, target, item, target.get_weapon(), "attack")/100., 0, 1)
            num_attacks = combat_calcs.outspeed(unit, target, item, target.get_weapon(), "attack")
            accuracy_term *= num_attacks
            # Tries to maximize distance from target
            distance_term = 0.01 * utils.calculate_distance(move, target.position)
            if skill_system.check_enemy(unit, target):
                return 0.5 * accuracy_term + distance_term
            else:
                return -0.5 * accuracy_term
        return 0

class Shove(ItemComponent):
    nid = 'shove'
    desc = "Item shoves target on hit"
    tag = 'special'

    expose = Type.Int
    value = 1

    def _check_shove(self, unit_to_move, anchor_pos, magnitude):
        offset_x = utils.clamp(unit_to_move.position[0] - anchor_pos[0], -1, 1)
        offset_y = utils.clamp(unit_to_move.position[1] - anchor_pos[1], -1, 1)
        new_position = (unit_to_move.position[0] + offset_x * magnitude,
                        unit_to_move.position[1] + offset_y * magnitude)

        mcost = game.movement.get_mcost(unit_to_move, new_position)
        if game.tilemap.check_bounds(new_position) and \
                not game.board.get_unit(new_position) and \
                mcost <= equations.parser.movement(unit_to_move):
            return new_position
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        if not skill_system.ignore_forced_movement(target):
            new_position = self._check_shove(target, unit.position, self.value)
            if new_position:
                actions.append(action.ForcedMovement(target, new_position))
                playback.append(('shove_hit', unit, item, target))

class ShoveOnEndCombat(Shove):
    nid = 'shove_on_end_combat'
    desc = "Item shoves target at the end of combat"
    tag = 'special'

    expose = Type.Int
    value = 1

    def end_combat(self, playback, unit, item, target, mode):
        if not skill_system.ignore_forced_movement(target):
            new_position = self._check_shove(target, unit.position, self.value)
            if new_position:
                action.do(action.ForcedMovement(target, new_position))

class ShoveTargetRestrict(Shove, ItemComponent):
    nid = 'shove_target_restrict'
    desc = "Target restriction for Shove"
    tag = 'special'

    expose = Type.Int
    value = 1

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # only targets units that need to be restored
        defender = game.board.get_unit(def_pos)
        if defender and self._check_shove(defender, unit.position, self.value) and \
                not skill_system.ignore_forced_movement(defender):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if self._check_shove(s, unit.position, self.value) and \
                    not skill_system.ignore_forced_movement(s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        pass

    def end_combat(self, playback, unit, item, target, mode):
        pass

class Swap(ItemComponent):
    nid = 'swap'
    desc = "Item swaps user with target on hit"
    tag = 'special'

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        if not skill_system.ignore_forced_movement(unit) and not skill_system.ignore_forced_movement(target):
            actions.append(action.Swap(unit, target))
            playback.append(('swap_hit', unit, item, target))

class Steal(ItemComponent):
    nid = 'steal'
    desc = "Steal any unequipped item from target on hit"
    tag = 'special'

    _did_steal = False

    def init(self, item):
        item.data['target_item'] = None

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Unit has item that can be stolen
        attack = equations.parser.steal_atk(unit)
        defender = game.board.get_unit(def_pos)  
        defense = equations.parser.steal_def(defender)
        if attack >= defense:
            for def_item in defender.items:
                if self.item_restrict(unit, item, defender, def_item):
                    return True
        return False

    def ai_targets(self, unit, item):
        positions = set()
        for other in game.units:
            if other.position and skill_system.check_enemy(unit, other):
                for def_item in other.items:
                    if self.item_restrict(unit, item, other, def_item):
                        positions.add(other.position)
                        break
        return positions

    def targets_items(self, unit, item) -> bool:
        return True

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if item_system.locked(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if def_item is defender.get_weapon():
            return False
        return True

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        target_item = item.data.get('target_item')
        if target_item:
            actions.append(action.RemoveItem(target, target_item))
            actions.append(action.DropItem(unit, target_item))
            if unit.team != 'player':
                actions.append(action.MakeItemDroppable(unit, target_item))
            actions.append(action.UpdateRecords('steal', (unit.nid, target.nid, target_item.nid)))
            self._did_steal = True

    def end_combat(self, playback, unit, item, target, mode):
        if self._did_steal:
            target_item = item.data.get('target_item')
            game.alerts.append(banner.StoleItem(unit, target_item))
            game.state.change('alert')
        item.data['target_item'] = None
        self._did_steal = False

    def ai_priority(self, unit, item, target, move):
        if target:
            steal_term = 0.75
            enemy_positions = utils.average_pos({other.position for other in game.units if other.position and skill_system.check_enemy(unit, other)})
            distance_term = utils.calculate_distance(move, enemy_positions)
            return steal_term + 0.01 * distance_term
        return 0

class GBASteal(Steal, ItemComponent):
    nid = 'gba_steal'
    desc = "Steal any non-weapon, non-spell from target on hit"
    tag = 'special'

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if item_system.locked(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if item_system.is_weapon(defender, def_item) or item_system.is_spell(defender, def_item):
            return False
        return True

class EventOnHit(ItemComponent):
    nid = 'event_on_hit'
    desc = "Calls event on hit"
    tag = 'special'

    expose = Type.Event

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            game.events.add_event(event_prefab.nid, event_prefab.commands, unit, target, item, target_pos)

class EventAfterCombat(ItemComponent):
    nid = 'event_after_combat'
    desc = "Item calls an event after hit"
    tag = 'special'

    expose = Type.Event

    _did_hit = False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        self._did_hit = True

    def end_combat(self, playback, unit, item, target, mode):
        if self._did_hit and target:
            event_prefab = DB.events.get_from_nid(self.value)
            if event_prefab:
                game.events.add_event(event_prefab.nid, event_prefab.commands, unit=unit, unit2=target, item=item, position=unit.position)
        self._did_hit = False
