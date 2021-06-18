from app import sprites
from app.constants import WINWIDTH, WINHEIGHT
from app.utilities import utils

from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine.fonts import FONT
from app.engine.input_manager import INPUT
from app.engine.state import State

from app.engine.game_state import game
from app.engine import menus, base_surf, background, text_funcs, \
    image_mods, gui, icons, prep, record_book, unit_sprite, action
from app.engine.fluid_scroll import FluidScroll
import app.engine.config as cf


class BaseMainState(State):
    name = 'base_main'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def start(self):
        base_music = game.game_vars.get('_base_music')
        if base_music:
            SOUNDTHREAD.fade_in(base_music)
        game.cursor.hide()
        game.cursor.autocursor()
        game.boundary.hide()
        # build background
        bg_name = game.game_vars.get('_base_bg_name')
        panorama = None
        if bg_name:
            panorama = RESOURCES.panoramas.get(bg_name)
        if panorama:
            panorama = RESOURCES.panoramas.get(bg_name)
            self.bg = background.PanoramaBackground(panorama)
        else:
            panorama = RESOURCES.panoramas.get('default_background')
            self.bg = background.ScrollingBackground(panorama)
            self.bg.scroll_speed = 50
        game.memory['base_bg'] = self.bg

        options = ['Manage', 'Convos', 'Codex', 'Options', 'Save', 'Continue']
        ignore = [False, True, False, False, False, False]
        if game.base_convos:
            ignore[1] = False
        if game.game_vars.get('_supports') and DB.support_constants.value('base_convos'):
            options.insert(2, 'Supports')
            ignore.insert(2, False)
        if DB.constants.value('bexp'):
            options.insert(2, 'Bonus EXP')
            ignore.insert(2, False)
        if game.game_vars.get('_base_market'):
            options.insert(1, 'Market')
            if game.market_items:
                ignore.insert(1, False)
            else:
                ignore.insert(1, True)
        if cf.SETTINGS['debug']:
            options.insert(0, 'Debug')
            ignore.insert(0, False)

        topleft = 4, WINHEIGHT // 2 - (len(options) * 16 + 8) // 2
        self.menu = menus.Choice(None, options, topleft=topleft)
        self.menu.set_ignore(ignore)

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
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
            elif selection == 'Manage':
                game.memory['next_state'] = 'base_manage'
                game.state.change('transition_to')
            elif selection == 'Market':
                game.memory['next_state'] = 'base_market_select'
                game.state.change('transition_to')
            elif selection == 'Convos':
                game.memory['option_owner'] = selection
                game.memory['option_menu'] = self.menu
                game.state.change('base_convos_child')
            elif selection == 'Supports':
                game.memory['next_state'] = 'base_supports'
                game.state.change('transition_to')
            elif selection == 'Codex':
                game.memory['option_owner'] = selection
                game.memory['option_menu'] = self.menu
                game.state.change('base_codex_child')
            elif selection == 'Options':
                game.memory['next_state'] = 'settings_menu'
                game.state.change('transition_to')
            elif selection == 'Save':
                game.memory['save_kind'] = 'base'
                game.memory['next_state'] = 'in_chapter_save'
                game.state.change('transition_to')
            elif selection == 'Continue':
                game.state.change('transition_pop')
            elif selection == 'Bonus EXP':
                game.memory['next_state'] = 'base_bexp_select'
                game.state.change('transition_to')

    def update(self):
        super().update()
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        surf = super().draw(surf)
        if self.bg:
            self.bg.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        return surf


