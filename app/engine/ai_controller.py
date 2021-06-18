import math

from app.utilities import utils
from app.data.database import DB

from app.engine import engine, action, combat_calcs, pathfinding, target_system, \
    equations, item_system, item_funcs, skill_system, line_of_sight, evaluate
from app.engine.combat import interaction
from app.engine.game_state import game

import logging

class AIController():
    def __init__(self):
        self.reset()

    def reset(self):
        self.unit = None
        self.state = "Init"

        self.behaviour_idx = 0
        self.behaviour = None
        self.inner_ai = None

        self.did_something = False

        self.move_ai_complete = False
        self.attack_ai_complete = False
        self.canto_ai_complete = False

    def load_unit(self, unit):
        self.reset()
        self.unit = unit

    def is_done(self):
        return self.move_ai_complete and \
            self.attack_ai_complete and self.canto_ai_complete

    def clean_up(self):
        self.goal_position = None
        self.goal_item = None
        self.goal_target = None

    def set_next_behaviour(self):
        behaviours = DB.ai.get(self.unit.ai).behaviours
        if self.behaviour_idx < len(behaviours):
            self.behaviour = behaviours[self.behaviour_idx]
            self.behaviour_idx += 1
        else:
            self.behaviour = None
            self.behaviour_idx = 0

    def get_behaviour(self):
        return self.behaviour

    def act(self):
        logging.info("AI Act!")

        change = False
        if not self.move_ai_complete:
            if self.think():
                change = self.move()
                self.move_ai_complete = True
        elif not self.attack_ai_complete:
            change = self.attack()
            self.attack_ai_complete = True
        elif not self.canto_ai_complete:
            if self.unit.has_attacked and skill_system.has_canto(self.unit, None):
                self.canto_retreat()
                change = self.move()
            self.canto_ai_complete = True

        return self.did_something, change

    def move(self):
        if self.goal_position and self.goal_position != self.unit.position:
            path = target_system.get_path(self.unit, self.goal_position)
            # if self.unit.has_attacked:
            #     self.unit.wait()
            game.state.change('movement')
            action.do(action.Move(self.unit, self.goal_position, path))
            return True
        else:
            return False

    def attack(self):
        # Attacking or supporting
        if self.goal_target:  # Target is a position tuple
            if self.goal_item and self.goal_item in item_funcs.get_all_items(self.unit):
                self.unit.equip(self.goal_item)
            # Highlights
            if item_system.is_weapon(self.unit, self.goal_item):
                game.highlight.remove_highlights()
                splash_positions = item_system.splash_positions(self.unit, self.goal_item, self.goal_target)
                game.highlight.display_possible_attacks({self.goal_target})
                game.highlight.display_possible_attacks(splash_positions, light=True)
            elif item_system.is_spell(self.unit, self.goal_item):
                game.highlight.remove_highlights()
                splash_positions = item_system.splash_positions(self.unit, self.goal_item, self.goal_target)
                game.highlight.display_possible_spell_attacks({self.goal_target})
                game.highlight.display_possible_spell_attacks(splash_positions, light=True)

            # Used for steal
            if item_system.targets_items(self.unit, self.goal_item):
                # Choose most expensive item that is legal
                target = game.board.get_unit(self.goal_target)
                legal_items = [item for item in target.items if item_system.item_restrict(self.unit, self.goal_item, target, item)]
                items = sorted(legal_items, key=lambda x: item_system.sell_price(self.unit, x) or 0)
                self.goal_item.data['target_item'] = items[-1]

            # Combat
            interaction.start_combat(self.unit, self.goal_target, self.goal_item, ai_combat=True)
            return True
        # Interacting with regions
        elif self.goal_position and self.behaviour and self.behaviour.action == 'Interact':
            # Get region
            region = None
            for r in game.level.regions:
                if r.contains(self.goal_position) and r.region_type == 'event' and r.sub_nid == self.behaviour.target_spec:
                    try:
                        if not r.condition or evaluate.evaluate(r.condition, self.unit, position=self.goal_position):
                            region = r
                            break
                    except:
                        logging.warning("Could not evaluate region conditional %s" % r.condition)
            if region:
                did_trigger = game.events.trigger(region.sub_nid, self.unit, position=self.unit.position, region=region)
                if did_trigger and region.only_once:
                    action.do(action.RemoveRegion(region))
                if did_trigger:
                    action.do(action.HasAttacked(self.unit))
                    return True
        return False

    def canto_retreat(self):
        valid_positions = self.get_true_valid_moves()
        enemy_positions = {u.position for u in game.units if u.position and skill_system.check_enemy(self.unit, u)}
        self.goal_position = utils.farthest_away_pos(self.unit.position, valid_positions, enemy_positions)

    def smart_retreat(self) -> bool:
        valid_positions = self.get_true_valid_moves()

        target_positions = get_targets(self.unit, self.behaviour)

        zero_move = max(target_system.find_potential_range(self.unit, True, True), default=0)
        single_move = zero_move + equations.parser.movement(self.unit)
        double_move = single_move + equations.parser.movement(self.unit)

        target_positions = {(pos, utils.calculate_distance(self.unit.position, pos)) for pos in target_positions}

        if self.behaviour.view_range == -4:
            pass
        elif self.behaviour.view_range == -3:
            target_positions = {(pos, mag) for pos, mag in target_positions if mag < double_move}
        elif self.behaviour.view_range == -2:
            target_positions = {(pos, mag) for pos, mag in target_positions if mag < single_move}
        elif self.behaviour.view_range == -1:
            target_positions = {(pos, mag) for pos, mag in target_positions if mag < zero_move}
        else:
            target_positions = {(pos, mag) for pos, mag in target_positions if mag < self.view_range}

        if target_positions and len(valid_positions) > 1:
            self.goal_position = utils.smart_farthest_away_pos(self.unit.position, valid_positions, target_positions)
            return True
        else:
            return False

    def get_true_valid_moves(self) -> set:
        valid_moves = target_system.get_valid_moves(self.unit)
        other_unit_positions = {unit.position for unit in game.units if unit.position and unit is not self.unit}
        valid_moves -= other_unit_positions
        return valid_moves

    def think(self):
        time = engine.get_time()
        success = False
        self.did_something = False
        orig_pos = self.unit.position

        logging.info("*** AI Thinking... ***")

        while True:
            # Can spend up to half a frame thinking
            over_time = engine.get_true_time() - time >= 8
            logging.info("Current State: %s", self.state)

            if self.state == 'Init':
                self.start_time = engine.get_time()
                logging.info("Starting AI with nid: %s, position: %s, class: %s, AI: %s", self.unit.nid, self.unit.position, self.unit.klass, self.unit.ai)
                self.clean_up()
                # Get next behaviour
                self.set_next_behaviour()
                if self.behaviour:
                    logging.info(self.behaviour.action)
                    if self.behaviour.action == "None":
                        pass  # Try again
                    elif self.behaviour.action == "Attack":
                        self.inner_ai = self.build_primary()
                        self.state = "Primary"
                    elif self.behaviour.action == "Support":
                        self.inner_ai = self.build_primary()
                        self.state = "Primary"
                    elif self.behaviour.action == 'Steal':
                        self.inner_ai = self.build_primary()
                        self.state = "Primary"
                    elif self.behaviour.action == 'Interact':
                        self.inner_ai = self.build_secondary()
                        self.state = "Secondary"
                    elif self.behaviour.action == 'Move_to':
                        self.inner_ai = self.build_secondary()
                        self.state = "Secondary"
                    elif self.behaviour.action == "Move_away_from":
                        success = self.smart_retreat()
                        if success:
                            self.state = "Done"
                        else:
                            self.state = "Init"  # Try another behaviour
                else:
                    self.state = 'Done'

            elif self.state == 'Primary':
                done, self.goal_target, self.goal_position, self.goal_item = self.inner_ai.run()
                if done:
                    if self.goal_target:
                        self.ai_group_ping()
                        success = True
                        self.state = "Done"
                    else:
                        self.inner_ai = self.build_secondary()
                        self.state = "Secondary"  # Try secondary
                elif over_time:
                    # Make sure to quick move back so that the in-between frames aren't flickering around
                    self.inner_ai.quick_move(self.inner_ai.orig_pos)

            elif self.state == 'Secondary':
                done, self.goal_position = self.inner_ai.run()
                if done:
                    if self.goal_position:
                        if self.goal_position != self.unit.position:
                            self.ai_group_ping()
                            success = True
                        self.state = "Done"
                    else:
                        self.state = "Init"  # Try another behaviour

            if self.state == 'Done':
                self.did_something = success
                self.state = 'Init'
                return True

            if over_time:
                break

        return False

    def ai_group_ping(self):
        ai_group = self.unit.ai_group
        if not ai_group:
            return
        for unit in game.units:
            if unit.team == self.unit.team and unit.ai_group == ai_group:
                if not unit._has_moved and not unit._has_attacked:
                    unit.has_run_ai = False  # So it can be run through the AI state again
                if not unit.ai_group_active:
                    action.do(action.AIGroupPing(unit))

    def build_primary(self):
        if self.behaviour.view_range == -1:  # Guard AI
            valid_moves = {self.unit.position}
        else:
            valid_moves = self.get_true_valid_moves()

        return PrimaryAI(self.unit, valid_moves, self.behaviour)

    def build_secondary(self):
        return SecondaryAI(self.unit, self.behaviour)

