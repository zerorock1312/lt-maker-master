from app.data.database import DB

from app.engine import combat_calcs, item_system, skill_system, static_random, action, item_funcs
from app.engine.game_state import game

import logging

class SolverState():
    def get_next_state(self, solver):
        return None

    def process(self, solver, actions, playback):
        return None

    def process_command(self, command):
        if command in ('hit2', 'crit2', 'miss2'):
            return 'defender'
        elif command in ('hit1', 'crit1', 'miss1'):
            return 'attacker'
        elif command == 'end':
            return None
        return None

class InitState(SolverState):
    def get_next_state(self, solver):
        command = solver.get_script()
        if command == '--':
            if solver.defender_has_vantage():
                return 'defender'
            else:
                return 'attacker'
        else:
            return self.process_command(command) 

class AttackerState(SolverState):
    def get_next_state(self, solver):
        command = solver.get_script()
        if solver.attacker_alive() and solver.defender_alive():
            if command == '--':
                if solver.defender:
                    if DB.constants.value('def_double') or skill_system.def_double(solver.defender):
                        defender_outspeed = combat_calcs.outspeed(solver.defender, solver.attacker, solver.def_item, solver.main_item, 'defense')
                    else:
                        defender_outspeed = 1
                    attacker_outspeed = combat_calcs.outspeed(solver.attacker, solver.defender, solver.main_item, solver.def_item, 'attack')
                else:
                    attacker_outspeed = defender_outspeed = 1
                multiattacks = combat_calcs.compute_multiattacks(solver.attacker, solver.defender, solver.main_item, 'attack')
            
                if solver.item_has_uses() and \
                        solver.num_subattacks < multiattacks:
                    return 'attacker'
                elif solver.allow_counterattack() and \
                        solver.num_defends < defender_outspeed:
                    solver.num_subdefends = 0
                    return 'defender'
                elif solver.item_has_uses() and \
                        solver.num_attacks < attacker_outspeed:
                    solver.num_subattacks = 0
                    return 'attacker'
                return None
            else:
                return self.process_command(command)
        else:
            return None

    def process(self, solver, actions, playback):
        playback.append(('attacker_phase',))
        for idx, item in enumerate(solver.items):
            defender = solver.defenders[idx]
            splash = solver.splashes[idx]
            target_pos = solver.target_positions[idx]
            if defender:
                solver.process(actions, playback, solver.attacker, defender, target_pos, item, defender.get_weapon(), 'attack')
            for target in splash:
                solver.process(actions, playback, solver.attacker, target, target_pos, item, None, 'splash')
            # Make sure that we run on_hit even if otherwise unavailable
            if not defender and not splash:
                solver.simple_process(actions, playback, solver.attacker, solver.attacker, target_pos, item, None, None)
        
        solver.num_subattacks += 1
        multiattacks = combat_calcs.compute_multiattacks(solver.attacker, solver.defender, solver.main_item, 'attack')
        if solver.num_subattacks >= multiattacks:
            solver.num_attacks += 1

class DefenderState(SolverState):
    def get_next_state(self, solver):
        command = solver.get_script()
        if solver.attacker_alive() and solver.defender_alive():
            if command == '--':
                if DB.constants.value('def_double') or skill_system.def_double(solver.defender):
                    defender_outspeed = combat_calcs.outspeed(solver.defender, solver.attacker, solver.def_item, solver.main_item, 'defense')
                else:
                    defender_outspeed = 1
                attacker_outspeed = combat_calcs.outspeed(solver.attacker, solver.defender, solver.main_item, solver.def_item, 'attack')
                multiattacks = combat_calcs.compute_multiattacks(solver.defender, solver.attacker, solver.def_item, 'defense')
                
                if solver.allow_counterattack() and \
                        solver.num_subdefends < multiattacks:
                    return 'defender'    
                elif solver.item_has_uses() and \
                        solver.num_attacks < attacker_outspeed:
                    solver.num_subattacks = 0
                    return 'attacker'
                elif solver.allow_counterattack() and \
                        solver.num_defends < defender_outspeed:
                    solver.num_subdefends = 0
                    return 'defender'
                return None
            else:
                return self.process_command(command)
        else:
            return None

    def process(self, solver, actions, playback):
        playback.append(('defender_phase',))
        solver.process(actions, playback, solver.defender, solver.attacker, solver.attacker.position, solver.def_item, solver.main_item, 'defense')
        
        solver.num_subdefends += 1
        multiattacks = combat_calcs.compute_multiattacks(solver.defender, solver.attacker, solver.def_item, 'defense')
        if solver.num_subdefends >= multiattacks:
            solver.num_defends += 1

