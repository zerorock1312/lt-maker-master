from app.data.database import DB

from app.engine.sound import SOUNDTHREAD
from app.engine.state import State
import app.engine.config as cf
from app.engine.game_state import game

import logging

class EventState(State):
    name = 'event'
    transparent = True
    event = None

    def begin(self):
        logging.debug("Begin Event State")
        self.game_over: bool = False  # Whether we've called for a game over
        if not self.event:
            self.event = game.events.get()
            if self.event and game.cursor:
                game.cursor.hide()

    def take_input(self, event):
        if event == 'START' or event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            self.event.skip(event == 'START')

        elif event == 'SELECT' or event == 'RIGHT' or event == 'DOWN':
            if self.event.state == 'dialog':
                if not cf.SETTINGS['talk_boop']:
                    SOUNDTHREAD.play_sfx('Select 1')
                self.event.hurry_up()

    def update(self):
        if self.game_over:
            return

        if self.event:
            self.event.update()
        else:
            logging.debug("Event complete")
            game.state.back()
            return 'repeat'

        if self.event.state == 'paused':
            return 'repeat'

        elif self.event.state == 'complete':
            return self.end_event()

    def draw(self, surf):
        if self.event:
            self.event.draw(surf)

        return surf

    def level_end(self):
        current_level_index = DB.levels.index(game.level.nid)
        game.clean_up()
        if current_level_index < len(DB.levels) - 1:
            # Assumes no overworld
            if game.game_vars.get('_goto_level'):
                if game.game_vars['_goto_level'] == '_force_quit':
                    game.state.clear()
                    game.state.change('title_start')
                else:
                    game.game_vars['_next_level_nid'] = game.game_vars['_goto_level']
                    game.game_vars['_goto_level'] = None
            else:
                next_level = DB.levels[current_level_index + 1]
                if 'debug' in next_level.nid.lower():
                    logging.info('No more levels!')
                    game.state.clear()
                    game.state.change('title_start')
                    return
                else:  # DEBUG
                    game.game_vars['_next_level_nid'] = next_level.nid
            game.state.clear()
            logging.info('Creating save...')
            game.memory['save_kind'] = 'start'
            game.state.change('title_save')
        else:
            logging.info('No more levels!')
            game.state.clear()
            game.state.change('title_start')

    def end_event(self):
        logging.debug("Ending Event")
        game.events.end(self.event)
        if game.level_vars.get('_win_game'):
            logging.info("Player Wins!")
            # Update statistics here, if necessary
            if game.level_vars.get('_level_end_triggered'):
                self.level_end()
            else:
                did_trigger = game.events.trigger('level_end')
                if did_trigger:
                    game.level_vars['_level_end_triggered'] = True
                else:
                    self.level_end()

        elif game.level_vars.get('_lose_game'):
            self.game_over = True
            game.memory['next_state'] = 'game_over'
            game.state.change('transition_to')

        elif self.event.battle_save_flag:
            game.memory['save_kind'] = 'battle'
            game.memory['next_state'] = 'in_chapter_save'
            game.state.change('transition_to')
            self.event.battle_save_flag = False

        elif self.event.turnwheel_flag:
            game.state.change('turnwheel')
            if self.event.turnwheel_flag == 2:
                game.memory['force_turnwheel'] = True
            else:
                game.memory['force_turnwheel'] = False
            self.event.turnwheel_flag = False

        else:
            game.state.back()

        return 'repeat'
