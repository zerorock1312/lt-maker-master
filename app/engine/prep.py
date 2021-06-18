from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT

# from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine.fonts import FONT
from app.engine.state import State, MapState

from app.engine.background import SpriteBackground
from app.engine import config as cf
from app.engine.game_state import game
from app.engine import menus, banner, action, base_surf, background, \
    info_menu, engine, equations, item_funcs, text_funcs, image_mods, \
    convoy_funcs, item_system, gui
from app.engine.combat import interaction
from app.engine.fluid_scroll import FluidScroll

class PrepMainState(MapState):
    name = 'prep_main'
    bg = None
    menu = None

    def start(self):
        prep_music = game.game_vars.get('_prep_music')
        if prep_music:
            SOUNDTHREAD.fade_in(prep_music)
        game.cursor.hide()
        game.cursor.autocursor()
        game.boundary.hide()

        self.create_background()

        options = ['Manage', 'Formation', 'Options', 'Save', 'Fight']
        if game.level_vars.get('_prep_pick'):
            options.insert(0, 'Pick Units')
        if cf.SETTINGS['debug']:
            options.insert(0, 'Debug')
        self.menu = menus.Choice(None, options, topleft='center')

        # Force place any required units
        for unit in game.get_units_in_party():
            possible_position = game.get_next_formation_spot()
            if 'Required' in unit.tags and possible_position and not unit.position:
                action.ArriveOnMap(unit, possible_position).do()
        
        # Force reset all units
        action.do(action.ResetAll([unit for unit in game.units if not unit.dead]))

        self.fade_out = False
        self.last_update = 0

        # game.state.change('transition_in')
        # return 'repeat'
        # game.events.trigger('prep_start')

    def create_background(self):
        img = SPRITES.get('focus_fade').convert_alpha()
        self.bg = SpriteBackground(img)

    def take_input(self, event):
        if self.fade_out:
            return
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        elif event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            selection = self.menu.get_current()
            if selection == 'Debug':
                game.state.change('debug')
            elif selection == 'Pick Units':
                game.memory['next_state'] = 'prep_pick_units'
                game.state.change('transition_to')
            elif selection == 'Manage':
                game.memory['next_state'] = 'prep_manage'
                game.state.change('transition_to')
            elif selection == 'Formation':
                self.bg.fade_out()
                game.state.change('prep_formation')
            elif selection == 'Options':
                game.memory['next_state'] = 'settings_menu'
                game.state.change('transition_to')
            elif selection == 'Save':
                game.memory['save_kind'] = 'prep'
                game.memory['next_state'] = 'in_chapter_save'
                game.state.change('transition_to')
            elif selection == 'Fight':
                if any(unit.position for unit in game.units):
                    self.bg.fade_out()
                    self.menu = None
                    self.fade_out = True
                    self.last_update = engine.get_time()
                else:
                    SOUNDTHREAD.play_sfx('Select 4')
                    alert = banner.Custom("Must select at least one unit!")
                    game.alerts.append(alert)
                    game.state.change('alert')

    def update(self):
        super().update()
        if self.fade_out:
            if engine.get_time() - self.last_update > 300:
                game.state.back()
        elif self.menu:
            self.menu.update()

    def draw(self, surf):
        surf = super().draw(surf)
        if not self.bg:
            self.create_background()
        if self.bg:
            self.bg.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        return surf

