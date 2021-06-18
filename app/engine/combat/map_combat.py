from app.constants import TILEWIDTH, TILEHEIGHT
from app.resources.resources import RESOURCES

from app.engine.combat.solver import CombatPhaseSolver

from app.engine.sound import SOUNDTHREAD
from app.engine import engine, combat_calcs, gui, action
from app.engine.health_bar import MapCombatInfo
from app.engine.animations import MapAnimation
from app.engine.game_state import game

from app.engine.combat.simple_combat import SimpleCombat

class MapCombat(SimpleCombat):
    alerts: bool = True
    
    def __init__(self, attacker, main_item, items, positions, main_target_positions, splash_positions, script):
        self._full_setup(attacker, main_item, items, positions, main_target_positions, splash_positions)
        self.state_machine = CombatPhaseSolver(
            attacker, self.main_item, self.items, 
            self.defenders, self.splashes, self.target_positions, 
            self.defender, self.def_item, script)

        self.last_update = engine.get_time()
        self.state = 'init'
        self.hp_bar_time = 400

        self._skip = False
        self.full_playback = []
        self.playback = []
        self.actions = []

        self.animations = []
        self.damage_numbers = []
        self.health_bars = {}

    def skip(self):
        self._skip = True
        self.attacker.sprite.reset()
        if self.defender:
            self.defender.sprite.reset()

    def update(self) -> bool:
        current_time = engine.get_time() - self.last_update

        # Only for the very first phase
        if self.state == 'init':
            if self._skip or current_time > 200:
                self.start_combat()
                self.state = 'begin_phase'
                self.last_update = engine.get_time()

        # print("Map Combat %s" % self.state)
        elif self.state == 'begin_phase':
            # Get playback
            if not self.state_machine.get_state():
                self.clean_up()
                return True
            self.actions, self.playback = self.state_machine.do()
            self.full_playback += self.playback
            if not self.actions and not self.playback:
                self.state_machine.setup_next_state()
                return False
            self._build_health_bars()

            # Camera
            if self.get_from_playback('defender_phase'):
                game.cursor.set_pos(self.attacker.position)
            else:
                if self.defender:
                    game.cursor.set_pos(self.defender.position)
                elif self.target_positions[0]:
                    game.cursor.set_pos(self.target_positions[0])
            if not self._skip:
                game.state.change('move_camera')

            # Sprites
            if self.get_from_playback('defender_phase'):
                if self.defender:
                    self.defender.sprite.change_state('combat_attacker')
                self.attacker.sprite.change_state('combat_counter')
            else:
                self.attacker.sprite.change_state('combat_attacker')
                if self.defender:
                    self.defender.sprite.change_state('combat_defender')
            self.state = 'red_cursor'

        elif self.state == 'red_cursor':
            if self.defender:
                game.cursor.combat_show()
            else:
                game.cursor.hide()
            self.state = 'start_anim'
            self.last_update = engine.get_time()

        elif self.state == 'start_anim':
            if self._skip or current_time > 400:
                game.cursor.hide()
                game.highlight.remove_highlights()
                animation_brushes = self.get_from_playback('cast_anim')
                for brush in animation_brushes:
                    anim = RESOURCES.animations.get(brush[1])
                    pos = game.cursor.position
                    if anim:
                        anim = MapAnimation(anim, pos)
                        self.animations.append(anim)
                self.state = 'sound'
                self.last_update = engine.get_time()

        elif self.state == 'sound':
            if self._skip or current_time > 250:
                if self.defender and self.defender.sprite.state == 'combat_attacker':
                    self.defender.sprite.change_state('combat_anim')
                else:
                    self.attacker.sprite.change_state('combat_anim')
                sound_brushes = self.get_from_playback('cast_sound')
                for brush in sound_brushes:
                    SOUNDTHREAD.play_sfx(brush[1])

                self.state = 'anim'
                self.last_update = engine.get_time()

        elif self.state == 'anim':
            if self._skip or current_time > 83:
                self._handle_playback()
                self._apply_actions()

                # Force update hp bars so we can get timing info
                for hp_bar in self.health_bars.values():
                    hp_bar.update()
                if self.health_bars:
                    self.hp_bar_time = max(hp_bar.get_time_for_change() for hp_bar in self.health_bars.values())
                else:
                    self.hp_bar_time = 0
                self.state = 'hp_bar_wait'
                self.last_update = engine.get_time()

        elif self.state == 'hp_bar_wait':
            if self._skip or current_time > self.hp_bar_time:
                self.state = 'end_phase'
                self.last_update = engine.get_time()

        elif self.state == 'end_phase':
            if self._skip or current_time > 550:
                if self.defender and self.defender.sprite.state == 'combat_anim':
                    self.defender.sprite.change_state('combat_attacker')
                else:
                    self.attacker.sprite.change_state('combat_attacker')
                self._end_phase()
                self.state_machine.setup_next_state()
                self.state = 'begin_phase'

        if self.state not in ('begin_phase', 'red_cursor'):
            for hp_bar in self.health_bars.values():
                hp_bar.update()

        return False

    def _build_health_bars(self):
        if (self.defender and self.all_splash) or len(self.all_splash) > 1:
            # Many splash attacks
            # No health bars!!
            self.health_bars.clear()

        else:
            # P1 on P1
            if self.defender and self.attacker is self.defender:
                hit = combat_calcs.compute_hit(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
                mt = combat_calcs.compute_damage(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
                if self.attacker not in self.health_bars:
                    attacker_health = MapCombatInfo('p1', self.attacker, self.main_item, self.defender, (hit, mt))
                    self.health_bars[self.attacker] = attacker_health
                else:
                    self.health_bars[self.attacker].update_stats((hit, mt))

            # P1 on P2
            elif self.defender:
                hit = combat_calcs.compute_hit(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
                mt = combat_calcs.compute_damage(self.attacker, self.defender, self.main_item, self.def_item, 'attack')
                if self.attacker not in self.health_bars:
                    attacker_health = MapCombatInfo('p1', self.attacker, self.main_item, self.defender, (hit, mt))
                    self.health_bars[self.attacker] = attacker_health
                else:
                    self.health_bars[self.attacker].update_stats((hit, mt))

                if combat_calcs.can_counterattack(self.attacker, self.main_item, self.defender, self.def_item):
                    hit = combat_calcs.compute_hit(self.defender, self.attacker, self.def_item, self.main_item, 'defense')
                    mt = combat_calcs.compute_damage(self.defender, self.attacker, self.def_item, self.main_item, 'defense')
                else:
                    hit, mt = None, None
                if self.defender not in self.health_bars:
                    defender_health = MapCombatInfo('p2', self.defender, self.def_item, self.attacker, (hit, mt))
                    self.health_bars[self.defender] = defender_health
                else:
                    self.health_bars[self.defender].update_stats((hit, mt))

            # P1 on single splash
            elif len(self.all_splash) == 1:
                defender = self.all_splash[0]
                hit = combat_calcs.compute_hit(self.attacker, defender, self.main_item, None, 'attack')
                mt = combat_calcs.compute_damage(self.attacker, defender, self.main_item, None, 'attack')
                if self.attacker not in self.health_bars:
                    attacker_health = MapCombatInfo('p1', self.attacker, self.main_item, defender, (hit, mt))
                    self.health_bars[self.attacker] = attacker_health
                else:
                    self.health_bars[self.attacker].update_stats((hit, mt))

                if defender not in self.health_bars:
                    splash_health = MapCombatInfo('splash', defender, None, self.attacker, (None, None))
                    self.health_bars[defender] = splash_health

    def _handle_playback(self):
        for brush in self.playback:
            if brush[0] == 'unit_tint_add':
                color = brush[2]
                brush[1].sprite.begin_flicker(333, color, 'add')
            elif brush[0] == 'unit_tint_sub':
                color = brush[2]
                brush[1].sprite.begin_flicker(333, color, 'sub')
            elif brush[0] == 'crit_tint':
                color = brush[2]
                brush[1].sprite.begin_flicker(33, color, 'add')
                # Delay five frames
                brush[1].sprite.start_flicker(83, 33, color, 'add')
                # Delay five more frames
                brush[1].sprite.start_flicker(166, 333, color, 'add', fade_out=True)
            elif brush[0] == 'crit_vibrate':
                # In 10 frames, start vibrating for 12 frames
                brush[1].sprite.start_vibrate(166, 200)
            elif brush[0] == 'hit_sound':
                sound = brush[1]
                SOUNDTHREAD.play_sfx(sound)
            elif brush[0] == 'shake':
                shake = brush[1]
                for health_bar in self.health_bars.values():
                    health_bar.shake(shake)
            elif brush[0] == 'hit_anim':
                anim = RESOURCES.animations.get(brush[1])
                pos = brush[2].position
                if anim and pos:
                    anim = MapAnimation(anim, pos)
                    self.animations.append(anim)
            elif brush[0] == 'damage_hit':
                damage = brush[4]
                if damage <= 0:
                    continue
                str_damage = str(damage)
                left = brush[3].position
                for idx, num in enumerate(str_damage):
                    d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'small_red')
                    self.damage_numbers.append(d)
            elif brush[0] == 'damage_crit':
                damage = brush[4]
                if damage <= 0:
                    continue
                str_damage = str(damage)
                left = brush[3].position
                for idx, num in enumerate(str_damage):
                    d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'small_yellow')
                    self.damage_numbers.append(d)
            elif brush[0] == 'heal_hit':
                damage = brush[4]
                if damage <= 0:
                    continue
                str_damage = str(damage)
                left = brush[3].position
                for idx, num in enumerate(str_damage):
                    d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'small_cyan')
                    self.damage_numbers.append(d)

    def _apply_actions(self):
        """
        Actually commit the actions that we had stored!
        """
        for act in self.actions:
            action.do(act)

    def _end_phase(self):
        pass

    def draw(self, surf):
        # Animations
        self.animations = [anim for anim in self.animations if not anim.update()]
        for anim in self.animations:
            anim.draw(surf, offset=(-game.camera.get_x(), -game.camera.get_y()))
        
        for hp_bar in self.health_bars.values():
            hp_bar.draw(surf)

        # Damage Nums
        for damage_num in self.damage_numbers:
            damage_num.update()
            position = damage_num.left
            c_pos = game.camera.get_xy()
            rel_x = position[0] - c_pos[0]
            rel_y = position[1] - c_pos[1]
            damage_num.draw(surf, (rel_x * TILEWIDTH + 4, rel_y * TILEHEIGHT))
        self.damage_numbers = [d for d in self.damage_numbers if not d.done]

        return surf
