from app.sprites import SPRITES

from app.engine import engine

for sprite in SPRITES.values():
    sprite.image = engine.image_load(sprite.full_path)