class PrimaryAI():
    def __init__(self, unit, valid_moves, behaviour):
        self.max_tp = 0

        self.unit = unit
        self.orig_pos = self.unit.position
        self.orig_item = self.unit.items[0] if self.unit.items else None
        self.behaviour = behaviour

        if self.behaviour.action == "Attack":
            self.items = [item for item in item_funcs.get_all_items(self.unit) if 
                          item_funcs.available(self.unit, item)]
            self.extra_abilities = skill_system.get_extra_abilities(self.unit)
            for ability in self.extra_abilities.values():
                self.items.append(ability)
        elif self.behaviour.action == 'Support':
            self.items = [item for item in item_funcs.get_all_items(self.unit) if 
                          item_funcs.available(self.unit, item)]
            self.extra_abilities = skill_system.get_extra_abilities(self.unit)
            for ability in self.extra_abilities.values():
                self.items.append(ability)
        elif self.behaviour.action == 'Steal':
            self.items = []
            self.extra_abilities = skill_system.get_extra_abilities(self.unit)
            for ability in self.extra_abilities.values():
                if ability.name == 'Steal':
                    self.items.append(ability)

        self.behaviour_targets = get_targets(self.unit, self.behaviour)

        logging.info("Testing Items: %s", self.items)
        
        self.item_index = 0
        self.move_index = 0
        self.target_index = 0

        self.valid_moves = list(valid_moves)

        self.best_target = None
        self.best_position = None
        self.best_item = None

        self.item_setup()

    def item_setup(self):
        if self.item_index < len(self.items):
            logging.info("Testing %s" % self.items[self.item_index])
            self.unit.equip(self.items[self.item_index])
            self.get_all_valid_targets()
            self.possible_moves = self.get_possible_moves()
            logging.info(self.possible_moves)

    def get_valid_targets(self, unit, item, valid_moves) -> list:
        item_range = item_funcs.get_range(unit, item)
        ai_targets = item_system.ai_targets(unit, item)
        if len(ai_targets) < 20:
            logging.info("AI Targets: %s", ai_targets)
        filtered_targets = set()

        for pos in ai_targets:
            for valid_move in valid_moves:
                # Determine if we can hit this unit at one of our moves
                if (utils.calculate_distance(pos, valid_move) in item_range) and \
                   (not DB.constants.value('ai_fog_of_war') or game.board.in_vision(pos, self.unit.team)):
                    filtered_targets.add(pos)
                    break

        return list(filtered_targets)

    def get_all_valid_targets(self):
        item = self.items[self.item_index]
        logging.info("Determining targets for item: %s", item)
        self.valid_targets = self.get_valid_targets(self.unit, item, self.valid_moves)
        # Only if we already have some legal targets (ie, ourself)
        if self.valid_targets and 0 in item_funcs.get_range(self.unit, item):
            self.valid_targets += self.valid_moves  # Hack to target self in all valid positions
            self.valid_targets = list(set(self.valid_targets))  # Only uniques
        logging.info("Valid Targets: %s", self.valid_targets)

    def get_possible_moves(self) -> list:
        if self.target_index < len(self.valid_targets) and self.item_index < len(self.items):
            # Given an item and a target, find all positions in valid_moves that I can strike the target at.
            item = self.items[self.item_index]
            target = self.valid_targets[self.target_index]
            a = target_system.find_manhattan_spheres(item_funcs.get_range(self.unit, item), *target)
            b = set(self.valid_moves)
            return list(a & b)
        else:
            return []

    def quick_move(self, move):
        game.leave(self.unit, test=True)
        self.unit.position = move
        game.arrive(self.unit, test=True)

    def run(self):
        if self.item_index >= len(self.items):
            self.quick_move(self.orig_pos)
            if self.orig_item:
                self.unit.equip(self.orig_item)
            return (True, self.best_target, self.best_position, self.best_item)

        elif self.target_index >= len(self.valid_targets):
            self.target_index = 0
            self.item_index += 1
            self.item_setup()

        elif self.move_index >= len(self.possible_moves):
            self.move_index = 0
            self.target_index += 1
            self.possible_moves = self.get_possible_moves()

        else:
            target = self.valid_targets[self.target_index]
            item = self.items[self.item_index]
            # If too many legal targets, just try for the best move first
            # Otherwise it spends way too long trying every possible position to strike from
            if len(self.valid_targets) > 10:
                enemy_positions = {u.position for u in game.units if u.position and skill_system.check_enemy(self.unit, u)}
                move = utils.farthest_away_pos(self.orig_pos, self.possible_moves, enemy_positions)
            else:
                move = self.possible_moves[self.move_index]

            if self.unit.position != move:
                self.quick_move(move)

            # Check line of sight
            line_of_sight_flag = True
            if DB.constants.value('line_of_sight'):
                max_item_range = max(item_funcs.get_range(self.unit, item))
                valid_targets = line_of_sight.line_of_sight([move], [target], max_item_range)
                if not valid_targets:
                    line_of_sight_flag = False

            if line_of_sight_flag:
                self.determine_utility(move, target, item)
            self.move_index += 1
            # If too many legal targets, do not bother with every possible move
            if len(self.valid_targets) > 10:
                self.move_index = len(self.possible_moves)

        # Not done yet
        return (False, self.best_target, self.best_position, self.best_item)

    def determine_utility(self, move, target, item):
        tp = 0
        main_target_pos, splash = item_system.splash(self.unit, item, target)
        if item_system.target_restrict(self.unit, item, main_target_pos, splash):
            tp = self.compute_priority(main_target_pos, splash, move, item)

        unit = game.board.get_unit(target)
        if unit:
            name = unit.nid
        else:
            name = '--'

        logging.info("Choice %.5f - Weapon: %s, Position: %s, Target: %s, Target Position: %s", tp, item, move, name, target)
        if tp > self.max_tp:
            self.best_target = target
            self.best_position = move
            self.best_item = item
            self.max_tp = tp

    def compute_priority(self, main_target_pos, splash, move, item) -> float:
        tp = 0
        main_target = game.board.get_unit(main_target_pos)
        # Only count main target if it's one of the legal targets
        if main_target and main_target_pos in self.behaviour_targets:  
            ai_priority = item_system.ai_priority(self.unit, item, main_target, move)
            # If no ai priority hook defined
            if ai_priority is None:
                pass
            else:
                tp += ai_priority

            if item_system.damage(self.unit, item) and \
                    skill_system.check_enemy(self.unit, main_target):
                ai_priority = self.default_priority(main_target, item, move)
                tp += ai_priority

        for splash_pos in splash:
            target = game.board.get_unit(splash_pos)
            # Only count splash target if it's one of the legal targets
            if not target or splash_pos not in self.behaviour_targets:
                continue
            ai_priority = item_system.ai_priority(self.unit, item, main_target, move)
            if ai_priority is None:
                pass
            else:
                tp += ai_priority

            if item_system.damage(self.unit, item):
                accuracy = utils.clamp(combat_calcs.compute_hit(self.unit, target, item, target.get_weapon(), "attack")/100., 0, 1)
                raw_damage = combat_calcs.compute_damage(self.unit, target, item, target.get_weapon(), "attack")
                lethality = utils.clamp(raw_damage / float(target.get_hp()), 0, 1)
                ai_priority = 3 if lethality * accuracy >= 1 else lethality * accuracy
                if skill_system.check_enemy(self.unit, target):
                    tp += ai_priority
                elif skill_system.check_ally(self.unit, target):
                    tp -= ai_priority
        return tp

    def default_priority(self, main_target, item, move):
        # Default method
        terms = []
        offense_term = 0
        defense_term = 1

        raw_damage = combat_calcs.compute_damage(self.unit, main_target, item, main_target.get_weapon(), "attack")
        crit_damage = combat_calcs.compute_damage(self.unit, main_target, item, main_target.get_weapon(), "attack", crit=True)

        # Damage I do compared to target's current hp
        lethality = utils.clamp(raw_damage / float(main_target.get_hp()), 0, 1)
        crit_lethality = utils.clamp(crit_damage / float(main_target.get_hp()), 0, 1)
        # Accuracy
        hit_comp = combat_calcs.compute_hit(self.unit, main_target, item, main_target.get_weapon(), "attack")
        if hit_comp:
            accuracy = utils.clamp(hit_comp/100., 0, 1)
        else:
            accuracy = 0
        crit_comp = combat_calcs.compute_crit(self.unit, main_target, item, main_target.get_weapon(), "attack")
        if crit_comp:
            crit_accuracy = utils.clamp(crit_comp/100., 0, 1)
        else:
            crit_accuracy = 0

        # Determine if I would get countered
        # Even if I wouldn't get countered, check anyway how much damage I would take
        target_weapon = main_target.get_weapon()
        target_damage = combat_calcs.compute_damage(main_target, self.unit, target_weapon, item, "defense")
        if not target_damage:
            target_damage = 0
        target_damage = utils.clamp(target_damage/main_target.get_hp(), 0, 1)
        target_accuracy = combat_calcs.compute_hit(main_target, self.unit, target_weapon, item, "defense")
        if not target_accuracy:
            target_accuracy = 0
        target_accuracy = utils.clamp(target_accuracy/100., 0, 1)
        # If I wouldn't get counterattacked, much less important, so multiply by 10 %
        if not combat_calcs.can_counterattack(self.unit, item, main_target, target_weapon):
            target_damage *= 0.3
            target_accuracy *= 0.3

        num_attacks = combat_calcs.outspeed(self.unit, main_target, item, target_weapon, "attack")
        first_strike = lethality * accuracy if lethality >= 1 else 0

        if num_attacks > 1 and target_damage >= 1:
            # Calculate chance I actually get to strike more than once
            num_attacks -= (target_accuracy * (1 - first_strike))

        offense_term += 3 if lethality * accuracy >= 1 else lethality * accuracy * num_attacks
        crit_term = (crit_lethality - lethality) * crit_accuracy * accuracy * num_attacks
        offense_term += crit_term
        defense_term -= target_damage * target_accuracy * (1 - first_strike)
        if offense_term <= 0:
            if lethality > 0 and DB.constants.value('attack_zero_hit'):
                logging.info("Accuracy is bad, but continuing with stupid AI")
            elif accuracy > 0 and DB.constants.value('attack_zero_dam'):
                logging.info("Zero Damage, but continuing with stupid AI")
            else:    
                logging.info("Offense: %.2f, Defense: %.2f", offense_term, defense_term)
                return 0

        # Only here to break ties
        # Tries to minimize how far the unit should move
        max_distance = equations.parser.movement(self.unit)
        if max_distance > 0:
            distance_term = (max_distance - utils.calculate_distance(move, self.orig_pos)) / float(max_distance)
        else:
            distance_term = 1

        logging.info("Damage: %.2f, Accuracy: %.2f, Crit Accuracy: %.2f", lethality, accuracy, crit_accuracy)
        logging.info("Offense: %.2f, Defense: %.2f, Distance: %.2f", offense_term, defense_term, distance_term)
        ai_prefab = DB.ai.get(self.unit.ai)
        offense_bias = ai_prefab.offense_bias
        offense_weight = offense_bias * (1 / (offense_bias + 1))
        defense_weight = 1 - offense_weight
        terms.append((offense_term, offense_weight))
        terms.append((defense_term, defense_weight))
        terms.append((distance_term, .0001))

        return utils.process_terms(terms)