class BaseMarketSelectState(prep.PrepManageState):
    name = 'base_market_select'

    def create_quick_disp(self):
        sprite = SPRITES.get('buttons')
        buttons = [sprite.subsurface(0, 66, 14, 13)]
        font = FONT['text-white']
        commands = ['Market']
        commands = [text_funcs.translate(c) for c in commands]
        size = (49 + max(font.width(c) for c in commands), 24)
        bg_surf = base_surf.create_base_surf(size[0], size[1], 'menu_bg_brown')
        bg_surf = image_mods.make_translucent(bg_surf, 0.1)
        bg_surf.blit(buttons[0], (12 - buttons[0].get_width() // 2, 18 - buttons[0].get_height()))
        for idx, command in enumerate(commands):
            font.blit(command, bg_surf, (30, idx * 16 + 3))
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
            game.memory['next_state'] = 'prep_market'
            game.state.change('transition_to')
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


class BaseConvosChildState(State):
    name = 'base_convos_child'
    transparent = True

    def start(self):
        self.fluid = FluidScroll()
        self.options = [event_nid for event_nid in game.base_convos.keys()]
        ignore = [game.base_convos[event_nid] for event_nid in self.options]

        selection = game.memory['option_owner']
        topleft = game.memory['option_menu']

        self.menu = menus.Choice(selection, self.options, topleft)
        # color = ['text-grey' if i else 'text-white' for i in ignore]
        # self.menu.set_color(color)
        self.menu.set_ignore(ignore)

    def begin(self):
        ignore = [game.base_convos[event_nid] for event_nid in self.options]
        # color = ['text-grey' if i else 'text-white' for i in ignore]
        # self.menu.set_color(color)
        self.menu.set_ignore(ignore)
        base_music = game.game_vars.get('_base_music')
        if base_music:
            SOUNDTHREAD.fade_in(base_music)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'SELECT':
            selection = self.menu.get_current()
            if not game.base_convos[selection]:
                SOUNDTHREAD.play_sfx('Select 1')
                # Auto-ignore
                game.base_convos[selection] = True
                game.events.trigger('on_base_convo', selection)

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if self.menu:
            self.menu.draw(surf)
        return surf


class SupportDisplay():
    support_word_sprite = SPRITES.get('support_words')

    def __init__(self):
        self.unit_nid = None
        self.topleft = (84, 4)
        self.width = WINWIDTH - 100
        self.bg_surf = base_surf.create_base_surf(self.width, WINHEIGHT - 8)
        shimmer = SPRITES.get('menu_shimmer2')
        self.bg_surf.blit(shimmer, (
            self.bg_surf.get_width() - shimmer.get_width() - 1, self.bg_surf.get_height() - shimmer.get_height() - 5))
        self.bg_surf = image_mods.make_translucent(self.bg_surf, .1)

        self.cursor = menus.Cursor()
        self.draw_cursor = False

        self.char_idx = 0
        self.rank_idx = 0

    def update_entry(self, unit_nid):
        if self.unit_nid and unit_nid == self.unit_nid:
            return  # No need to update
        self.unit_nid = unit_nid
        self.options = self.get_other_unit_nids()
        self.char_idx = 0
        self.rank_idx = 0

    def get_other_unit_nids(self) -> list:
        other_unit_nids = []
        for prefab in DB.support_pairs:
            if prefab.unit1 == self.unit_nid:
                other_unit_nid = prefab.unit2
            elif prefab.unit2 == self.unit_nid:
                other_unit_nid = prefab.unit1
            else:
                continue
            other_unit_nids.append(other_unit_nid)
        other_unit_nids = sorted(other_unit_nids)
        return other_unit_nids

    def click_selection(self) -> bool:
        other_unit_nids = self.options
        other_unit_nid = other_unit_nids[self.char_idx]
        prefabs = DB.support_pairs.get_pairs(self.unit_nid, other_unit_nid)
        if prefabs:
            prefab = prefabs[0]
            if prefab.nid not in game.supports.support_pairs:
                game.supports.create_pair(prefab.nid)
            pair = game.supports.support_pairs[prefab.nid]
            bonus = prefab.requirements[self.rank_idx]
            rank = bonus.support_rank
            if rank in pair.unlocked_ranks:
                game.events.trigger('on_support', game.get_unit(self.unit_nid), game.get_unit(other_unit_nid), rank)
                return True
            elif pair.can_support() and rank in pair.locked_ranks:
                game.events.trigger('on_support', game.get_unit(self.unit_nid), game.get_unit(other_unit_nid), rank)
                action.do(action.UnlockSupportRank(pair.nid, rank))
                return True
        return False

    def get_num_ranks(self, other_unit_nid) -> int:
        prefabs = DB.support_pairs.get_pairs(self.unit_nid, other_unit_nid)
        if prefabs:
            prefab = prefabs[0]
            return len(prefab.requirements)

    def move_down(self, first_push=True) -> bool:
        self.char_idx += 1
        if self.char_idx > len(self.options) - 1:
            if first_push:
                self.char_idx = 0
            else:
                self.char_idx -= 1
                return False
        else:
            self.cursor.y_offset_down()
        # check limit for new row
        limit = max(0, self.get_num_ranks(self.options[self.char_idx]) - 1)
        self.rank_idx = utils.clamp(self.rank_idx, 0, limit)
        return True

    def move_up(self, first_push=True) -> bool:
        self.char_idx -= 1
        if self.char_idx < 0:
            if first_push:
                self.char_idx = len(self.options) - 1
            else:
                self.char_idx += 1
                return False
        else:
            self.cursor.y_offset_up()
        # check limit for new row
        limit = max(0, self.get_num_ranks(self.options[self.char_idx]) - 1)
        self.rank_idx = utils.clamp(self.rank_idx, 0, limit)
        return True

    def move_left(self, first_push=True) -> bool:
        self.rank_idx -= 1
        if self.rank_idx < 0 and first_push:
            self.rank_idx = 0
            return False
        return True

    def move_right(self, first_push=True) -> bool:
        self.rank_idx += 1
        num_ranks = self.get_num_ranks(self.options[self.char_idx])
        if self.rank_idx > num_ranks - 1:
            if first_push:
                self.rank_idx = 0
            else:
                self.rank_idx -= 1
                return False
        return True

    def draw(self, surf):
        if self.unit_nid:
            bg_surf = self.bg_surf.copy()
            other_unit_nids = self.options

            map_sprites = []
            for idx, other_unit_nid in enumerate(other_unit_nids):
                if game.get_unit(other_unit_nid):
                    other_unit = game.get_unit(other_unit_nid)
                    if other_unit.dead:
                        map_sprite = other_unit.sprite.create_image('gray')
                    elif self.char_idx == idx:
                        map_sprite = other_unit.sprite.create_image('active')
                    else:
                        map_sprite = other_unit.sprite.create_image('passive')
                    image = map_sprite
                    name = other_unit.name
                    affinity = DB.affinities.get(other_unit.affinity)
                elif DB.units.get(other_unit_nid):  # Not loaded into game yet
                    other_unit_prefab = DB.units.get(other_unit_nid)
                    map_sprite = unit_sprite.load_map_sprite(other_unit_prefab, 'black')
                    image = map_sprite.passive[game.map_view.passive_sprite_counter.count].copy()
                    # name = other_unit_prefab.name
                    name = '---'
                    affinity = DB.affinities.get(other_unit_prefab.affinity)
                else:
                    image = None
                    name = '---'
                    affinity = None

                map_sprites.append(image)
                # Blit name
                FONT['text-white'].blit(name, bg_surf, (25, idx * 16 + 20))
                # Blit affinity
                if affinity:
                    icons.draw_item(bg_surf, affinity, (72, idx * 16 + 19))
                # Blit support levels
                prefabs = DB.support_pairs.get_pairs(self.unit_nid, other_unit_nid)
                if prefabs:
                    prefab = prefabs[0]
                    if prefab.nid not in game.supports.support_pairs:
                        game.supports.create_pair(prefab.nid)
                    pair = game.supports.support_pairs[prefab.nid]
                    for ridx, bonus in enumerate(prefab.requirements):
                        rank = bonus.support_rank
                        if rank in pair.locked_ranks:
                            fnt = FONT['text-green']
                        elif rank in pair.unlocked_ranks:
                            fnt = FONT['text-white']
                        else:
                            fnt = FONT['text-grey']
                        fnt.blit(rank, bg_surf, (90 + ridx * 10, idx * 16 + 20))

            for idx, map_sprite in enumerate(map_sprites):
                if map_sprite:
                    bg_surf.blit(map_sprite, (-20, idx * 16 - 4))

            surf.blit(bg_surf, (100, 4))

            surf.blit(self.support_word_sprite, (120, 11))

            # Cursor
            if self.draw_cursor:
                left = self.rank_idx * 10 + 82 + 100
                top = self.char_idx * 16 + 12 + 12
                self.cursor.update()
                self.cursor.draw(surf, left, top)

        return surf


class BaseSupportsState(State):
    name = 'base_supports'

    def start(self):
        self.fluid = FluidScroll()
        self.bg = game.memory['base_bg']

        player_units = game.get_units_in_party()
        # Filter only to units with supports
        self.units = [unit for unit in player_units if
                      any(prefab.unit1 == unit.nid or prefab.unit2 == unit.nid for prefab in DB.support_pairs)]

        self.menu = menus.Table(None, self.units, (9, 1), (4, 4))
        self.menu.set_mode('unit')

        self.display = SupportDisplay()
        self.display.update_entry(self.menu.get_current().nid)

        self.in_display = False

        game.state.change('transition_in')
        return 'repeat'

    def begin(self):
        base_music = game.game_vars.get('_base_music')
        if base_music:
            SOUNDTHREAD.fade_in(base_music)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if not self.display.unit_nid or self.display.unit_nid != self.menu.get_current().nid:
            self.display.update_entry(self.menu.get_current().nid)

        if 'DOWN' in directions:
            if self.in_display:
                if self.display.move_down(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
            else:
                if self.menu.move_down(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
                self.display.update_entry(self.menu.get_current().nid)
        elif 'UP' in directions:
            if self.in_display:
                if self.display.move_up(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
            else:
                if self.menu.move_up(first_push):
                    SOUNDTHREAD.play_sfx('Select 6')
                self.display.update_entry(self.menu.get_current().nid)
        elif 'RIGHT' in directions:
            if self.in_display:
                if self.display.move_right(first_push):
                    SOUNDTHREAD.play_sfx('TradeRight')
                else:
                    SOUNDTHREAD.play_sfx('Error')
            else:
                SOUNDTHREAD.play_sfx('TradeRight')
                self.in_display = True
                self.display.draw_cursor = True
        elif 'LEFT' in directions:
            if self.in_display:
                if self.display.move_left(first_push):
                    SOUNDTHREAD.play_sfx('TradeRight')
                else:
                    self.in_display = False
                    self.display.draw_cursor = False
                    SOUNDTHREAD.play_sfx('Select 6')

        if event == 'BACK':
            if self.in_display:
                SOUNDTHREAD.play_sfx('TradeRight')
                self.in_display = False
                self.display.draw_cursor = False
            else:
                SOUNDTHREAD.play_sfx('Select 4')
                game.state.change('transition_pop')

        elif event == 'SELECT':
            if self.in_display:
                success = self.display.click_selection()
                if success:
                    pass
                else:
                    SOUNDTHREAD.play_sfx('Error')
            else:
                if self.display.move_right():
                    SOUNDTHREAD.play_sfx('TradeRight')
                else:
                    SOUNDTHREAD.play_sfx('Error')

        elif event == 'INFO':
            game.memory['scroll_units'] = self.units
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.menu.get_current()
            game.state.change('transition_to')

    def update(self):
        game.map_view.update()
        if self.menu and not self.display.draw_cursor:
            self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        if self.display:
            self.display.draw(surf)
        return surf


class BaseCodexChildState(State):
    name = 'base_codex_child'
    transparent = True

    def start(self):
        self.fluid = FluidScroll()

        options = []
        unlocked_lore = [lore for lore in DB.lore if lore.nid in game.unlocked_lore]
        if unlocked_lore:
            options.append('Library')
        if game.game_vars['_world_map_in_base']:
            options.append('Map')
        options.append('Records')
        # TODO Achievements?
        # TODO Tactics?
        unlocked_guide = [lore for lore in unlocked_lore if lore.category == 'Guide']
        if unlocked_guide:
            options.append('Guide')

        selection = game.memory['option_owner']
        topleft = game.memory['option_menu']

        self.menu = menus.Choice(selection, options, topleft)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'SELECT':
            selection = self.menu.get_current()
            SOUNDTHREAD.play_sfx('Select 1')

            if selection == 'Library':
                game.memory['next_state'] = 'base_library'
                game.state.change('transition_to')
            elif selection == 'Map':
                game.memory['next_state'] = 'base_world_map'
                game.state.change('transition_to')
            elif selection == 'Records':
                game.memory['next_state'] = 'base_records'
                game.state.change('transition_to')
            elif selection == 'Guide':
                game.memory['next_state'] = 'base_guide'
                game.state.change('transition_to')

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if self.menu:
            self.menu.draw(surf)
        return surf


class LoreDisplay():
    def __init__(self):
        self.lore = None
        self.topleft = (84, 4)
        self.width = WINWIDTH - 84
        self.bg_surf = base_surf.create_base_surf(self.width, WINHEIGHT - 8, 'menu_bg_brown')
        shimmer = SPRITES.get('menu_shimmer3')
        self.bg_surf.blit(shimmer, (
            self.bg_surf.get_width() - shimmer.get_width() - 1, self.bg_surf.get_height() - shimmer.get_height() - 5))
        self.bg_surf = image_mods.make_translucent(self.bg_surf, .1)

        self.left_arrow = gui.ScrollArrow('left', (self.topleft[0] + 4, 8))
        self.right_arrow = gui.ScrollArrow('right', (self.topleft[0] + self.width - 11, 8), 0.5)

        self.dialogs = []

    def update_entry(self, lore_nid):
        from app.engine import dialog

        if self.lore and lore_nid == self.lore.nid:
            return  # No need to update

        class LoreDialog(dialog.Dialog):
            num_lines = 8
            draw_cursor_flag = False

        self.lore = DB.lore.get(lore_nid)
        text = self.lore.text.split('\n')
        self.page_num = 0
        self.dialogs.clear()
        for idx, line in enumerate(text):
            dialog = LoreDialog(text[idx])
            dialog.position = self.topleft[0], self.topleft[1] + 12
            dialog.text_width = WINWIDTH - 100
            dialog.font = FONT['text-white']
            dialog.font_type = 'text'
            dialog.font_color = 'white'
            self.dialogs.append(dialog)
        self.num_pages = len(text)

    def page_right(self, first_push=False) -> bool:
        if self.page_num < self.num_pages - 1:
            self.page_num += 1
            self.right_arrow.pulse()
            return True
        elif first_push:
            self.page_num = (self.page_num + 1) % self.num_pages
            self.right_arrow.pulse()
            return True
        return False

    def page_left(self, first_push=False) -> bool:
        if self.page_num > 0:
            self.page_num -= 1
            self.left_arrow.pulse()
            return True
        elif first_push:
            self.page_num = (self.page_num - 1) % self.num_pages
            self.left_arrow.pulse()
            return True
        return False

    def draw(self, surf):
        if self.lore:
            image = self.bg_surf.copy()
            if game.get_unit(self.lore.nid):
                unit = game.get_unit(self.lore.nid)
                icons.draw_portrait(image, unit, (self.width - 96, WINHEIGHT - 12 - 80))
            elif self.lore.nid in DB.units.keys():
                portrait = icons.get_portrait_from_nid(DB.units.get(self.lore.nid).portrait_nid)
                image.blit(portrait, (self.width - 96, WINHEIGHT - 12 - 80))

            FONT['text-blue'].blit_center(self.lore.title, image, (self.width // 2, 4))

            if self.num_pages > 1:
                text = '%d / %d' % (self.page_num + 1, self.num_pages)
                FONT['text-yellow'].blit_right(text, image, (self.width - 8, WINHEIGHT - 12 - 16))

            surf.blit(image, self.topleft)

            if self.dialogs and self.page_num < len(self.dialogs):
                self.dialogs[self.page_num].update()
                self.dialogs[self.page_num].draw(surf)

            if self.num_pages > 1:
                self.left_arrow.draw(surf)
                self.right_arrow.draw(surf)

        return surf


class BaseLibraryState(State):
    name = 'base_library'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def _build_menu(self, unlocked_lore, ignore=None):
        topleft = 4, 4
        self.options = unlocked_lore
        self.menu = menus.Choice(None, self.options, topleft=topleft, background='menu_bg_brown')
        self.menu.shimmer = 3
        self.menu.gem = 'brown'
        self.menu.set_limit(9)
        self.menu.set_hard_limit(True)
        if ignore:
            self.menu.set_ignore(ignore)

    def start(self):
        self.bg = game.memory['base_bg']

        unlocked_lore = [lore for lore in DB.lore if lore.nid in game.unlocked_lore and lore.category != 'Guide']
        sorted_lore = sorted(unlocked_lore, key=lambda x: x.category)
        self.categories = []
        options = []
        ignore = []
        for lore in sorted_lore:
            if lore.category not in self.categories:
                self.categories.append(lore.category)
                options.append(lore)
                ignore.append(True)
            options.append(lore)
            ignore.append(False)

        self._build_menu(options, ignore)

        self.display = LoreDisplay()
        self.display.update_entry(self.menu.get_current().nid)

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if not self.display.lore or self.display.lore.nid != self.menu.get_current().nid:
            self.display.update_entry(self.menu.get_current().nid)

        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
            self.display.update_entry(self.menu.get_current().nid)
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
            self.display.update_entry(self.menu.get_current().nid)
        elif 'RIGHT' in directions:
            if self.display.page_right():
                SOUNDTHREAD.play_sfx('Status_Page_Change')
        elif 'LEFT' in directions:
            if self.display.page_left():
                SOUNDTHREAD.play_sfx('Status_Page_Change')

        if event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.change('transition_pop')

        elif event == 'SELECT':
            if self.display.page_right(True):
                SOUNDTHREAD.play_sfx('Status_Page_Change')

        elif event == 'AUX':
            SOUNDTHREAD.play_sfx('Info')
            lore = self.menu.get_current()
            # Go to previous category
            cidx = self.categories.index(lore.category)
            new_category = self.categories[(cidx + 1) % len(self.categories)]
            idx = self.options.index(new_category)
            option = self.options[idx + 1]

            self.display.update_entry(option.nid)

        elif event == 'INFO':
            SOUNDTHREAD.play_sfx('Info')
            lore = self.menu.get_current()
            # Go to next category
            cidx = self.categories.index(lore.category)
            new_category = self.categories[(cidx - 1) % len(self.categories)]
            idx = self.options.index(new_category)
            option = self.options[idx + 1]

            self.display.update_entry(option.nid)

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        if self.display:
            self.display.draw(surf)
        return surf


class BaseGuideState(BaseLibraryState):
    name = 'base_guide'

    def start(self):
        self.bg = game.memory.get('base_bg', None)
        if not self.bg:
            panorama = RESOURCES.panoramas.get('default_background')
            self.bg = background.ScrollingBackground(panorama)
            self.bg.scroll_speed = 50

        unlocked_lore = [lore for lore in DB.lore if lore.nid in game.unlocked_lore and lore.category == 'Guide']
        self.categories = ["Guide"]

        self._build_menu(unlocked_lore)

        self.display = LoreDisplay()
        self.display.update_entry(self.menu.get_current().nid)

        game.state.change('transition_in')
        return 'repeat'


class BaseRecordsState(State):
    name = 'base_records'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def start(self):
        self.mouse_indicator = gui.MouseIndicator()
        self.bg = game.memory.get('base_bg')
        if not self.bg:
            panorama = RESOURCES.panoramas.get('default_background')
            self.bg = background.ScrollingBackground(panorama)
            self.bg.scroll_speed = 50

        self.record_menu = record_book.RecordsDisplay()
        self.chapter_menus = [record_book.ChapterStats(option.get()[0]) for option in self.record_menu.options if
                              not option.ignore]
        self.mvp = record_book.MVPDisplay()
        self.unit_menus = [record_book.UnitStats(option.get()[0]) for option in self.mvp.options if not option.ignore]

        self.state = 'records'
        self.current_menu = self.record_menu
        self.prev_menu = None

        self.current_offset_x = 0
        self.current_offset_y = 0
        self.prev_offset_x = 0
        self.prev_offset_y = 0

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.current_menu.handle_mouse()

        if 'DOWN' in directions:
            if self.current_menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
        elif 'UP' in directions:
            if self.current_menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')

        if event == 'LEFT':
            self.move_left()

        elif event == 'RIGHT':
            self.move_right()

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            if self.state in ('records', 'mvp'):
                game.state.change('transition_pop')
            else:
                self.prev_menu = self.current_menu
                self.current_offset_y = -WINHEIGHT
                self.prev_offset_y = 1

            if self.state == 'unit':
                self.state = 'mvp'
                self.current_menu = self.mvp
            elif self.state == 'chapter':
                self.state = 'records'
                self.current_menu = self.record_menu

        elif event == 'SELECT':
            if self.check_mouse_position():
                pass
            else:
                SOUNDTHREAD.play_sfx('Select 1')
                if self.state in ('records', 'mvp'):
                    self.prev_menu = self.current_menu
                    self.current_offset_y = WINHEIGHT
                    self.prev_offset_y = -1

                if self.state == 'records':
                    self.state = 'chapter'
                    self.current_menu = self.chapter_menus[self.current_menu.get_current_index()]
                elif self.state == 'mvp':
                    self.state = 'unit'
                    self.current_menu = self.unit_menus[self.current_menu.get_current_index()]

    def check_mouse_position(self):
        mouse_position = INPUT.get_mouse_position()
        if mouse_position:
            mouse_x, mouse_y = mouse_position
            if mouse_x <= 16:
                self.move_left()
                return True
            elif mouse_x >= WINWIDTH - 16:
                self.move_right()
                return True
            elif mouse_y <= 16:
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_up()
                return True
            elif mouse_y >= WINHEIGHT - 16:
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_down()
                return True
        return False

    def move_left(self):
        SOUNDTHREAD.play_sfx('Status_Page_Change')
        self.prev_menu = self.current_menu
        self.current_offset_x = -WINWIDTH
        self.prev_offset_x = 1
        if self.state == 'records':
            self.state = 'mvp'
            self.current_menu = self.mvp
        elif self.state == 'mvp':
            self.state = 'records'
            self.current_menu = self.record_menu
        elif self.state == 'chapter':
            self.record_menu.move_up(True)
            self.current_menu = self.chapter_menus[self.record_menu.get_current_index()]
        elif self.state == 'unit':
            self.mvp.move_up(True)
            self.current_menu = self.unit_menus[self.mvp.get_current_index()]

    def move_right(self):
        SOUNDTHREAD.play_sfx('Status_Page_Change')
        self.prev_menu = self.current_menu
        self.current_offset_x = WINWIDTH
        self.prev_offset_x = -1
        if self.state == 'records':
            self.state = 'mvp'
            self.current_menu = self.mvp
        elif self.state == 'mvp':
            self.state = 'records'
            self.current_menu = self.record_menu
        elif self.state == 'chapter':
            self.record_menu.move_down(True)
            self.current_menu = self.chapter_menus[self.record_menu.get_current_index()]
        elif self.state == 'unit':
            self.mvp.move_down(True)
            self.current_menu = self.unit_menus[self.mvp.get_current_index()]

    def update(self):
        if self.current_menu:
            self.current_menu.update()

        # X axis
        if self.current_offset_x > 0:
            self.current_offset_x -= 16
        elif self.current_offset_x < 0:
            self.current_offset_x += 16
        if self.prev_menu:
            if self.prev_offset_x > 0:
                self.prev_offset_x += 16
            elif self.prev_offset_x < 0:
                self.prev_offset_x -= 16
            if self.prev_offset_x > WINWIDTH or self.prev_offset_x < -WINWIDTH:
                self.prev_offset_x = 0
                self.prev_menu = None

        # Y axis
        if self.current_offset_y > 0:
            self.current_offset_y -= 16
        elif self.current_offset_y < 0:
            self.current_offset_y += 16
        if self.prev_menu:
            if self.prev_offset_y > 0:
                self.prev_offset_y += 16
            elif self.prev_offset_y < 0:
                self.prev_offset_y -= 16
            if self.prev_offset_y > WINHEIGHT or self.prev_offset_y < -WINHEIGHT:
                self.prev_offset_y = 0
                self.prev_menu = None

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.current_menu:
            self.current_menu.draw(surf, offset=(self.current_offset_x, self.current_offset_y))
        if self.prev_menu:
            self.prev_menu.draw(surf, offset=(self.prev_offset_x, self.prev_offset_y))
        if self.mouse_indicator:
            self.mouse_indicator.draw(surf)
        return surf


class BaseBEXPSelectState(prep.PrepManageState):
    name = 'base_bexp_select'

    def begin(self):
        super().begin()
        ignore = []
        for unit in self.units:
            auto_promote = (DB.constants.value('auto_promote') or 'AutoPromote' in unit.tags) and \
                DB.classes.get(unit.klass).turns_into and 'NoAutoPromote' not in unit.tags
            ignore.append(unit.level >= DB.classes.get(unit.klass).max_level and not auto_promote)
        self.menu.set_ignore(ignore)

    def create_quick_disp(self):
        sprite = SPRITES.get('buttons')
        buttons = [sprite.subsurface(0, 66, 14, 13)]
        font = FONT['text-white']
        commands = ['Manage']
        commands = [text_funcs.translate(c) for c in commands]
        size = (49 + max(font.width(c) for c in commands), 24)
        bg_surf = base_surf.create_base_surf(size[0], size[1], 'menu_bg_brown')
        bg_surf = image_mods.make_translucent(bg_surf, 0.1)
        bg_surf.blit(buttons[0], (12 - buttons[0].get_width() // 2, 18 - buttons[0].get_height()))
        for idx, command in enumerate(commands):
            font.blit(command, bg_surf, (30, idx * 16 + 3))
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
            game.memory['next_state'] = 'base_bexp_allocate'
            game.state.change('transition_to')
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


class BaseBEXPAllocateState(State):
    show_map = False
    name = 'base_bexp_allocate'

    def start(self):
        self.fluid = FluidScroll()
        self.unit = game.memory['current_unit']
        # These 2 need removal
        options = ['Right: +1 EXP', 'Left: -1 EXP', 'Up: To Next Level',
                   'Down: Reset']
        self.menu = menus.Choice(self.unit, options, (128, 80))
        self.menu.draw_cursor = False

        # This draws the controls
        self.buttons = [SPRITES.get('buttons').subsurface(1, 19, 13, 12),
                        SPRITES.get('buttons').subsurface(1, 4, 13, 12),
                        SPRITES.get('buttons').subsurface(1, 50, 12, 13),
                        SPRITES.get('buttons').subsurface(1, 34, 12, 13)]
        self.font = FONT['text-white']
        self.commands = ['+1 EXP', '-1 EXP', 'To Next Level', 'Reset']
        pos = (
            33 + self.font.size(self.commands[2])[0] + 4, self.font.size(self.commands[2])[1] * len(self.commands) + 8)
        self.quick_sort_disp = base_surf.create_base_surf(pos[0], pos[1], 'menu_bg_brown')
        self.quick_sort_disp = image_mods.make_translucent(self.quick_sort_disp, 10)
        for idx, button in enumerate(self.buttons):
            self.quick_sort_disp.blit(button, (
                10 - button.get_width() // 2, idx * self.font.height + 8 - button.get_height() // 2 + 4))
        for idx, command in enumerate(self.commands):
            self.font.blit(command, self.quick_sort_disp, (25, idx * self.font.height + 4))

        self.bg = game.memory['base_bg']

        # Sets up variables, needed for display and calculations
        self.current_bexp = int(game.get_bexp())
        self.new_bexp = int(game.get_bexp())
        self.current_exp = int(self.unit.exp)
        self.new_exp = int(self.unit.exp)
        # This is Radiant Dawn's formula, can be adjusted per user's needs.
        # Note that this does take tier zero into account. A level 5 fighter who promoted from Journeyman would be treated as level 15.
        self.determine_needed_bexp(int(self.unit.get_internal_level()))

    def determine_needed_bexp(self, level):
        self.bexp_needed = 50 * level + 50
        self.exp_increment = int(self.bexp_needed / 100)

    # Player input is handled here
    def take_input(self, event):
        first_push = self.fluid.update(game)
        directions = self.fluid.get_directions()

        # Down resets values to their starting values
        if 'DOWN' in directions:
            if self.new_exp > self.current_exp:
                SOUNDTHREAD.play_sfx('Select 5')
                self.new_bexp = self.current_bexp
                self.new_exp = self.current_exp
            elif first_push:
                SOUNDTHREAD.play_sfx('Error')
        # Right increments by 1 EXP
        elif 'RIGHT' in directions:
            if self.new_exp < 100 and self.new_bexp > 0 and self.new_bexp >= self.exp_increment:
                SOUNDTHREAD.play_sfx('Select 5')
                self.new_exp += 1
                self.new_bexp -= self.exp_increment
            elif first_push:
                SOUNDTHREAD.play_sfx('Error')
        # Left decrements by 1 EXP
        elif 'LEFT' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            if self.new_exp > self.current_exp:
                self.new_exp -= 1
                self.new_bexp += self.exp_increment
        # Up attempts to get us to 100 EXP, or the highest amount possible if 100 cannot be reached.
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 5')
            if self.new_exp < 100 and self.new_bexp > self.exp_increment:
                amount_needed = (100 - self.new_exp) * self.exp_increment
                if self.new_bexp >= amount_needed:
                    self.new_bexp -= amount_needed
                    self.new_exp = 100
                else:
                    self.new_exp += int(self.new_bexp / self.exp_increment)
                    self.new_bexp = self.new_bexp % self.exp_increment

        # Allocates EXP, performs level up, and sets values as needed
        if event == 'SELECT':
            if self.new_exp > self.current_exp:
                SOUNDTHREAD.play_sfx('Select 1')
                exp_to_gain = self.new_exp - self.current_exp
                if DB.constants.value('rd_bexp_lvl'):
                    game.memory['exp_method'] = 'BEXP'
                game.exp_instance.append((self.unit, exp_to_gain, None, 'init'))
                game.state.change('exp')
                if self.new_exp == 100:
                    self.current_exp = 0
                    self.new_exp = 0
                    self.determine_needed_bexp(int(self.unit.get_internal_level() + 1))
                else:
                    self.current_exp = self.new_exp
                self.current_bexp = self.new_bexp
                game.set_bexp(self.current_bexp)

            # Resets values to starting values and goes back to previous menu
        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            self.new_bexp = self.current_exp
            self.new_bexp = self.current_bexp
            game.state.change('transition_pop')

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.menu.draw(surf)
        menus.draw_unit_bexp(surf, (6, 72), self.unit, self.new_exp, self.new_bexp, self.current_bexp,
                             include_face=True, include_top=True, shimmer=2)
        return surf
