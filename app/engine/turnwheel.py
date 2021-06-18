from dataclasses import dataclass
from app.constants import WINWIDTH, WINHEIGHT

from app.engine.sound import SOUNDTHREAD
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine.input_manager import INPUT

from app.engine.game_state import game
import app.engine.action as Action
from app.engine.background import SpriteBackground
from app.engine.state import MapState
from app.engine import engine, base_surf, image_mods, gui

import logging

class ActionLog():
    def __init__(self):
        self.actions = []
        self.action_index = -1  # Means no actions
        self.first_free_action = -1
        self.locked = False
        self.record = True  # Whether the action log is currently recording
        self.action_depth = 0

        # For playback
        self.current_unit = None
        self.hovered_unit = None
        self.current_move = None
        self.current_move_index = 0
        self.unique_moves = []

    def append(self, action):
        logging.debug("Add Action %d: %s", self.action_index + 1, action.__class__.__name__)
        self.actions.append(action)
        self.action_index += 1

    def remove(self, action):
        logging.debug("Remove Action %d: %s", self.action_index, action.__class__.__name__)
        self.actions.remove(action)
        self.action_index -= 1

    def hard_remove(self, action):
        """
        Removes action and all actions that happened after it
        """
        logging.debug("Hard Remove Action %d: %s", self.action_index, action.__class__.__name__)
        idx = self.actions.index(action)
        diff = len(self.actions) - idx
        self.action_index -= diff
        self.actions = self.actions[:idx]
        logging.debug("New Action Index: %d", self.action_index)

    def run_action_backward(self):
        action = self.actions[self.action_index]
        action.reverse()
        self.action_index -= 1
        return action

    def run_action_forward(self):
        self.action_index += 1
        action = self.actions[self.action_index]
        action.execute()
        return action

    def at_far_past(self):
        return not self.actions or self.action_index <= self.first_free_action

    def at_far_future(self):
        return not self.actions or self.action_index + 1 >= len(self.actions)

    @dataclass
    class Move():
        unit: str = None
        begin: int = None
        end: int = None

        def __repr__(self):
            return "Move: %s (%s %s)" % (self.unit.nid, self.begin, self.end)

    def set_up(self):
        def finalize(move):
            if isinstance(move, self.Move) and move.end is None:
                move.end = move.begin
            self.unique_moves.append(move)
        
        # Pay attention to which actions the turnwheel actually has to know about
        self.unique_moves.clear()
        current_move = None

        for action_index in range(self.first_free_action, len(self.actions)):
            action = self.actions[action_index]
            # Only regular moves, not CantoMove or other nonsense gets counted
            if type(action) == Action.Move or type(action) == Action.Teleport:
                if current_move:
                    finalize(current_move)
                current_move = self.Move(action.unit, action_index)
            elif isinstance(action, Action.Wait) or isinstance(action, Action.Die):
                if current_move and action.unit == current_move.unit:
                    current_move.end = action_index
                    finalize(current_move)
                    current_move = None
            elif isinstance(action, Action.MarkPhase):
                if current_move:
                    finalize(current_move)
                    current_move = None
                self.unique_moves.append(('Phase', action_index, action.phase_name))
            elif isinstance(action, Action.LockTurnwheel):
                if current_move:
                    finalize(current_move)
                    current_move = None
                self.unique_moves.append(('Lock', action_index, action.lock))

        # Handles having extra actions off the right of the action log
        if self.unique_moves:
            last_move = self.unique_moves[-1]
            last_action_index = len(self.actions) - 1
            if isinstance(last_move, self.Move):
                if last_move.end < last_action_index:
                    self.unique_moves.append(('Extra', last_move.end + 1, last_action_index))
            elif last_move[1] < last_action_index:
                self.unique_moves.append(('Extra', last_move[1] + 1, last_action_index))

        logging.debug("*** Turnwheel Begin ***")
        logging.debug(self.unique_moves)

        self.current_move_index = len(self.unique_moves)

        # Determine starting lock
        self.locked = self.get_last_lock()

        # Get the text message
        for move in reversed(self.unique_moves):
            if isinstance(move, self.Move):
                if move.end:
                    text_list = self.get_unit_turn(move.unit, move.end)
                    return text_list
                return []
            elif move[0] == 'Phase':
                return ["Start of %s phase" % move[2].capitalize()]
        return []

    def backward(self):
        if self.current_move_index < 1:
            return None

        self.current_move = self.unique_moves[self.current_move_index - 1]
        logging.debug("Backward %s %s %s", self.current_move_index, self.current_move, self.action_index)
        self.current_move_index -= 1
        action = None

        if isinstance(self.current_move, self.Move):
            if self.current_unit:
                while self.action_index >= self.current_move.begin:
                    action = self.run_action_backward()
                game.cursor.set_pos(self.current_unit.position)
                self.current_unit = None
                return []
            else:
                if self.hovered_unit:
                    self.hover_off()
                self.current_unit = self.current_move.unit
                if self.current_move.end:
                    while self.action_index > self.current_move.end:
                        action = self.run_action_backward()
                    prev_action = None
                    if self.action_index >= 1:
                        prev_action = self.actions[self.action_index]
                        logging.debug("Prev Action %s", prev_action)
                    if self.current_unit.position:
                        game.cursor.set_pos(self.current_unit.position)
                    # Unless the current unit just DIED!
                    elif isinstance(prev_action, Action.Die):
                        if prev_action.old_pos:
                            game.cursor.set_pos(prev_action.old_pos)
                    self.hover_on(self.current_unit)
                    text_list = self.get_unit_turn(self.current_unit, self.action_index)
                    self.current_move_index += 1
                    logging.debug("In Backward %s %s %s %s", text_list, self.current_unit.nid, self.current_unit.position, prev_action)
                    return text_list
                else:
                    while self.action_index >= self.current_move.begin:
                        action = self.run_action_backward()
                    game.cursor.set_pos(self.current_unit.position)
                    self.hover_on(self.current_unit)
                    return []

        elif self.current_move[0] == 'Phase':
            while self.action_index > self.current_move[1]:
                action = self.run_action_backward()
            if self.hovered_unit:
                self.hover_off()
            if self.current_move[2] == 'player':
                game.cursor.autocursor()
            return ["Start of %s phase" % self.current_move[2].capitalize()]

        elif self.current_move[0] == 'Lock':
            while self.action_index >= self.current_move[1]:
                action = self.run_action_backward()
            self.locked = self.get_last_lock()
            return self.backward()  # Go again

        elif self.current_move[0] == 'Extra':
            while self.action_index >= self.current_move[1]:
                action = self.run_action_backward()
            return self.backward()  # Go again

    def forward(self):
        if self.current_move_index >= len(self.unique_moves):
            return None

        self.current_move = self.unique_moves[self.current_move_index]
        logging.debug("Forward %s %s %s", self.current_move_index, self.current_move, self.action_index)
        self.current_move_index += 1
        action = None

        if isinstance(self.current_move, self.Move):
            if self.current_unit:
                while self.action_index < self.current_move.end:
                    action = self.run_action_forward()
                if self.current_unit.position:
                    game.cursor.set_pos(self.current_unit.position)
                elif isinstance(action, Action.Die):
                    game.cursor.set_pos(action.old_pos)
                text_list = self.get_unit_turn(self.current_unit, self.action_index)
                logging.debug("In Forward %s %s %s", text_list, self.current_unit.name, action)
                self.current_unit = None
                # Extra Moves
                if self.current_move_index < len(self.unique_moves):
                    next_move = self.unique_moves[self.current_move_index]
                    if isinstance(next_move, tuple) and next_move[0] == 'Extra':
                        self.forward()  # Skip through the extra move
                return text_list
            else:  # Get the next hovered unit
                if self.hovered_unit:
                    self.hover_off()
                self.current_unit = self.current_move.unit
                while self.action_index < self.current_move.begin - 1:
                    # Does next action, so -1 is necessary
                    action = self.run_action_forward()
                game.cursor.set_pos(self.current_unit.position)
                self.hover_on(self.current_unit)
                self.current_move_index -= 1  # Make sure we don't skip second half of this
                return []

        elif self.current_move[0] == 'Phase':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward()
            if self.hovered_unit:
                self.hover_off()
            if self.current_move[2] == 'player':
                game.cursor.autocursor()
            return ["Start of %s phase" % self.current_move[2].capitalize()]

        elif self.current_move[0] == 'Lock':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward()
            self.locked = self.current_move[2]
            return self.forward()  # Go again

        elif self.current_move[0] == 'Extra':
            while self.action_index < self.current_move[1]:
                action = self.run_action_forward()
            return []

    def finalize(self):
        """
        Removes all actions after the one we turned back to
        """
        self.current_unit = None
        if self.hovered_unit:
            self.hover_off()
        self.actions = self.actions[:self.action_index + 1]

    def reset(self):
        """
        Pretend we never touched turnwheel
        """
        self.current_unit = None
        if self.hovered_unit:
            self.hover_off()
        while not self.at_far_future():
            self.run_action_forward()

    def get_last_lock(self):
        cur_index = self.action_index
        while cur_index > self.first_free_action:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.LockTurnwheel):
                return cur_action.lock
        return False  # Assume not locked

    def get_current_phase(self):
        cur_index = self.action_index
        while cur_index > 0:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.MarkPhase):
                return cur_action.phase_name
        return 'player'

    def is_turned_back(self):
        return self.action_index + 1 < len(self.actions)

    def can_use(self):
        return self.is_turned_back() and not self.locked

    def get_unit_turn(self, unit, wait_index):
        cur_index = wait_index
        text = []
        while cur_index > self.first_free_action:
            cur_index -= 1
            cur_action = self.actions[cur_index]
            if isinstance(cur_action, Action.Message):
                text.insert(0, cur_action.message)
            elif isinstance(cur_action, Action.Move):
                return text

    def get_previous_position(self, unit):
        for action in reversed(self.actions):
            if isinstance(action, Action.Move):
                if action.unit == unit:
                    return action.old_pos
        return unit.position

    def set_first_free_action(self):
        if self.first_free_action == -1:
            logging.debug("*** First Free Action ***")
            self.first_free_action = self.action_index

    def hover_on(self, unit):
        game.cursor.set_turnwheel_sprite()
        self.hovered_unit = unit

    def hover_off(self):
        game.cursor.hide()
        self.hovered_unit = None

    def save(self):
        return ([action.save() for action in self.actions], self.first_free_action)

    @classmethod
    def restore(cls, serial):
        self = cls()
        actions, first_free_action = serial
        for name, action in actions:
            self.append(getattr(Action, name).restore(action))
        self.first_free_action = first_free_action
        return self