def handle_unit_spec(all_targets, behaviour):
    target_spec = behaviour.target_spec
    if not target_spec:
        return all_targets
    invert = bool(behaviour.invert_targeting)
    # Uses ^ (which is XOR) to handle inverting the targeting
    if target_spec[0] == "Tag":
        all_targets = [pos for pos in all_targets if bool(target_spec[1] in game.board.get_unit(pos).tags) ^ invert]
    elif target_spec[0] == "Class":
        all_targets = [pos for pos in all_targets if bool(game.board.get_unit(pos).klass == target_spec[1]) ^ invert]
    elif target_spec[0] == "Name":
        all_targets = [pos for pos in all_targets if bool(game.board.get_unit(pos).name == target_spec[1]) ^ invert]
    elif target_spec[0] == 'Faction':
        all_targets = [pos for pos in all_targets if bool(game.board.get_unit(pos).faction == target_spec[1]) ^ invert]
    elif target_spec[0] == 'Party':
        all_targets = [pos for pos in all_targets if bool(game.board.get_unit(pos).party == target_spec[1]) ^ invert]
    elif target_spec[0] == 'ID':
        all_targets = [pos for pos in all_targets if bool(game.board.get_unit(pos).nid == target_spec[1]) ^ invert]
    return all_targets

def get_targets(unit, behaviour):
    all_targets = []
    if behaviour.target == 'Unit':
        all_targets = [u.position for u in game.units if u.position]
    elif behaviour.target == 'Enemy':
        all_targets = [u.position for u in game.units if u.position and skill_system.check_enemy(unit, u)]
    elif behaviour.target == 'Ally':
        all_targets = [u.position for u in game.units if u.position and skill_system.check_ally(unit, u)]
    elif behaviour.target == 'Event':
        target_spec = behaviour.target_spec
        all_targets = []
        for region in game.level.regions:
            try:
                if region.region_type == 'event' and region.sub_nid == target_spec and (not region.condition or evaluate.evaluate(region.condition, unit)):
                    all_targets += region.get_all_positions()
            except:
                logging.warning("Region Condition: Could not parse %s" % region.condition)
        all_targets = list(set(all_targets))  # Remove duplicates
    elif behaviour.target == 'Position':
        if behaviour.target_spec == "Starting":
            if unit.starting_position:
                all_targets = [unit.starting_position]
            else:
                all_targets = []
        else:
            all_targets = [tuple(behaviour.target_spec)]
    if behaviour.target in ('Unit', 'Enemy', 'Ally'):
        all_targets = handle_unit_spec(all_targets, behaviour)

    if behaviour.target != 'Position':
        if DB.constants.value('ai_fog_of_war'):
            all_targets = [pos for pos in all_targets if game.board.in_vision(pos, unit.team)]
    return all_targets

