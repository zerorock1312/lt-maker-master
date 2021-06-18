from app.utilities import utils, str_utils
from app.constants import TILEWIDTH, TILEHEIGHT

from app.engine import engine, image_mods

# Generic Animation Object
# Used, for instance, for miss and no damage animations

class Animation():
    def __init__(self, anim, position, delay=0, loop=False, hold=False, reverse=False):
        if not anim.image:
            anim.image = engine.image_load(anim.full_path)
            anim.image = anim.image.convert_alpha()
        self.sprite = anim.image
        self.position = position
        self.frame_x, self.frame_y = anim.frame_x, anim.frame_y
        self.num_frames = anim.num_frames
        self.speed = anim.speed
        self.delay = delay
        self.loop = loop
        self.hold = hold
        self.reverse = reverse
        self.enabled = True
        self.tint = False
        self.tint_after_delay = None

        self.width = self.sprite.get_width() // self.frame_x
        self.height = self.sprite.get_height() // self.frame_y

        self.image = engine.subsurface(self.sprite, (0, 0, self.width, self.height))

        self.counter = 0
        self.frames_held = 0
        self.first_update = engine.get_time()

    def use_center(self):
        self.position = self.position[0] - self.width//2, self.position[1] - self.height//2

    def is_ready(self, current_time):
        return self.enabled and (current_time - self.first_update >= self.delay)

    def get_position(self, offset):
        if offset:
            return self.position[0] + offset[0], self.position[1] + offset[1]
        else:
            return self.position

    def set_tint(self, val):
        self.tint = val

    def set_tint_after_delay(self, i):
        self.tint_after_delay = i

    def get_wait(self) -> int:
        if str_utils.is_int(self.speed):
            return self.num_frames * self.speed
        else:
            return utils.frames2ms(sum(self.speed))

    def update(self):
        current_time = engine.get_time()
        if not self.is_ready(current_time):
            return

        done = False
        if str_utils.is_int(self.speed):
            self.counter = int(current_time - self.first_update) // self.speed
            if self.counter >= self.num_frames:
                if self.loop:
                    self.counter = 0
                    self.first_update = current_time
                    self.delay = 0
                elif self.hold:
                    self.counter = self.num_frames - 1
                else:
                    self.counter = self.num_frames - 1
                    done = True
        else:  # Frame by frame timing
            num_frames = self.speed[self.counter]
            self.frames_held += 1
            if self.frames_held > num_frames:
                self.frames_held = 0
                self.counter += 1
            if self.counter >= min(len(self.speed), self.num_frames):
                if self.loop:
                    self.counter = 0
                    self.frames_held = 0
                    self.delay = 0
                elif self.hold:
                    self.counter = self.num_frames - 1
                else:
                    self.counter = self.num_frames - 1
                    done = True

        if self.tint_after_delay == self.counter:
            self.tint = True
            
        # Now actually create image
        if self.reverse:
            frame_counter = self.num_frames - 1 - self.counter
        else:
            frame_counter = self.counter
        left = (frame_counter % self.frame_x) * self.width
        top = (frame_counter // self.frame_x) * self.height
        self.image = engine.subsurface(self.sprite, (left, top, self.width, self.height))

        return done

    def draw(self, surf, offset=None, blend=None):
        current_time = engine.get_time()
        if not self.is_ready(current_time):
            return surf
        x, y = self.get_position(offset)
        if blend:
            image = image_mods.change_color(self.image, blend)
        else:
            image = self.image
        if self.tint:
            engine.blit(surf, image, (x, y), image.get_rect(), engine.BLEND_RGB_ADD)
        else:
            surf.blit(image, (x, y))
        return surf

class MapAnimation(Animation):
    def __init__(self, anim, position, delay=0, loop=False, hold=False):
        super().__init__(anim, position, delay, loop, hold)
        self.position = self.position[0] * TILEWIDTH, self.position[1] * TILEHEIGHT
        self.use_center()

    def use_center(self):
        self.position = self.position[0] + TILEWIDTH//2 - self.width//2, self.position[1] + TILEHEIGHT//2 - self.height//2

    def get_position(self, offset):
        if offset:
            return self.position[0] + offset[0] * TILEWIDTH, self.position[1] + offset[1] * TILEHEIGHT
        else:
            return self.position
