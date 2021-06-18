from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT

from app.counters import generic3counter, simplecounter, movement_counter

from app.utilities.utils import frames2ms
from app.engine import engine
from app.engine.game_state import game

import time

class MapView():
    def __init__(self):
        self.passive_sprite_counter = generic3counter(frames2ms(32), frames2ms(4))
        self.active_sprite_counter = generic3counter(frames2ms(13), frames2ms(6))
        self.move_sprite_counter = simplecounter((frames2ms(10), frames2ms(5), frames2ms(10), frames2ms(5)))
        self.fast_move_sprite_counter = simplecounter((frames2ms(6), frames2ms(3), frames2ms(6), frames2ms(3)))
        self.attack_movement_counter = movement_counter()
        self.arrow_counter = simplecounter((frames2ms(16), frames2ms(16), frames2ms(16)))
        self.x2_counter = simplecounter([frames2ms(3)] * 18)

    def update(self):
        current_time = engine.get_time()
        self.passive_sprite_counter.update(current_time)
        self.active_sprite_counter.update(current_time)
        self.move_sprite_counter.update(current_time)
        self.fast_move_sprite_counter.update(current_time)
        self.attack_movement_counter.update(current_time)
        self.arrow_counter.update(current_time)
        self.x2_counter.update(current_time)

    def draw_units(self, surf, cull_rect):
        # Update all units except the cur unit
        update_units = [unit for unit in game.units if (unit.position or unit.sprite.fake_position)]
        for unit in update_units:
            unit.sprite.update()
            unit.sound.update()

        pos_units = [unit for unit in update_units if unit is not game.cursor.cur_unit and (unit.position or unit.sprite.fake_position)]
        # Only draw units within 2 tiles of cull_rect
        culled_units = [unit for unit in pos_units if unit.sprite.draw_anyway() or
                        (cull_rect[0] - TILEWIDTH*2 < (unit.position or unit.sprite.fake_position)[0] * TILEWIDTH < cull_rect[0] + cull_rect[2] + TILEWIDTH*2 and
                         cull_rect[1] - TILEHEIGHT*2 < (unit.position or unit.sprite.fake_position)[1] * TILEHEIGHT < cull_rect[1] + cull_rect[3] + TILEHEIGHT*2)]
        if game.level_vars.get('_fog_of_war'):
            culled_units = [unit for unit in culled_units if game.board.in_vision(unit.position or unit.sprite.fake_position)]
        draw_units = sorted(culled_units, key=lambda unit: unit.position[1] if unit.position else unit.sprite.fake_position[1])
        
        for unit in draw_units:
            surf = unit.sprite.draw(surf, cull_rect)
            if 'event' not in game.state.state_names():
                surf = unit.sprite.draw_hp(surf, cull_rect)
        for unit in draw_units:
            surf = unit.sprite.draw_markers(surf, cull_rect)

        # Draw the movement arrows
        surf = game.cursor.draw_arrows(surf, cull_rect)

        # Draw the main unit
        cur_unit = game.cursor.cur_unit
        if cur_unit and (cur_unit.position or cur_unit.sprite.fake_position):
            surf = cur_unit.sprite.draw(surf, cull_rect)
            if 'event' not in game.state.state_names():
                surf = cur_unit.sprite.draw_hp(surf, cull_rect)
                surf = cur_unit.sprite.draw_markers(surf, cull_rect)

    def draw(self):
        # start = time.time_ns()
        game.tilemap.update()
        # Camera Cull
        cull_rect = int(game.camera.get_x() * TILEWIDTH), int(game.camera.get_y() * TILEHEIGHT), WINWIDTH, WINHEIGHT
        full_size = game.tilemap.width * TILEWIDTH, game.tilemap.height * TILEHEIGHT

        map_image = game.tilemap.get_full_image(cull_rect)

        surf = engine.copy_surface(map_image)
        surf = surf.convert_alpha()

        surf = game.boundary.draw(surf, full_size, cull_rect)
        surf = game.boundary.draw_fog_of_war(surf, full_size, cull_rect)
        surf = game.highlight.draw(surf, cull_rect)

        self.draw_units(surf, cull_rect)

        surf = game.cursor.draw(surf, cull_rect)
        for weather in game.tilemap.weather:
            weather.update()
            weather.draw(surf, cull_rect[0], cull_rect[1])

        surf = game.ui_view.draw(surf)
        # print((time.time_ns() - start)/1e6)
        return surf
