from app.engine.sound import SOUNDTHREAD
from app.engine.sprites import SPRITES
from app.engine.state import State
from app.engine import background, image_mods, engine

from app.engine.game_state import game

class GameOverState(State):
    name = 'game_over'

    game_over_fade = SPRITES.get('game_over_fade').convert_alpha()

    def start(self):
        """
        Displays the game over screen for a little transition,
        then cut to start screen
        """
        initial_state = 'text_fade_in'
        self.state = initial_state
        self.text_transparency = 1
        # Music
        SOUNDTHREAD.fade_in('Game Over')

        self.text_surf = SPRITES.get('game_over_text')

        self.bg = background.TransitionBackground(SPRITES.get('game_over_bg'))
        game.memory['transition_speed'] = 0.1
        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        if self.state == 'stasis' and event:
            # Any input returns to start screen
            game.memory['next_state'] = 'title_start'
            game.state.change('transition_to')

    def update(self):
        if self.state == 'text_fade_in':
            self.text_transparency -= .02
            if self.text_transparency <= 0:
                self.text_transparency = 0
                self.state = 'bg_fade_in'
                self.bg.set_update(engine.get_time())
        elif self.state == 'bg_fade_in':
            if self.bg.update():
                self.state = 'stasis'
        elif self.state == 'stasis':
            self.bg.update()

    def draw(self, surf):
        engine.fill(surf, (0, 0, 0))
        self.bg.draw(surf)
        text_surf = image_mods.make_translucent(self.text_surf, self.text_transparency)
        engine.blit_center(surf, text_surf)
        surf.blit(self.game_over_fade, (0, 0))
        return surf