class PrepPickUnitsState(State):
    name = 'prep_pick_units'

    def start(self):
        self.fluid = FluidScroll()
        player_units = game.get_units_in_party()
        stuck_units = [unit for unit in player_units if unit.position and not game.check_for_region(unit.position, 'formation')]
        unstuck_units = [unit for unit in player_units if unit not in stuck_units]

        units = stuck_units + sorted(unstuck_units, key=lambda unit: bool(unit.position), reverse=True)
        self.menu = menus.Table(None, units, (6, 2), (110, 24))
        self.menu.set_mode('position')

        self.bg = background.create_background('rune_background')
        game.memory['prep_bg'] = self.bg

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            self.menu.move_up(first_push)
        elif 'LEFT' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            self.menu.move_left(first_push)
        elif 'RIGHT' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            self.menu.move_right(first_push)

        if event == 'SELECT':
            unit = self.menu.get_current()
            if unit.position and not game.check_for_region(unit.position, 'formation'):
                SOUNDTHREAD.play_sfx('Select 4')  # Locked/Lord character
            elif unit.position and 'Required' in unit.tags:
                SOUNDTHREAD.play_sfx('Select 4')  # Required unit, can't be removed
            elif unit.position:
                SOUNDTHREAD.play_sfx('Select 1')
                action.LeaveMap(unit).do()
            else:
                possible_position = game.get_next_formation_spot()
                is_fatigued = False
                if DB.constants.value('fatigue') and game.game_vars.get('_fatigue') == 1:
                    if unit.get_fatigue() >= equations.parser.max_fatigue(unit):
                        is_fatigued = True
                if 'Blacklist' in unit.tags:  # Blacklisted unit can't be added
                    is_fatigued = True  
                if possible_position and not is_fatigued:
                    SOUNDTHREAD.play_sfx('Select 1')
                    action.do(action.ArriveOnMap(unit, possible_position))
                    action.do(action.Reset(unit))
                elif is_fatigued:
                    SOUNDTHREAD.play_sfx('Select 4')

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.change('transition_pop')

        elif event == 'INFO':
            game.memory['scroll_units'] = game.get_units_in_party()
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.menu.get_current()
            game.state.change('transition_to')

    def update(self):
        game.map_view.update()  # For menu
        self.menu.update()

    def draw_pick_units_card(self, surf):
        bg_surf = base_surf.create_base_surf(132, 24, 'menu_bg_white')
        player_units = game.get_units_in_party()
        on_map = [unit for unit in game.units if unit.position and unit in player_units and game.check_for_region(unit.position, 'formation')]
        num_slots = game.level_vars.get('_prep_slots')
        if num_slots is None:
            num_slots = len(game.get_all_formation_spots())
        num_on_map = len(on_map)
        pick_s = ['Pick ', str(num_slots - num_on_map), ' units  ', str(num_on_map), '/', str(num_slots)]
        pick_f = ['text-white', 'text-blue', 'text-white', 'text-blue', 'text-white', 'text-blue']
        left_justify = 8
        for word, font in zip(pick_s, pick_f):
            FONT[font].blit(word, bg_surf, (left_justify, 4))
            left_justify += FONT[font].width(word)
        surf.blit(bg_surf, (110, 4))

    def draw_fatigue_card(self, surf):
        # Useful for telling at a glance which units are fatigued
        bg_surf = base_surf.create_base_surf(132, 24)
        topleft = (110, 128 + 4)
        unit = self.menu.get_current()
        if unit.get_fatigue() >= equations.parser.max_fatigue(unit):
            text = text_funcs.translate('Fatigued')
        elif 'Blacklist' in unit.tags:
            text = text_funcs.translate('Away')
        else:
            text = text_funcs.translate('Ready!')
        FONT['text-white'].blit_center(text, bg_surf, (66, 4))
        surf.blit(bg_surf, topleft)

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        menus.draw_unit_items(surf, (4, 44), self.menu.get_current(), include_top=True)

        self.draw_pick_units_card(surf)
        if DB.constants.value('fatigue') and game.game_vars.get('_fatigue') == 1:
            self.draw_fatigue_card(surf)

        self.menu.draw(surf)
        return surf

