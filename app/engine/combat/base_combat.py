from app.engine.combat.solver import CombatPhaseSolver

from app.engine import skill_system, item_system
from app.engine.game_state import game
from app.engine.combat.simple_combat import SimpleCombat

from app.engine.objects.unit import UnitObject
from app.engine.objects.item import ItemObject

class BaseCombat(SimpleCombat):
    alerts: bool = True
    """
    Handles in base and in prep screen "use" of items
    """

    def __init__(self, attacker: UnitObject, main_item: ItemObject, 
                 main_target: UnitObject, script):
        self.attacker = attacker
        self.defender = main_target
        self.main_item = main_item
        self.def_item = None
        if self.defender:
            self.def_item = self.defender.get_weapon()

        self.state_machine = CombatPhaseSolver(
            self.attacker, self.main_item, [self.main_item],
            [self.defender], [[]], [self.defender.position],
            self.defender, self.def_item, script)

        self.full_playback = []
        self.playback = []
        self.actions = []

        self.start_combat()
        while self.state_machine.get_state():
            self.actions, self.playback = self.state_machine.do()
            self.full_playback += self.playback
            self._apply_actions()
            self.state_machine.setup_next_state()

    def start_combat(self):
        game.events.trigger('combat_start', self.attacker, self.defender, self.main_item, self.attacker.position)
        skill_system.pre_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        if self.attacker is not self.defender:
            skill_system.pre_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')

        skill_system.start_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        item_system.start_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')

        if self.attacker is not self.defender:
            skill_system.start_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')
            if self.def_item:
                item_system.start_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')

    def cleanup_combat(self):
        skill_system.cleanup_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        if self.attacker is not self.defender:
            skill_system.cleanup_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')

    def end_combat(self):
        skill_system.end_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        item_system.end_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        if self.attacker is not self.defender:
            skill_system.end_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')
            if self.def_item:
                item_system.end_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')

        skill_system.post_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        if self.attacker is not self.defender:
            skill_system.post_combat(self.full_playback, self.defender, self.def_item, self.attacker, 'defense')

    def _all_units(self) -> list:
        """
        Returns list of all units taking in this combat
        """
        all_units = [self.attacker]
        if self.attacker is not self.defender:
            all_units.append(self.defender)
        return all_units

    def handle_state_stack(self):
        pass