class TurnwheelDisplay():
    # locked_sprite = engine.image_load(SPRITES['focus_fade_red'].full_path, convert_alpha=True)
    # unlocked_sprite = engine.image_load(SPRITES['focus_fade_green'].full_path, convert_alpha=True)
    locked_sprite = SPRITES.get('focus_fade_red')
    unlocked_sprite = SPRITES.get('focus_fade_green')

    def __init__(self, desc, turn):
        self.desc = desc
        self.turn = turn
        self.state = 'in'
        self.transition = -24

    def change_text(self, desc, turn):
        self.desc = desc
        self.turn = turn

    def fade_out(self):
        self.state = 'out'

    def draw(self, surf):
        if self.state == 'in':
            self.transition += 2
            if self.transition >= 0:
                self.transition = 0
                self.state = 'normal'
        elif self.state == 'out':
            self.transition -= 2

        if game.action_log.locked:
            surf.blit(self.locked_sprite, (0, 0))
        else:
            surf.blit(self.unlocked_sprite, (0, 0))

        # Turnwheel message
        if self.desc:
            font = FONT['text-white']
            num_lines = len(self.desc)
            bg = base_surf.create_base_surf(WINWIDTH, 8 + font.height * num_lines, 'menu_bg_clear')
            for idx, line in enumerate(self.desc):
                font.blit(line, bg, (4, 4 + font.height * idx))
            if self.transition != 0:
                bg = image_mods.make_translucent(bg, -self.transition/24.)
            surf.blit(bg, (0, 0))

        # Turncount
        golden_words_surf = SPRITES.get('golden_words')
        # Get turn
        turn_surf = engine.subsurface(golden_words_surf, (0, 17, 26, 10))
        turn_bg = base_surf.create_base_surf(48, 24)
        turn_bg = image_mods.make_translucent(turn_bg, .1)
        turn_bg.blit(turn_surf, (4, 6))
        FONT['text-blue'].blit_right(str(self.turn), turn_bg, (44, 3))
        surf.blit(turn_bg, (WINWIDTH - 52, 4 + self.transition))
        # Unit Count
        count_bg = base_surf.create_base_surf(48, 24)
        count_bg = image_mods.make_translucent(count_bg, .1)
        player_units = [unit for unit in game.units if unit.team == 'player' and unit.position]
        unused_units = [unit for unit in player_units if not unit.finished]
        count_str = str(len(unused_units)) + "/" + str(len(player_units))
        count_width = FONT['text-blue'].width(count_str)
        FONT['text-blue'].blit(count_str, count_bg, (24 - count_width/2, 3))
        surf.blit(count_bg, (4, WINHEIGHT - 28 - self.transition))
        # Num uses
        if game.game_vars.get('_max_turnwheel_uses', -1) > 0:
            uses_bg = base_surf.create_base_surf(48, 24)
            uses_bg = image_mods.make_translucent(uses_bg, .1)
            uses_text = str(game.game_vars['_current_turnwheel_uses']) + ' Left'
            x = 48 - FONT['text-blue'].width(uses_text) - 8
            FONT['text-blue'].blit(uses_text, uses_bg, (x, 4))
            surf.blit(uses_bg, (WINWIDTH - 52, WINHEIGHT - 28 - self.transition))

