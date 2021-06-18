from app.engine.sprites import SPRITES
from app.engine import engine

def create_base_surf(width, height, base='menu_bg_base'):
    sprite = SPRITES.get(base)
    
    base_width = sprite.get_width()
    base_height = sprite.get_height()

    full_width = width - width%(base_width//3)
    full_height = height - height%(base_height//3)
    width = base_width//3
    height = base_height//3

    assert full_width%width == 0, "The dimensions of the menu are wrong (width: %d %d)" % (full_width, width)
    assert full_height%height == 0, "The dimensions of the menu are wrong (height: %d %d)" % (full_height, height)

    surf = engine.create_surface((full_width, full_height), transparent=True)

    topleft = engine.subsurface(sprite, (0, 0, width, height))
    top = engine.subsurface(sprite, (width, 0, width, height))
    topright = engine.subsurface(sprite, (2 * width, 0, width, height))
    midleft = engine.subsurface(sprite, (0, height, width, height))
    mid = engine.subsurface(sprite, (width, height, width, height))
    midright = engine.subsurface(sprite, (2 * width, height, width, height))
    botleft = engine.subsurface(sprite, (0, 2 * height, width, height))
    bot = engine.subsurface(sprite, (width, 2 * height, width, height))
    botright = engine.subsurface(sprite, (2 * width, 2 * height, width, height))

    # center sprite
    for x in range(full_width//width - 2):
        for y in range(full_height//height - 2):
            surf.blit(mid, ((x + 1) * width, (y + 1) * height))

    # edges
    for x in range(full_width//width - 2):
        surf.blit(top, ((x + 1) * width, 0))
        surf.blit(bot, ((x + 1) * width, full_height - height))

    for y in range(full_height//height - 2):
        surf.blit(midleft, (0, (y + 1) * height))
        surf.blit(midright, (full_width - width, (y + 1) * height))

    # corners
    surf.blit(topleft, (0, 0))
    surf.blit(topright, (full_width - width, 0))
    surf.blit(botleft, (0, full_height - height))
    surf.blit(botright, (full_width - width, full_height - height))

    return surf