class CombatPhaseSolver():
    states = {'init': InitState,
              'attacker': AttackerState,
              'defender': DefenderState}

    def __init__(self, attacker, main_item, items, defenders, 
                 splashes, target_positions, defender, def_item, 
                 script=None):
        self.attacker = attacker
        self.main_item = main_item
        self.items = items
        self.defenders = defenders
        self.splashes = splashes
        self.target_positions = target_positions
        self.defender = defender
        self.def_item = def_item        

        self.state = InitState()
        self.num_attacks, self.num_defends = 0, 0
        self.num_subattacks, self.num_subdefends = 0, 0

        # For event combats
        self.script = list(reversed(script)) if script else []
        self.current_command = '--'

    def get_state(self):
        return self.state

    def do(self):
        old_random_state = static_random.get_combat_random_state()
        
        actions, playback = [], []
        self.state.process(self, actions, playback)

        new_random_state = static_random.get_combat_random_state()
        action.do(action.RecordRandomState(old_random_state, new_random_state))

        return actions, playback

    def setup_next_state(self):
        old_random_state = static_random.get_combat_random_state()

        next_state = self.state.get_next_state(self)
        logging.debug("Next State: %s" % next_state)
        if next_state:
            self.state = self.states[next_state]()
        else:
            self.state = None
            
        new_random_state = static_random.get_combat_random_state()
        action.do(action.RecordRandomState(old_random_state, new_random_state))

    def get_script(self):
        if self.script:
            self.current_command = self.script.pop()
        else:
            self.current_command = '--'
        return self.current_command

    def generate_roll(self):
        rng_mode = game.mode.rng_choice
        if rng_mode == 'Classic':
            roll = static_random.get_combat()
        elif rng_mode == 'True Hit':
            roll = (static_random.get_combat() + static_random.get_combat()) // 2
        elif rng_mode == 'True Hit+':
            roll = (static_random.get_combat() + static_random.get_combat() + static_random.get_combat()) // 3
        elif rng_mode == 'Grandmaster':
            roll = 0
        return roll

    def generate_crit_roll(self):
        return static_random.get_combat()

    def process(self, actions, playback, attacker, defender, def_pos, item, def_item, mode):
        # Is the item I am processing the first one?
        first_item = item is self.main_item or item is self.items[0]

        to_hit = combat_calcs.compute_hit(attacker, defender, item, def_item, mode)

        if self.current_command in ('hit1', 'hit2', 'crit1', 'crit2'):
            roll = -1
        elif self.current_command in ('miss1', 'miss2'):
            roll = 100
        else:
            roll = self.generate_roll()

        if roll < to_hit:
            crit = False
            if DB.constants.value('crit') or skill_system.crit_anyway(attacker) or self.current_command in ('crit1', 'crit2'):
                to_crit = combat_calcs.compute_crit(attacker, defender, item, def_item, mode)
                if self.current_command in ('crit1', 'crit2'):
                    crit = True
                elif self.current_command in ('hit1', 'hit2', 'miss1', 'miss2'):
                    crit = False
                elif to_crit is not None:
                    crit_roll = self.generate_crit_roll()
                    if crit_roll < to_crit:
                        crit = True
            if crit:
                item_system.on_crit(actions, playback, attacker, item, defender, def_pos, mode, first_item)
                if defender:
                    playback.append(('mark_crit', attacker, defender, self.attacker, item))
            else:
                item_system.on_hit(actions, playback, attacker, item, defender, def_pos, mode, first_item)
                if defender:
                    playback.append(('mark_hit', attacker, defender, self.attacker, item))
            item_system.after_hit(actions, playback, attacker, item, defender, mode)
            skill_system.after_hit(actions, playback, attacker, item, defender, mode)
        else:
            item_system.on_miss(actions, playback, attacker, item, defender, def_pos, mode, first_item)
            if defender:
                playback.append(('mark_miss', attacker, defender, self.attacker, item))

    def simple_process(self, actions, playback, attacker, defender, def_pos, item, def_item, mode):
        # Is the item I am processing the first one?
        first_item = item is self.main_item or item is self.items[0]
        
        item_system.on_hit(actions, playback, attacker, item, defender, def_pos, mode, first_item)
        if defender:
            playback.append(('mark_hit', attacker, defender, self.attacker, item))

    def attacker_alive(self):
        return self.attacker.get_hp() > 0

    def defender_alive(self):
        return self.defender and self.defender.get_hp() > 0

    def defender_has_vantage(self) -> bool:
        return self.allow_counterattack() and \
            skill_system.vantage(self.defender)

    def allow_counterattack(self) -> bool:
        return combat_calcs.can_counterattack(self.attacker, self.main_item, self.defender, self.def_item)

    def item_has_uses(self):
        return item_funcs.available(self.attacker, self.main_item)

    def target_item_has_uses(self):
        return self.defender and self.def_item and item_funcs.available(self.defender, self.def_item)