class PrepFormationState(MapState):
    name = 'prep_formation'

    def begin(self):
        game.cursor.show()
        game.highlight.show_formation(game.get_all_formation_spots())
        game.boundary.show()

    def take_input(self, event):
        game.cursor.take_input()

        if event == 'INFO':
            info_menu.handle_info()

        elif event == 'AUX':
            pass

        elif event == 'SELECT':
            cur_unit = game.cursor.get_hover()
            if cur_unit:
                if game.check_for_region(game.cursor.position, 'formation'):
                    SOUNDTHREAD.play_sfx('Select 3')
                    game.state.change('prep_formation_select')
                else:
                    SOUNDTHREAD.play_sfx('Select 2')
                    if cur_unit.team == 'enemy' or cur_unit.team == 'enemy2':
                        SOUNDTHREAD.play_sfx('Select 3')
                        game.boundary.toggle_unit(cur_unit)
                    else:
                        SOUNDTHREAD.play_sfx('Error')

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 1')
            game.state.back()

        elif event == 'START':
            SOUNDTHREAD.play_sfx('Select 5')
            game.state.change('minimap')

    def update(self):
        super().update()
        game.highlight.handle_hover()

    def finish(self):
        game.ui_view.remove_unit_display()
        game.cursor.hide()
        game.highlight.hide_formation()
        game.highlight.remove_highlights()

class PrepFormationSelectState(MapState):
    name = 'prep_formation_select'
    marker = SPRITES.get('menu_hand_rotated')
    marker_offset = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1]

    def start(self):
        game.cursor.formation_show()
        self.last_update = engine.get_time()
        self.counter = 0
        self.unit = game.cursor.get_hover()

    def take_input(self, event):
        game.cursor.take_input()

        if event == 'SELECT':
            if game.check_for_region(game.cursor.position, 'formation'):
                SOUNDTHREAD.play_sfx('FormationSelect')
                cur_unit = game.cursor.get_hover()
                if cur_unit and cur_unit.team != 'player':
                    pass
                elif cur_unit:
                    game.leave(cur_unit)
                    game.leave(self.unit)
                    cur_unit.position, self.unit.position = self.unit.position, cur_unit.position
                    game.arrive(cur_unit)
                    game.arrive(self.unit)
                    action.UpdateFogOfWar(cur_unit).do()
                    action.UpdateFogOfWar(self.unit).do()
                else:
                    game.leave(self.unit)
                    self.unit.position = game.cursor.position
                    game.arrive(self.unit)
                    action.UpdateFogOfWar(self.unit).do()
                game.state.back()
                game.ui_view.remove_unit_display()
                game.highlight.remove_highlights()
            else:
                SOUNDTHREAD.play_sfx('Error')

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'AUX':
            game.cursor.set_pos(self.unit.position)

        elif event == 'INFO':
            info_menu.handle_info()

    def draw(self, surf):
        surf = super().draw(surf)

        # Draw static hand
        if self.unit:
            pos = self.unit.position
            x = (pos[0] - game.camera.get_x()) * TILEWIDTH + 2
            y = (pos[1] - game.camera.get_y() - 1) * TILEHEIGHT
            surf.blit(self.marker, (x, y))

        if game.check_for_region(game.cursor.position, 'formation'):
            pos = game.cursor.position
            while engine.get_time() - 50 > self.last_update:
                self.last_update += 50
                self.counter = self.counter % len(self.marker_offset)
            x = (pos[0] - game.camera.get_x()) * TILEWIDTH + 2
            y = (pos[1] - game.camera.get_y() - 1) * TILEHEIGHT + self.marker_offset[self.counter]
            surf.blit(self.marker, (x, y))

        return surf

def draw_funds(surf):
    # Draw R: Info display
    helper = engine.get_key_name(cf.SETTINGS['key_INFO']).upper()
    FONT['text-yellow'].blit(helper, surf, (123, 143))
    FONT['text-white'].blit(': Info', surf, (123 + FONT['text-blue'].width(helper), 143))
    # Draw Funds display
    surf.blit(SPRITES.get('funds_display'), (168, 137))
    money = str(game.get_money())
    FONT['text-blue'].blit_right(money, surf, (219, 141))

