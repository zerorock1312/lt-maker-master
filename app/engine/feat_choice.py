from app.constants import WINWIDTH, WINHEIGHT
from app.data.database import DB

from app.engine.sound import SOUNDTHREAD
from app.engine.fonts import FONT
from app.engine.state import MapState

from app.engine import engine, text_funcs, menus, action, \
    menu_options, icons, help_menu, banner, base_surf
from app.engine.game_state import game

class SkillOption(menu_options.BasicOption):
    """
    Skill Prefabs, not Skill Objects
    """
    def __init__(self, idx, skill):
        self.idx = idx
        self.skill = skill
        self.help_box = None
        self.color = 'text-white'
        self.ignore = False

    def get(self):
        return self.skill

    def set_text(self, text):
        pass

    def set_skill(self, skill):
        self.skill = skill

    def width(self):
        return FONT[self.color].width(self.skill.name) + 24

    def height(self):
        return 16

    def get_color(self):
        main_font = 'text-grey'
        if self.ignore:
            pass
        elif self.color:
            main_font = self.color
        return main_font

    def get_help_box(self):
        return help_menu.HelpDialog(self.skill.desc, name=self.skill.name)

    def draw(self, surf, x, y):
        icon = icons.get_icon(self.skill)
        if icon:
            surf.blit(icon, (x + 2, y))
        main_font = self.get_color()
        FONT[main_font].blit(self.skill.name, surf, (x + 20, y))

class FeatChoice(menus.Table):
    def create_options(self, options, info_desc=None):
        self.options.clear()
        for idx, option in enumerate(options):
            option = SkillOption(idx, option)
            self.options.append(option)

class FeatChoiceState(MapState):
    name = 'feat_choice'
    transparent = True

    def start(self):
        self.unit = game.memory['current_unit']
        feats = DB.skills.get_feats()

        current_skills = [skill.nid for skill in self.unit.skills]
        ignore = [True if feat.nid in current_skills else False for feat in feats]
        self.menu = FeatChoice(self.unit, feats, (5, 2), 'center')
        self.menu.shimmer = 2
        self.menu.topleft = (self.menu.get_topleft()[0], WINHEIGHT - self.menu.get_menu_height() - 4) 
        self.menu.set_ignore(ignore)

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
        if 'RIGHT' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_right(first_push)
        elif 'LEFT' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_left(first_push)

        if event == 'BACK':
            if self.menu.info_flag:
                SOUNDTHREAD.play_sfx('Info Out')
            else:
                SOUNDTHREAD.play_sfx('Info In')
            self.menu.toggle_info()

        elif event == 'INFO':
            SOUNDTHREAD.play_sfx('Select 2')
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.unit
            game.state.change('transition_to')

        elif event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            selection = self.menu.get_current()
            game.state.back()
            act = action.AddSkill(self.unit, selection.nid)
            action.do(act)
            if act.skill_obj:
                game.alerts.append(banner.GiveSkill(self.unit, act.skill_obj))
                game.state.change('alert')

    def update(self):
        self.menu.update()

    def draw_face(self, surf):
        im = icons.get_portrait(self.unit)
        if im:
            x_pos = (im.get_width() - 80)//2
            portrait_surf = engine.subsurface(im, (x_pos, 0, 80, 72))

            topleft = self.menu.get_topleft()
            surf.blit(portrait_surf, (WINWIDTH//2 - 80//2, topleft[1] - 72))

    def draw_label(self, surf):
        label = text_funcs.translate('Feat Choice')
        label_width = FONT['text-white'].width(label) + 16
        bg_surf = base_surf.create_base_surf(label_width, 24)
        FONT['text-white'].blit_center(label, bg_surf, (bg_surf.get_width()//2, 4))
        surf.blit(bg_surf, (0, 0))

    def draw(self, surf):
        self.draw_face(surf)
        self.draw_label(surf)
        self.menu.draw(surf)
        return surf
