import math

from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.utilities import utils
from app.engine import engine, image_mods, icons, unit_funcs, action, banner
from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine.fonts import FONT
from app.engine.state import State
from app.engine.state_machine import SimpleStateMachine
from app.engine.animations import Animation
from app.engine.game_state import game

class ExpState(State):
    name = 'exp'
    transparent = True
    state = None

    def start(self):
        if game.exp_instance:
            self.unit, self.exp_gain, self.combat_object, self.starting_state = \
                game.exp_instance.pop()
        else:
            game.state.back()
            return 'repeat'
        # Check if we need to use a custom method
        self.method = None
        if game.memory.get('exp_method'):
            self.method = game.memory['exp_method']
            game.memory['exp_method'] = None

        self.old_exp = self.unit.exp
        self.old_level = self.unit.level
        self.unit_klass = DB.classes.get(self.unit.klass)
        self.auto_promote = (DB.constants.value('auto_promote') or 'AutoPromote' in self.unit.tags) and \
            self.unit_klass.turns_into and 'NoAutoPromote' not in self.unit.tags

        # For mana
        self.old_mana = self.unit.get_mana()
        self.max_mana = self.unit.get_max_mana()
        self.mana_to_gain = 0
        if game.mana_instance:
            self.mana_to_gain = game.mana_instance.pop()[1]
            if self.mana_to_gain + self.old_mana > self.max_mana:
                self.mana_to_gain = self.max_mana - self.old_mana
        self.mana_bar = None

        self.state = SimpleStateMachine(self.starting_state)
        self.start_time = engine.get_time()

        self.exp_bar = None
        self.level_up_animation = None
        self.level_up_screen = None

        if not self.auto_promote:
            max_exp = 100 * (self.unit_klass.max_level - self.old_level) - self.old_exp
            self.exp_gain = min(self.exp_gain, max_exp)

        self.total_time_for_exp = utils.frames2ms(self.exp_gain)  # 1 frame per exp

        self.stat_changes = None
        self.new_wexp = None

        if self.unit.level >= self.unit_klass.max_level and not self.auto_promote:
            # We're done here
            game.state.back()
            return 'repeat'

        self.level_up_sound_played = False

    def begin(self):
        game.cursor.hide()

    def create_level_up_logo(self):
        if self.combat_object:
            anim = RESOURCES.animations.get('LevelUpBattle')
            if anim:
                anim = Animation(anim, (0, 6))
                anim.set_tint_after_delay(40)
                self.level_up_animation = anim
        else:
            if self.unit.position:
                x, y = self.unit.position
                left = (x - game.camera.get_x() - 2) * TILEWIDTH
                top = (y - game.camera.get_y() - 1) * TILEHEIGHT
                pos = (left, top)
            else:
                pos = (WINWIDTH//2, WINHEIGHT//2)
            anim = RESOURCES.animations.get('LevelUpMap')
            if anim:
                anim = Animation(anim, pos)
                self.level_up_animation = anim

    def update(self):
        current_time = engine.get_time()

        # Initiating State
        if self.state.get_state() == 'init':
            self.exp_bar = ExpBar(self.old_exp, center=not self.combat_object)
            self.start_time = current_time

            if self.mana_to_gain or (self.unit.get_max_mana() > 0 and self.unit.get_mana() != self.unit.get_max_mana()):
                self.mana_bar = ManaBar(self.old_mana, center=not self.combat_object)
                self.mana_bar.bar_max = self.unit.get_max_mana()

            self.state.change('exp_wait')

        # Wait before starting to increment exp
        elif self.state.get_state() == 'exp_wait':
            self.exp_bar.update(self.old_exp)
            if self.mana_bar:
                self.mana_bar.update(self.old_mana)
            if current_time - self.start_time > 466:
                self.state.change('exp0')
                self.start_time = current_time
                SOUNDTHREAD.play_sfx('Experience Gain', True)

        # Increment exp until done or 100 exp is reached
        elif self.state.get_state() == 'exp0':
            progress = (current_time - self.start_time)/float(self.total_time_for_exp)
            exp_set = self.old_exp + progress * self.exp_gain
            exp_set = min(self.old_exp + self.exp_gain, exp_set)
            self.exp_bar.update(exp_set)
            exp_set = int(exp_set)

            if self.mana_bar:
                mana_set = self.old_mana + progress * self.mana_to_gain
                mana_set = min(self.old_mana + self.mana_to_gain, mana_set)
                self.mana_bar.update(mana_set)
                mana_set = int(mana_set)

            if exp_set >= self.old_exp + self.exp_gain:
                SOUNDTHREAD.stop_sfx('Experience Gain')

            if exp_set >= 100:
                max_level = self.unit_klass.max_level
                if self.unit.level >= max_level:  # Do I promote?
                    SOUNDTHREAD.stop_sfx('Experience Gain')
                    if self.auto_promote:
                        self.exp_bar.update(100)
                        SOUNDTHREAD.play_sfx('Level Up')
                    else:
                        self.exp_bar.update(99)
                    self.state.clear()
                    self.state.change('prepare_promote')
                    self.state.change('exp_leave')
                    self.exp_bar.fade_out()
                    self.start_time = current_time
                else:
                    self.state.change('exp100')

            elif current_time - self.start_time >= self.total_time_for_exp + 500:
                SOUNDTHREAD.stop_sfx('Experience Gain')  # Just in case
                self.state.clear()
                self.state.change('exp_leave')
                self.exp_bar.fade_out()
                self.start_time = current_time

        elif self.state.get_state() == 'exp_leave':
            done = self.exp_bar.update()
            if done:
                action.do(action.GainExp(self.unit, self.exp_gain))
                if self.mana_to_gain:
                    action.do(action.ChangeMana(self.unit, self.mana_to_gain))
                action.do(action.UpdateRecords('exp_gain', (self.unit.nid, self.exp_gain, self.unit.klass)))
                self.state.back()
                self.start_time = current_time
                # If we're ready to leave
                if len(self.state.state) <= 0:
                    game.state.back()
                # Otherwise, we're probably about to level up!

        elif self.state.get_state() == 'exp100':
            progress = (current_time - self.start_time)/float(self.total_time_for_exp)
            exp_set = self.old_exp + (self.exp_gain * progress) - 100
            exp_set = min(self.old_exp + self.exp_gain - 100, exp_set)
            self.exp_bar.update(exp_set)
            exp_set = int(exp_set)

            if exp_set >= self.old_exp + self.exp_gain - 100:
                SOUNDTHREAD.stop_sfx('Experience Gain')

            # Extra time to account for pause at end
            if current_time - self.start_time >= self.total_time_for_exp + 333:
                old_growth_points = self.unit.growth_points.copy()
                self.stat_changes = unit_funcs.get_next_level_up(self.unit, self.method)
                action.do(action.GrowthPointChange(self.unit, old_growth_points, self.unit.growth_points))
                action.do(action.IncLevel(self.unit))
                action.do(action.ApplyStatChanges(self.unit, self.stat_changes))
                action.do(action.UpdateRecords('level_gain', (self.unit.nid, self.unit.level, self.unit.klass)))
                self.create_level_up_logo()
                self.state.clear()
                self.state.change('level_up')
                self.state.change('exp_leave')
                self.exp_bar.fade_out()
                self.start_time = current_time

        elif self.state.get_state() == 'level_up':
            if not self.level_up_sound_played:
                SOUNDTHREAD.play_sfx('Level Up')
                self.level_up_sound_played = True

            if self.level_up_animation.update():
                if self.combat_object:
                    self.combat_object.darken_ui()
                self.state.change('level_screen')
                self.start_time = current_time

        elif self.state.get_state() == 'level_screen':
            if not self.level_up_screen:
                self.level_up_screen = LevelUpScreen(
                    self.unit, self.stat_changes, self.old_level, self.unit.level)
            if self.level_up_screen.update(current_time):
                game.state.back()
                game.events.trigger('unit_level_up', self.unit)
                if self.combat_object:
                    self.combat_object.lighten_ui()

                # check for weapon experience gain
                if self.new_wexp:
                    for weapon_nid, value in self.new_wexp.items():
                        action.do(action.AddWexp(self.unit, weapon_nid, value))

                # check for skill gain unless the unit is using a booster to
                # get to this screen
                if self.starting_state != "stat_booster":
                    unit_klass = DB.classes.get(self.unit.klass)
                    for level_needed, class_skill in unit_klass.learned_skills:
                        if self.unit.level == level_needed:
                            if class_skill == 'Feat':
                                game.memory['current_unit'] = self.unit
                                game.state.change('feat_choice')
                            else:
                                act = action.AddSkill(self.unit, class_skill)
                                action.do(act)
                                if act.skill_obj:
                                    game.alerts.append(banner.GiveSkill(self.unit, act.skill_obj))
                                    game.state.change('alert')

        # Wait 100 ms before transferring to the promotion state
        elif self.state.get_state() == 'prepare_promote':
            self.exp_bar.update()
            if current_time - self.start_time > 100:
                class_options = self.unit_klass.turns_into
                if self.auto_promote:
                    self.exp_bar.update(0)
                    if len(class_options) > 1:
                        game.memory['current_unit'] = self.unit
                        game.state.change('promotion_choice')
                        game.state.change('transition_out')
                        # We are leaving
                        self.state.clear()
                        self.state.change('wait')
                        self.start_time = current_time
                    elif len(class_options) == 1:
                        game.memory['current_unit'] = self.unit
                        game.memory['next_class'] = class_options[0]
                        game.state.change('promotion')
                        game.state.change('transition_out')  # We are leaving
                        self.state.clear()
                        self.state.change('wait')
                        self.start_time = current_time
                    else:
                        action.do(action.SetExp(self.unit, 99))
                        game.state.back()
                else:
                    action.do(action.SetExp(self.unit, 99))
                    game.state.back()

        elif self.state.get_state() in ('promote', 'class_change'):
            # TODO Combat Anims for Promotion
            old_anim = self.unit.battle_anim

            if self.state.get_state() == 'promote':
                promote_action = action.Promote(self.unit, game.memory['next_class'])
            else:
                promote_action = action.ClassChange(self.unit, game.memory['next_class'])
            self.stat_changes, self.new_wexp = promote_action.get_data()
            print(self.new_wexp)
            action.do(promote_action)
            action.do(action.UpdateRecords('level_gain', (self.unit.nid, self.unit.level, self.unit.klass)))

            if self.combat_object:
                self.combat_object.darken_ui()
                if old_anim:
                    self.combat_object.update_battle_anim(old_anim)

            self.state.clear()
            self.state.change('level_screen')
            self.start_time = current_time

        elif self.state.get_state() == 'stat_booster':
            self.stat_changes = game.memory['stat_changes']
            self.exp_gain = 0
            self.old_level = self.unit.level
            self.state.change('level_screen')
            self.start_time = current_time

        elif self.state.get_state() == 'wait':
            if current_time - self.start_time > 1000:  # Wait a while
                game.state.back()

    def draw(self, surf):
        if not self.state:
            return surf

        if self.state.get_state() in ('init', 'exp_wait', 'exp_leave', 'exp0', 'exp100', 'prepare_promote'):
            if self.mana_bar:
                self.mana_bar.draw(surf)
            if self.exp_bar:
                self.exp_bar.draw(surf)

        elif self.state.get_state() == 'level_up':
            if self.level_up_animation:
                self.level_up_animation.update()
                self.level_up_animation.draw(surf)

        elif self.state.get_state() == 'level_screen':
            if self.level_up_screen:
                self.level_up_screen.draw(surf)

        return surf

class LevelUpScreen():
    bg = SPRITES.get('level_screen')
    bg = bg.convert_alpha()
    width = bg.get_width()
    height = bg.get_height()

    spark_time = 350
    level_up_wait = 1366

    underline = SPRITES.get('stat_underline')

    def __init__(self, unit, stat_changes, old_level, new_level):
        self.unit = unit
        self.stat_list = [stat_changes.get(nid, 0) for nid in DB.stats.keys()]
        self.stat_list = self.stat_list[:8]  # Can only show first 8 stats on level up
        self.old_level = old_level
        self.new_level = new_level

        self.current_spark = -1

        self.unit_scroll_offset = 80
        self.screen_scroll_offset = self.width + 32
        self.underline_offset = 36

        self.animations = []
        self.arrow_animations = []

        self.state = 'scroll_in'
        self.start_time = 0

    def make_spark(self, topleft):
        anim = RESOURCES.animations.get('StatUpSpark')
        if anim:
            return Animation(anim, topleft)
        return None

    def get_position(self, i):
        if i >= 4:
            position = (self.width//2 + 8, (i - 4) * 16 + 35)
        else:
            position = (10, i * 16 + 35)
        return position

    def inc_spark(self):
        self.current_spark += 1
        if self.current_spark >= len(self.stat_list):
            return True
        elif self.stat_list[self.current_spark] == 0:
            return self.inc_spark()
        return False

    def update(self, current_time):
        if self.state == 'init_pause':
            if current_time - self.start_time > 268:
                self.state = 'scroll_in'
                self.start_time = current_time

        elif self.state == 'scroll_in':
            self.unit_scroll_offset = max(0, self.unit_scroll_offset - 8)
            self.screen_scroll_offset = max(0, self.screen_scroll_offset - 16)
            if self.unit_scroll_offset == 0 and self.screen_scroll_offset == 0:
                self.state = 'init_wait'
                self.start_time = current_time

        elif self.state == 'init_wait':
            if current_time - self.start_time > 500:
                if self.old_level == self.new_level:  # No level up spark
                    self.state = 'get_next_spark'
                else:
                    self.state = 'first_spark'
                    topleft = (87, 27)
                    self.animations.append(self.make_spark(topleft))
                    SOUNDTHREAD.play_sfx('Level_Up_Level')
                self.start_time = current_time

        elif self.state == 'scroll_out':
            self.unit_scroll_offset += 10
            self.screen_scroll_offset += 20
            if current_time - self.start_time > 500:
                return True  # Done

        elif self.state == 'first_spark':
            if current_time - self.start_time > self.spark_time:
                self.state = 'get_next_spark'
                self.start_time = current_time

        elif self.state == 'get_next_spark':
            done = self.inc_spark()
            if done:
                self.state = 'level_up_wait'
                self.start_time = current_time
            else:
                pos = self.get_position(self.current_spark)
                # Animations
                # Number
                increase = self.stat_list[self.current_spark]
                # Arrow
                if increase > 0:
                    anim = RESOURCES.animations.get('LevelUpArrow')
                elif increase < 0:
                    anim = RESOURCES.animations.get('LevelDownArrow')
                if anim:
                    arrow_animation = Animation(anim, (pos[0] + 45, pos[1] - 11), hold=True)
                    self.arrow_animations.append(arrow_animation)
                # Spark
                spark_pos = pos[0] + 14, pos[1] + 26
                spark_anim = self.make_spark(spark_pos)
                if spark_anim:
                    self.animations.append(spark_anim)

                if increase > 0:
                    anim = RESOURCES.animations.get('LevelUpNumber' + str(increase))
                elif increase < 0:
                    anim = RESOURCES.animations.get('LevelDownNumber' + str(-increase))
                if anim:
                    number_animation = Animation(anim, (pos[0] + 43, pos[1] + 49), delay=80, hold=True)
                    self.animations.append(number_animation)

                SOUNDTHREAD.play_sfx('Stat Up')
                self.underline_offset = 36 # for underline growing
                self.state = 'spark_wait'
                self.start_time = current_time

        elif self.state == 'spark_wait':
            if current_time - self.start_time > self.spark_time:
                self.state = 'get_next_spark'

        elif self.state == 'level_up_wait':
            if current_time - self.start_time > self.level_up_wait:
                self.animations.clear()
                self.state = 'scroll_out'
                self.start_time = current_time

    def draw(self, surf):
        sprite = self.bg.copy()
        # Changes through entire color wheel
        # from t = 0 to t = 1 in
        # 180 * 10 milliseconds
        t = math.sin(math.radians((engine.get_time()//10) % 180))
        new_color = image_mods.blend_colors((88, 16, -40), (-80, -32, 40), t)

        # Render top
        klass = DB.classes.get(self.unit.klass)
        FONT['text-white'].blit(klass.name, sprite, (12, 3))
        FONT['text-yellow'].blit('Lv', sprite, (self.width//2 + 12, 3))
        if self.state in ('scroll_in', 'init_wait'):
            level = str(self.old_level)
        else:
            level = str(self.new_level)
        width = FONT['text-blue'].width(level)
        FONT['text-blue'].blit(level, sprite, (self.width//2 + 50 - width, 3))

        # Render underlines
        new_underline_surf = image_mods.change_color(self.underline, new_color)
        for idx, num in enumerate(self.stat_list[:self.current_spark + 1]):
            if num != 0:  # Stat change
                if idx == self.current_spark:
                    rect = (self.underline_offset, 0,
                            new_underline_surf.get_width() - self.underline_offset, 3)
                    new_underline_surf = engine.subsurface(new_underline_surf, rect)
                    # Change underline offset
                    self.underline_offset = max(0, self.underline_offset - 6)
                    pos = self.get_position(idx)
                    pos = (pos[0] + self.underline_offset//2 + 1, pos[1] + 10)
                else:
                    pos = self.get_position(idx)
                    pos = (pos[0] + 4, pos[1] + 11)
                sprite.blit(new_underline_surf, pos)

        # Update and draw arrow animations
        self.arrow_animations = [a for a in self.arrow_animations if not a.update()]
        for animation in self.arrow_animations:
            animation.draw(sprite, blend=new_color)

        # Draw stats
        for idx, stat in enumerate(DB.stats.keys()):
            # Can only show first 8 stats on levelup
            if idx >= len(self.stat_list):
                continue
            pos = self.get_position(idx)
            name = DB.stats.get(stat).name
            FONT['text-yellow'].blit(name, sprite, pos)
            text = self.unit.stats[stat] - (self.stat_list[idx] if self.current_spark < idx else 0)
            width = FONT['text-blue'].width(str(text))
            FONT['text-blue'].blit(str(text), sprite, (pos[0] + 40 - width, pos[1]))

        pos = (6 - self.screen_scroll_offset, WINHEIGHT - 8 - self.height)
        surf.blit(sprite, pos)

        # Blit unit's pic
        right = WINWIDTH - 4
        bottom = WINHEIGHT + self.unit_scroll_offset
        icons.draw_portrait(surf, self.unit, bottomright=(right, bottom))

        # Update and draw animations
        self.animations = [a for a in self.animations if not a.update()]
        # offset = game.camera.get_x() * TILEWIDTH, game.camera.get_y() * TILEHEIGHT
        for animation in self.animations:
            animation.draw(surf)

        return surf

class ExpBar():
    background = engine.subsurface(SPRITES.get('expbar'), (0, 0, 136, 24))
    begin = engine.subsurface(SPRITES.get('expbar'), (0, 24, 3, 7))
    middle = engine.subsurface(SPRITES.get('expbar'), (3, 24, 1, 7))
    end = engine.subsurface(SPRITES.get('expbar'), (4, 24, 2, 7))
    width = 136
    height = 24
    bar_max = 100

    def __init__(self, old_exp, center=True):
        self.bg_surf = self.create_bg_surf()
        if center:
            self.pos = WINWIDTH//2 - self.width//2, WINHEIGHT//2 - self.height//2
        else:
            self.pos = WINWIDTH//2 - self.width//2, WINHEIGHT - self.height

        self.offset = self.height//2  # Start with fade in
        self.done = False

        self.num = old_exp

    def create_bg_surf(self):
        surf = engine.create_surface((self.width, self.height), transparent=True)
        surf.blit(self.background, (0, 0))
        surf.blit(self.begin, (7, 9))
        return surf

    def fade_out(self):
        self.done = True

    def update(self, exp: float = None):
        if self.done:
            self.offset += 1  # So fade in and out
            if self.offset >= self.height//2:
                return True
        elif self.offset > 0:
            self.offset -= 1

        if exp is not None:
            self.num = exp

    def draw(self, surf):
        new_surf = engine.copy_surface(self.bg_surf)

        # Blit correct number of sprites for middle of exp bar
        idx = int(100 * max(0, self.num) / self.bar_max)
        for x in range(idx):
            new_surf.blit(self.middle, (10 + x, 9))

        # Blit end of exp bar
        new_surf.blit(self.end, (10 + idx, 9))

        # Blit current amount of exp
        FONT['number-small3'].blit_right(str(int(self.num)), new_surf, (self.width - 4, 4))

        # Transition
        new_surf = engine.subsurface(new_surf, (0, self.offset, self.width, self.height - self.offset * 2))

        surf.blit(new_surf, (self.pos[0], self.pos[1] + self.offset))
        return surf

class ManaBar(ExpBar):
    background = engine.subsurface(SPRITES.get('manabar'), (0, 0, 136, 24))
    begin = engine.subsurface(SPRITES.get('manabar'), (0, 24, 3, 7))
    middle = engine.subsurface(SPRITES.get('manabar'), (3, 24, 1, 7))
    end = engine.subsurface(SPRITES.get('manabar'), (4, 24, 2, 7))

    def __init__(self, old_exp, center=True):
        super().__init__(old_exp, center)
        self.pos = self.pos[0], self.pos[1] - self.height