class PrepManageState(State):
    name = 'prep_manage'

    def start(self):
        self.fluid = FluidScroll()

        units = game.get_units_in_party()
        self.units = sorted(units, key=lambda unit: bool(unit.position), reverse=True)
        self.menu = menus.Table(None, self.units, (4, 3), (6, 0))
        self.menu.set_mode('unit')

        # Display
        self.quick_disp = self.create_quick_disp()

        if self.name.startswith('base') and game.memory['base_bg']:
            self.bg = game.memory['base_bg']
        else:
            self.bg = background.create_background('rune_background')
        game.memory['prep_bg'] = self.bg
        game.memory['manage_menu'] = self.menu

        game.state.change('transition_in')
        return 'repeat'

    def begin(self):
        # If come back from info menu
        unit = game.memory.get('current_unit')
        if unit and unit in self.units:
            idx = self.units.index(unit)
            self.menu.move_to(idx)
        game.memory['current_unit'] = None

    def create_quick_disp(self):
        sprite = SPRITES.get('buttons')
        buttons = [sprite.subsurface(0, 66, 14, 13), sprite.subsurface(0, 165, 33, 9)]
        font = FONT['text-white']
        commands = ['Manage', 'Optimize All']
        commands = [text_funcs.translate(c) for c in commands]
        size = (49 + max(font.width(c) for c in commands), 40)
        bg_surf = base_surf.create_base_surf(size[0], size[1], 'menu_bg_brown')
        bg_surf = image_mods.make_translucent(bg_surf, 0.1)
        bg_surf.blit(buttons[0], (20 - buttons[0].get_width()//2, 18 - buttons[0].get_height()))
        bg_surf.blit(buttons[1], (20 - buttons[1].get_width()//2, 32 - buttons[1].get_height()))
        for idx, command in enumerate(commands):
            font.blit(command, bg_surf, (38, idx * 16 + 3))
        return bg_surf

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'LEFT' in directions:
            if self.menu.move_left(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'RIGHT' in directions:
            if self.menu.move_right(first_push):
                SOUNDTHREAD.play_sfx('Select 5')

        if event == 'SELECT':
            unit = self.menu.get_current()
            game.memory['current_unit'] = unit
            if self.name == 'base_manage':
                game.state.change('base_manage_select')
            else:
                game.state.change('prep_manage_select')
            SOUNDTHREAD.play_sfx('Select 1')
        elif event == 'BACK':
            game.state.change('transition_pop')
            SOUNDTHREAD.play_sfx('Select 4')
        elif event == 'INFO':
            SOUNDTHREAD.play_sfx('Select 1')
            game.memory['scroll_units'] = game.get_units_in_party()
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.menu.get_current()
            game.state.change('transition_to')
        elif event == 'START':
            SOUNDTHREAD.play_sfx('Select 1')
            convoy_funcs.optimize_all()

    def update(self):
        game.map_view.update()
        self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.menu.draw(surf)
        menus.draw_unit_items(surf, (6, 72), self.menu.get_current(), include_face=True, shimmer=2)
        surf.blit(self.quick_disp, (WINWIDTH//2 + 10, WINHEIGHT//2 + 9))
        draw_funds(surf)
        return surf

class PrepManageSelectState(State):
    name = 'prep_manage_select'

    def start(self):
        self.fluid = FluidScroll()

        self.bg = game.memory['prep_bg']
        self.menu = game.memory['manage_menu']
        self.unit = game.memory['current_unit']
        self.current_index = self.menu.current_index

        options = ['Trade', 'Restock', 'Give all', 'Optimize', 'Items', 'Market']
        ignore = self.get_ignore()
        self.select_menu = menus.Table(self.unit, options, (3, 2), (120, 80))
        self.select_menu.set_ignore(ignore)

    def get_ignore(self) -> list:
        ignore = [False, True, True, True, True, True]
        if game.game_vars.get('_convoy'):
            ignore = [False, True, True, False, False, True]
            tradeable_items = item_funcs.get_all_tradeable_items(self.unit)
            if tradeable_items:
                ignore[2] = False
            if any(convoy_funcs.can_restock(item) for item in tradeable_items):
                ignore[1] = False
        if self.name == 'base_manage_select':
            if game.game_vars.get('_base_market') and game.market_items:
                ignore[5] = False
        else:
            if game.game_vars.get('_prep_market') and game.market_items:
                ignore[5] = False
        return ignore

    def begin(self):
        ignore = self.get_ignore()
        self.select_menu.set_ignore(ignore)
        self.menu.move_to(self.current_index)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.select_menu.handle_mouse()
        if 'DOWN' in directions:
            if self.select_menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
        elif 'UP' in directions:
            if self.select_menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
        elif 'RIGHT' in directions:
            if self.select_menu.move_right(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
        elif 'LEFT' in directions:
            if self.select_menu.move_left(first_push):
                SOUNDTHREAD.play_sfx('Select 6')

        if event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            choice = self.select_menu.get_current()
            if choice == 'Trade':
                game.state.change('prep_trade_select')
            elif choice == 'Give all':
                tradeable_items = item_funcs.get_all_tradeable_items(self.unit)
                for item in tradeable_items:
                    convoy_funcs.store_item(item, self.unit)
            elif choice == 'Items':
                game.memory['next_state'] = 'prep_items'
                game.state.change('transition_to')
            elif choice == 'Restock':
                game.state.change('prep_restock')
            elif choice == 'Optimize':
                convoy_funcs.optimize(self.unit)
            elif choice == 'Market':
                game.memory['next_state'] = 'prep_market'
                game.state.change('transition_to')

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

    def update(self):
        game.map_view.update()
        self.menu.update()
        self.select_menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.menu.draw(surf)
        menus.draw_unit_items(surf, (6, 72), self.unit, include_face=True, include_top=True, shimmer=2)
        self.select_menu.draw(surf)
        draw_funds(surf)
        return surf

class PrepTradeSelectState(State):
    name = 'prep_trade_select'

    def start(self):
        self.fluid = FluidScroll()

        self.menu = game.memory['manage_menu']
        self.bg = game.memory['prep_bg']
        self.unit = game.memory['current_unit']
        self.menu.set_fake_cursor(self.menu.current_index)

        if game.state.from_transition():
            game.state.change('transition_in')
            return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'LEFT' in directions:
            if self.menu.move_left(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'RIGHT' in directions:
            if self.menu.move_right(first_push):
                SOUNDTHREAD.play_sfx('Select 5')

        if event == 'SELECT':
            unit2 = self.menu.get_current()
            game.memory['unit1'] = self.unit
            game.memory['unit2'] = unit2
            game.memory['next_state'] = 'prep_trade'
            game.state.change('transition_to')

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.change('transition_pop')

        elif event == 'INFO':
            game.memory['scroll_units'] = game.get_units_in_party()
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.menu.get_current()
            game.state.change('transition_to')

    def update(self):
        game.map_view.update()
        self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        menus.draw_unit_items(surf, (6, 72), self.unit, include_face=True, shimmer=2)
        menus.draw_unit_items(surf, (126, 72), self.menu.get_current(), include_face=True, right=False, shimmer=2)
        
        self.menu.draw(surf)

        return surf

    def finish(self):
        self.menu.set_fake_cursor(None)

class PrepItemsState(State):
    name = 'prep_items'

    trade_name_surf = SPRITES.get('trade_name')

    def start(self):
        self.fluid = FluidScroll()

        self.bg = game.memory.get('prep_bg')
        if not self.bg:
            self.bg = background.create_background('rune_background')
        self.unit = game.memory['current_unit']
        include_other_units_items = (self.name != 'supply_items')
        self.menu = menus.Convoy(self.unit, (WINWIDTH - 116, 40), include_other_units_items)
        
        self.state = 'free'
        self.sub_menu = None

        game.state.change('transition_in')
        return 'repeat'

    def begin(self):
        self.menu.update_options()

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        if self.state in ('free', 'trade_convoy', 'trade_inventory'):
            self.menu.handle_mouse()
            if 'DOWN' in directions:
                if self.menu.move_down(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
            elif 'UP' in directions:
                if self.menu.move_up(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
            elif 'LEFT' in directions:
                if self.menu.move_left(first_push):
                    SOUNDTHREAD.play_sfx('TradeRight')
            elif 'RIGHT' in directions:
                if self.menu.move_right(first_push):
                    SOUNDTHREAD.play_sfx('TradeRight')
        elif self.sub_menu:
            self.sub_menu.handle_mouse()
            if 'DOWN' in directions:
                if self.sub_menu.move_down(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
            elif 'UP' in directions:
                if self.sub_menu.move_up(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')

        if event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            if self.state == 'free':
                current = self.menu.get_current()
                context = self.menu.get_context()
                if context == 'inventory':
                    if current:
                        self.state = 'owner_item'
                        options = ['Store', 'Trade']
                        if item_system.can_use(self.unit, current) and \
                                item_funcs.available(self.unit, current) and \
                                item_system.can_use_in_base(self.unit, current):
                            options.append('Use')
                        if convoy_funcs.can_restock(current):
                            options.append('Restock')
                        topleft = (96, self.menu.get_current_index() * 16 + 68 - 8 * len(options))
                        self.sub_menu = menus.Choice(current, options, topleft)
                    else:
                        self.menu.move_to_convoy()
                elif context == 'convoy':
                    if current:
                        if item_system.can_use(self.unit, current) and \
                                item_funcs.available(self.unit, current) and \
                                item_system.can_use_in_base(self.unit, current):
                            self.state = 'convoy_item'
                            topleft = (80, self.menu.get_current_index() * 16)
                            if item_funcs.inventory_full(self.unit, current):
                                options = ['Trade', 'Use']
                            else:
                                options = ['Take', 'Use']
                            self.sub_menu = menus.Choice(current, options, topleft)
                        else:
                            action.do(action.HasTraded(self.unit))
                            if item_funcs.inventory_full(self.unit, current):
                                self.state = 'trade_inventory'
                                self.menu.move_to_inventory()
                            else:
                                if current.owner_nid:
                                    unit = game.get_unit(current.owner_nid)
                                    convoy_funcs.give_item(current, unit, self.unit)
                                else:
                                    convoy_funcs.take_item(current, self.unit)
                                self.menu.update_options()
                    else:
                        pass  # Nothing happens

            elif self.state == 'owner_item':
                current = self.sub_menu.get_current()
                item = self.menu.get_current()
                if current == 'Store':
                    action.do(action.HasTraded(self.unit))
                    convoy_funcs.store_item(item, self.unit)
                    self.menu.update_options()
                    self.menu.move_to_item_type(item)
                    self.state = 'free'
                elif current == 'Trade':
                    self.state = 'trade_convoy'
                    self.menu.move_to_convoy()
                    self.menu.update_options()
                elif current == 'Use':
                    action.do(action.HasTraded(self.unit))
                    interaction.start_combat(self.unit, None, item)
                    self.state = 'free'
                elif current == 'Restock':
                    action.do(action.HasTraded(self.unit))
                    convoy_funcs.restock(item)
                    self.menu.update_options()
                    self.state = 'free'
                self.sub_menu = None

            elif self.state == 'convoy_item':
                current = self.sub_menu.get_current()
                item = self.menu.get_current()
                if current == 'Take':
                    action.do(action.HasTraded(self.unit))
                    convoy_funcs.take_item(item, self.unit)
                    self.state = 'free'
                elif current == 'Trade':
                    self.state = 'trade_inventory'
                    self.menu.move_to_inventory()
                elif current == 'Use':
                    action.do(action.HasTraded(self.unit))
                    interaction.start_combat(self.unit, None, item)
                    self.state = 'free'
                self.sub_menu = None
                self.menu.update_options()

            elif self.state == 'trade_convoy':
                action.do(action.HasTraded(self.unit))
                unit_item = self.menu.get_inventory_current()
                convoy_item = self.menu.get_convoy_current()
                # print(unit_item, convoy_item, self.unit.nid)
                convoy_funcs.trade_items(convoy_item, unit_item, self.unit)
                self.menu.unlock()
                self.menu.update_options()
                self.state = 'free'

            elif self.state == 'trade_inventory':
                action.do(action.HasTraded(self.unit))
                convoy_item = self.menu.get_convoy_current()
                unit_item = self.menu.get_inventory_current()
                convoy_funcs.trade_items(convoy_item, unit_item, self.unit)
                self.menu.unlock()
                self.menu.update_options()
                self.state = 'free'

        elif event == 'BACK':
            if self.menu.info_flag:
                self.menu.toggle_info()
                SOUNDTHREAD.play_sfx('Info Out')
            elif self.state == 'free':
                SOUNDTHREAD.play_sfx('Select 4')
                game.state.change('transition_pop')
            elif self.state == 'owner_item':
                self.sub_menu = None
                self.state = 'free'
            elif self.state == 'convoy_item':
                self.sub_menu = None
                self.state = 'free'
            elif self.state == 'trade_convoy':
                self.menu.move_to_inventory()
                self.menu.unlock()
                self.menu.update_options()
                self.state = 'free'
            elif self.state == 'trade_inventory':
                self.menu.move_to_convoy()
                self.menu.unlock()
                self.menu.update_options()
                self.state = 'free'

        elif event == 'INFO':
            if self.state in ('free', 'trade_convoy', 'trade_inventory'):
                self.menu.toggle_info()
                if self.menu.info_flag:
                    SOUNDTHREAD.play_sfx('Info In')
                else:
                    SOUNDTHREAD.play_sfx('Info Out')

    def update(self):
        self.menu.update()
        if self.sub_menu:
            self.sub_menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.menu.draw(surf)
        if self.sub_menu:
            self.sub_menu.draw(surf)
        if self.menu.info_flag:
            self.menu.draw_info(surf)
        return surf

class PrepRestockState(State):
    name = 'prep_restock'

    def start(self):
        self.fluid = FluidScroll()

        self.bg = game.memory['prep_bg']
        self.unit = game.memory['current_unit']
        self.unit_menu = game.memory['manage_menu']

        topleft = (6, 72)
        self.menu = menus.Inventory(self.unit, self.unit.items, topleft)
        ignore = [not convoy_funcs.can_restock(item) for item in self.unit.items]
        self.menu.set_ignore(ignore)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            self.menu.move_up(first_push)

        if event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            item = self.menu.get_current()
            convoy_funcs.restock(item)
            ignore = [not convoy_funcs.can_restock(item) for item in self.unit.items]
            if all(ignore):
                self.menu.set_ignore(ignore)
                game.state.back()
            else:
                self.menu.set_ignore(ignore)

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'INFO':
            self.menu.toggle_info()
            if self.menu.info_flag:
                SOUNDTHREAD.play_sfx('Info In')
            else:
                SOUNDTHREAD.play_sfx('Info Out')

    def update(self):
        self.menu.update()
        self.unit_menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.unit_menu.draw(surf)
        self.menu.draw(surf)
        return surf

class PrepMarketState(State):
    name = 'prep_market'

    def start(self):
        self.fluid = FluidScroll()

        self.bg = game.memory['prep_bg']
        self.unit = game.memory['current_unit']

        self.sell_menu = menus.Market(self.unit, None, (WINWIDTH - 160, 40), disp_value='sell')
        market_items = item_funcs.create_items(self.unit, game.market_items)
        self.buy_menu = menus.Market(self.unit, market_items, (WINWIDTH - 160, 40), disp_value='buy')
        self.display_menu = self.buy_menu
        self.sell_menu.set_takes_input(False)
        self.buy_menu.set_takes_input(False)

        self.state = 'free'
        options = ["Buy", "Sell"]
        self.choice_menu = menus.Choice(self.unit, options, (20, 24), 'menu_bg_brown')
        self.choice_menu.gem = False
        self.menu = self.choice_menu

        self.money_counter_disp = gui.PopUpDisplay((66, WINHEIGHT - 40))

        game.state.change('transition_in')
        return 'repeat'

    def update_options(self):
        self.buy_menu.update_options()
        self.sell_menu.update_options()

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
            if self.state == 'free':
                current = self.menu.get_current()
                if current == 'Buy':
                    self.display_menu = self.buy_menu
                else:
                    self.display_menu = self.sell_menu
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
            if self.state == 'free':
                current = self.menu.get_current()
                if current == 'Buy':
                    self.display_menu = self.buy_menu
                else:
                    self.display_menu = self.sell_menu
        elif 'LEFT' in directions:
            SOUNDTHREAD.play_sfx('TradeRight')
            self.display_menu.move_left(first_push)
        elif 'RIGHT' in directions:
            SOUNDTHREAD.play_sfx('TradeRight')
            self.display_menu.move_right(first_push)

        if event == 'SELECT':
            if self.state == 'buy':
                item = self.menu.get_current()
                if item:
                    value = item_funcs.buy_price(self.unit, item)
                    if game.get_money() - value >= 0:
                        SOUNDTHREAD.play_sfx('GoldExchange')
                        game.set_money(game.get_money() - value)
                        self.money_counter_disp.start(-value)
                        new_item = item_funcs.create_item(self.unit, item.nid)
                        game.register_item(new_item)
                        if not item_funcs.inventory_full(self.unit, new_item):
                            self.unit.add_item(new_item)
                        else:
                            new_item.change_owner(None)
                            game.party.convoy.append(new_item)
                        self.update_options()
                    else:
                        # You don't have enough money
                        SOUNDTHREAD.play_sfx('Select 4')
                else:
                    # You didn't choose anything to buy
                    SOUNDTHREAD.play_sfx('Select 4')

            elif self.state == 'sell':
                item = self.menu.get_current()
                if item:
                    value = item_funcs.sell_price(self.unit, item)
                    if value:
                        SOUNDTHREAD.play_sfx('GoldExchange')
                        game.set_money(game.get_money() + value)
                        self.money_counter_disp.start(value)
                        if item.owner_nid:
                            owner = game.get_unit(item.owner_nid)
                            owner.remove_item(item)
                        else:
                            game.party.convoy.remove(item)
                        self.update_options()
                    else:
                        # No value, can't be sold
                        SOUNDTHREAD.play_sfx('Select 4')
                else:
                    # You didn't choose anything to sell
                    SOUNDTHREAD.play_sfx('Select 4')

            elif self.state == 'free':
                current = self.menu.get_current()
                if current == 'Buy':
                    self.menu = self.buy_menu
                    self.state = 'buy'
                    self.display_menu = self.buy_menu
                else:
                    self.menu = self.sell_menu
                    self.state = 'sell'
                    self.display_menu = self.sell_menu
                self.menu.set_takes_input(True)

        elif event == 'BACK':
            if self.state == 'buy' or self.state == 'sell':
                if self.menu.info_flag:
                    self.menu.toggle_info()
                    SOUNDTHREAD.play_sfx('Info Out')
                else:
                    SOUNDTHREAD.play_sfx('Select 4')
                    self.state = 'free'
                    self.menu.set_takes_input(False)
                    self.menu = self.choice_menu
            else:
                SOUNDTHREAD.play_sfx('Select 4')
                game.state.change('transition_pop')

        elif event == 'INFO':
            if self.state == 'buy' or self.state == 'sell':
                self.menu.toggle_info()
                if self.menu.info_flag:
                    SOUNDTHREAD.play_sfx('Info In')
                else:
                    SOUNDTHREAD.play_sfx('Info Out')

    def update(self):
        self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.choice_menu.draw(surf)
        self.display_menu.draw(surf)
        # Money
        surf.blit(SPRITES.get('funds_display'), (10, WINHEIGHT - 24))
        money = str(game.get_money())
        FONT['text-blue'].blit_right(money, surf, (61, WINHEIGHT - 20))
        self.money_counter_disp.draw(surf)

        return surf
