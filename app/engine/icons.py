from app.utilities import utils

from app.constants import COLORKEY
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine import engine, skill_system, image_mods
from app.engine.game_state import game

def get_icon(item):
    if not item:
        return None
    image = RESOURCES.icons16.get(item.icon_nid)
    if not image:
        return None

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (item.icon_index[0] * 16, item.icon_index[1] * 16, 16, 16))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)
    return image

def draw_item(surf, item, topleft, cooldown=False):
    image = get_icon(item)
    if not image:
        return None

    surf.blit(image, topleft)

    return surf

def draw_skill(surf, skill, topleft, compact=True, simple=False):
    image = get_icon(skill)
    if not image:
        return None

    surf.blit(image, topleft)
    if simple:
        return surf
    frac = skill_system.get_cooldown(skill)
    if frac is not None and frac < 1:
        cooldown_surf = SPRITES.get('icon_cooldown')
        index = utils.clamp(int(8 * frac), 0, 7)
        c = engine.subsurface(cooldown_surf, (16 * index, 0, 16, 16))
        surf.blit(c, topleft)

    if compact:
        pass
    else:
        text = skill_system.get_text(skill)
        if text is not None:
            FONT['text-blue'].blit(text, surf, (topleft[0] + 16, topleft[1]))
    
    return surf

def draw_weapon(surf, weapon_type, topleft, gray=False):
    w_type_obj = DB.weapons.get(weapon_type)
    if not w_type_obj:
        return surf
    image = RESOURCES.icons16.get(w_type_obj.icon_nid)
    if not image:
        return surf

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (w_type_obj.icon_index[0] * 16, w_type_obj.icon_index[1] * 16, 16, 16))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)

    if gray:
        image = image_mods.make_gray(image.convert_alpha())
    
    surf.blit(image, topleft)
    return surf

def draw_faction(surf, faction, topleft):
    image = RESOURCES.icons32.get(faction.icon_nid)
    if not image:
        return surf

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (faction.icon_index[0] * 32, faction.icon_index[1] * 32, 32, 32))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)
    
    surf.blit(image, topleft)
    return surf

def get_portrait(unit):
    image = RESOURCES.portraits.get(unit.portrait_nid)
    if image:
        if not image.image:
            image.image = engine.image_load(image.full_path)
        image = engine.subsurface(image.image, (0, 0, 96, 80))
    else:  # Generic class portrait
        klass = DB.classes.get(unit.klass)
        image = RESOURCES.icons80.get(klass.icon_nid)
        if not image:
            return None
        if not image.image:
            image.image = engine.image_load(image.full_path)
        image = engine.subsurface(image.image, (klass.icon_index[0] * 80, klass.icon_index[1] * 72, 80, 72))
        
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)

    return image

def get_portrait_from_nid(portrait_nid):
    image = RESOURCES.portraits.get(portrait_nid)
    if image:
        if not image.image:
            image.image = engine.image_load(image.full_path)
        image = engine.subsurface(image.image, (0, 0, 96, 80))
        image = image.convert()
        engine.set_colorkey(image, COLORKEY, rleaccel=True)
    return image

def draw_portrait(surf, unit, topleft=None, bottomright=None):
    image = get_portrait(unit)
    if not image:
        return None

    if topleft:
        surf.blit(image, topleft)
    elif bottomright:
        surf.blit(image, (bottomright[0] - 96, bottomright[1] - 80))
    return surf

def draw_chibi(surf, nid, topleft=None, bottomright=None):
    image = RESOURCES.portraits.get(nid)
    if not image:
        return surf

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (96, 16, 32, 32))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)

    if topleft:
        surf.blit(image, topleft)
    elif bottomright:
        surf.blit(image, (bottomright[0] - 32, bottomright[1] - 32))
    return surf

def draw_stat(surf, stat_nid, unit, topright, compact=False):
    if stat_nid not in DB.stats.keys():
        FONT['text-yellow'].blit_right('--', surf, topright)
        return
    class_obj = DB.classes.get(unit.klass)
    value = unit.stats.get(stat_nid, 0)
    bonus = unit.stat_bonus(stat_nid)
    if compact:
        pass
    else:
        if value >= class_obj.max_stats.get(stat_nid, 30):
            FONT['text-yellow'].blit_right(str(value), surf, topright)
        else:
            FONT['text-blue'].blit_right(str(value), surf, topright)
        if bonus > 0:
            FONT['small-green'].blit("+%d" % bonus, surf, topright)
        elif bonus < 0:
            FONT['text-red'].blit(str(bonus), surf, topright)

def draw_growth(surf, stat_nid, unit, topright, compact=False):
    if stat_nid not in DB.stats.keys():
        FONT['text-yellow'].blit_right('--', surf, topright)
        return
    class_obj = DB.classes.get(unit.klass)
    value = unit.growths.get(stat_nid, 0)
    bonus = unit.growth_bonus(stat_nid)
    klass_bonus = class_obj.growth_bonus.get(stat_nid, 0)
    bonus += klass_bonus
    difficulty_bonus = game.mode.get_growth_bonus(unit)
    d_bonus = difficulty_bonus.get(stat_nid, 0)
    bonus += d_bonus
    if compact:
        pass
    else:
        FONT['text-blue'].blit_right(str(value), surf, topright)
        if bonus > 0:
            FONT['small-green'].blit("+%d" % bonus, surf, topright)
        elif bonus < 0:
            FONT['text-red'].blit(str(bonus), surf, topright)