class SecondaryAI():
    def __init__(self, unit, behaviour):
        self.unit = unit
        self.behaviour = behaviour
        self.view_range = self.behaviour.view_range
        if self.view_range == -4 or self.unit.ai_group_active:
            self.view_range = -3  # Try this first

        self.available_targets = []

        # Determine all targets
        self.all_targets = get_targets(self.unit, behaviour)

        self.zero_move = max(target_system.find_potential_range(self.unit, True, True), default=0)
        self.single_move = self.zero_move + equations.parser.movement(self.unit)
        self.double_move = self.single_move + equations.parser.movement(self.unit)

        movement_group = game.movement.get_movement_group(self.unit)
        self.grid = game.board.get_grid(movement_group)
        self.pathfinder = \
            pathfinding.AStar(self.unit.position, None, self.grid, 
                              game.tilemap.width, game.tilemap.height, 
                              self.unit.team, skill_system.pass_through(self.unit),
                              DB.constants.value('ai_fog_of_war'))

        self.widen_flag = False  # Determines if we've widened our search
        self.reset()

    def reset(self):
        self.max_tp = 0
        self.best_target = 0
        self.best_path = None

        limit = self.get_limit()
        self.available_targets = [t for t in self.all_targets if utils.calculate_distance(self.unit.position, t) <= limit]

        self.best_position = None

    def get_limit(self) -> int:
        # Make sure we don't exceed double move
        if self.widen_flag or self.view_range == -4:
            limit = 99
        elif self.view_range == -3:
            limit = self.double_move
        elif self.view_range == -2:
            if self.behaviour.action in ('Attack', 'Support', 'Steal'):
                limit = -1  # Because the primary AI should have already taken care of this...
            else:
                limit = self.single_move
        elif self.view_range == -1:
            limit = -1
        else:
            limit = self.view_range
        return limit

    def run(self):
        if self.available_targets:
            target = self.available_targets.pop()
            # Find a path to the target
            path = self.get_path(target)
            if not path:
                logging.info("No valid path to %s.", target)
                return False, None
            # We found a path
            tp = self.compute_priority(target, len(path))
            logging.info("Path to %s. -- %s", target, tp)
            if tp > self.max_tp:
                self.max_tp = tp
                self.best_target = target
                self.best_path = path

        elif self.best_target:
            self.best_position = target_system.travel_algorithm(self.best_path, self.unit.movement_left, self.unit, self.grid)
            logging.info("Best Target: %s", self.best_target)
            logging.info("Best Position: %s", self.best_position)
            return True, self.best_position

        else:
            if (self.behaviour.view_range == -4 or self.unit.ai_group_active) and not self.widen_flag:
                logging.info("Widening search!")
                self.widen_flag = True
                self.view_range = -4
                self.available_targets = [t for t in self.all_targets if t not in self.available_targets]
            else:
                return True, None
        return False, None

    def get_path(self, goal_pos):
        self.pathfinder.set_goal_pos(goal_pos)

        if self.behaviour.target == 'Event':
            adj_good_enough = False
        else:
            adj_good_enough = True

        limit = self.get_limit()
        path = self.pathfinder.process(game.board, adj_good_enough=adj_good_enough, ally_block=False, limit=limit)
        self.pathfinder.reset()
        return path

    def default_priority(self, enemy):
        hp_max = equations.parser.hitpoints(enemy)
        weakness_term = float(hp_max - enemy.get_hp()) / hp_max

        items = [item for item in item_funcs.get_all_items(self.unit) if 
                 item_funcs.available(self.unit, item)]

        terms = []
        tp, highest_damage_term, highest_status_term = 0, 0, 0

        for item in items:
            status_term = 1 if item.status_on_hit else 0
            true_damage = 0
            if item_system.is_weapon(self.unit, item) or item_system.is_spell(self.unit, item):
                raw_damage = combat_calcs.compute_damage(self.unit, enemy, item, enemy.get_weapon(), 'attack')
                hit = utils.clamp(combat_calcs.compute_hit(self.unit, enemy, item, enemy.get_weapon(), 'attack')/100., 0, 1)
                if raw_damage:
                    true_damage = raw_damage * hit
                else:
                    true_damage = 0

            if true_damage <= 0 and status_term <= 0:
                continue  # If no damage could be dealt, ignore
            damage_term = min(float(true_damage / hp_max), 1.)
            new_tp = damage_term + status_term/2
            if new_tp > tp:
                tp = new_tp
                highest_damage_term = damage_term
                highest_status_term = status_term

        if highest_status_term == 0 and highest_damage_term == 0:
            # Just don't include any of this
            return terms
        terms.append((highest_damage_term, 15))
        terms.append((highest_status_term, 10))
        terms.append((weakness_term, 15))
        return terms

    def compute_priority(self, target, distance=0):
        terms = []
        if distance:
            distance_term = 1 - math.log(distance)/4.
        else:
            target_distance = utils.calculate_distance(self.unit.position, target)
            distance_term = 1 - math.log(target_distance)/4.
        terms.append((distance_term, 60))

        enemy = game.board.get_unit(target)
        if self.behaviour.action == "Attack" and enemy:
            new_terms = self.default_priority(enemy)
            if new_terms:
                terms += new_terms
            else:
                return 0
        elif self.behaviour.action == "Steal" and enemy:
            return 0  # TODO: For now, Steal just won't work with secondary AI
        else:
            pass

        return utils.process_terms(terms)