class TurnwheelState(MapState):
    def begin(self):
        # Whether the player MUST move the turnwheel back
        self.force = game.memory.get('force_turnwheel', False)
        game.memory['force_turnwheel'] = False

        self.mouse_indicator = gui.MouseIndicator()
        # Kill off any units who are currently dying
        for unit in game.units:
            if unit.is_dying:
                game.death.force_death(unit)

        game.action_log.record = False

        # Lower volume

        self.bg = SpriteBackground(SPRITES.get('focus_fade'), fade=True)
        turnwheel_desc = game.action_log.set_up()
        self.display = TurnwheelDisplay(turnwheel_desc, game.turncount)

        self.transition_out = 0
        self.turnwheel_activated = False

        # For darken background and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.end_effect = None
        self.particles = []

        self.last_direction = 'FORWARD'

    def move_forward(self):
        SOUNDTHREAD.play_sfx('Select 1')
        old_message = None
        if self.last_direction == 'BACKWARD':
            game.action_log.current_unit = None
            old_message = game.action_log.forward()
        new_message = game.action_log.forward()
        if new_message is None:
            new_message = old_message
        if new_message is not None:
            self.display.change_text(new_message, game.turncount)
        self.last_direction = 'FORWARD'

    def move_back(self):
        SOUNDTHREAD.play_sfx('Select 2')
        old_message = None
        if self.last_direction == 'FORWARD':
            game.action_log.current_unit = None
            old_message = game.action_log.backward()
        new_message = game.action_log.backward()
        if new_message is None:
            new_message = old_message
        if new_message is not None:
            self.display.change_text(new_message, game.turncount)
        self.last_direction = 'BACKWARD'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        if self.transition_out > 0:
            return  # Don't take input after a choice has been made

        if 'DOWN' in directions or 'RIGHT' in directions:
            self.move_forward()
        elif 'UP' in directions or 'LEFT' in directions:
            self.move_back()

        if event == 'SELECT':
            if self.check_mouse_position():
                pass
            elif game.action_log.can_use():
                game.action_log.finalize()
                self.transition_out = 60
                self.display.fade_out()
                self.turnwheel_effect()
                self.bg.fade_out()
                self.turnwheel_activated = True
                if game.game_vars['_current_turnwheel_uses'] > 0:
                    game.game_vars['_current_turnwheel_uses'] -= 1
            elif not self.force and not game.action_log.locked:
                self.back_out()
            else:
                SOUNDTHREAD.play_sfx('Error')

        elif event == 'BACK':
            if not self.force:
                self.back_out()
            else:
                SOUNDTHREAD.play_sfx('Error')

    def check_mouse_position(self) -> bool:
        mouse_position = INPUT.get_mouse_position()
        if mouse_position:
            mouse_x, mouse_y = mouse_position
            if mouse_x <= 16:
                self.move_back()
                return True
            elif mouse_x >= WINWIDTH - 16:
                self.move_forward()
                return True
            elif mouse_y <= 16:
                self.move_back()
                return True
            elif mouse_y >= WINHEIGHT - 16:
                self.move_forward()
                return True
        return False

    def back_out(self):
        game.action_log.reset()
        self.transition_out = 24
        self.display.fade_out()
        self.bg.fade_out()

    def turnwheel_effect(self):
        pass
        # Add effect and warp flowers

    def update(self):
        super().update()

        if self.transition_out > 0:
            self.transition_out -= 1
            if self.transition_out <= 0:
                if game.phase.get_current() == 'player':
                    game.state.back()
                    game.state.back()
                else:
                    game.state.clear()
                    game.state.change('free')
                    game.phase.set_player()
                # Call turnwheel script whenever the turnwheel is used
                if self.turnwheel_activated:
                    game.events.trigger('on_turnwheel')

        # Update animations
        # if self.end_effect:
        #     self.end_effect.update()

    def darken(self):
        self.target_dark += 4

    def lighten(self):
        self.target_dark -= 4

    def draw(self, surf):
        surf = super().draw(surf)
        if self.bg:
            self.bg.draw(surf)
        if self.display:
            self.display.draw(surf)

        if self.darken_background or self.target_dark:
            # Only used by Turnwheel flash
            bg = image_mods.make_translucent(SPRITES.get('bg_black'), 1 - self.darken_background/8.)
            surf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 1
            elif self.target_dark < self.darken_background:
                self.darken_background -= 1

        self.mouse_indicator.draw(surf)

        # Draw animation
        return surf

    def end(self):
        game.boundary.reset()
        # Set volume back
        game.action_log.record = True
