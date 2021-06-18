import math

from app.constants import TILEX, TILEY
from app.utilities import utils
from app.engine.game_state import game

class Camera():
    def __init__(self):
        # Where the camera is going
        self.target_x = 0
        self.target_y = 0
        # Where the camera actually is
        self.current_x = 0
        self.current_y = 0

        # How fast the camera should move
        self.speed = 8.0  # Linear speed based on distance from target

        # Whether the camera should be panning at a constant speed
        self.pan_mode = False
        self.pan_speed = 0.125  
        self.pan_targets = []

    def _shift_x(self, x):
        if x <= self.target_x + 2:
            self.target_x -= 1
        elif x >= (TILEX + self.target_x - 3):
            self.target_x += 1

    def _shift_y(self, y):
        if y <= self.target_y + 1:
            self.target_y -= 1
        elif y >= (TILEY + self.target_y - 2):
            self.target_y += 1

    def cursor_x(self, x):
        self._shift_x(x)

    def cursor_y(self, y):
        self._shift_y(y)

    def mouse_x(self, x):
        self._shift_x(x)

    def mouse_y(self, y):
        self._shift_y(y)

    def mouse_xy(self, x, y):
        """
        Gives mouse position
        """
        self.mouse_x(x)
        self.mouse_y(y)

    def _change_x(self, x):
        if x <= self.target_x + 3:
            new_x = x - 3
        elif x >= self.target_x + TILEX - 3:
            new_x = x - TILEX + 3
        else:
            new_x = self.target_x
        return new_x

    def _change_y(self, y):
        if y <= self.target_y + 3:
            new_y = y - 3
        elif y >= self.target_y + TILEY - 3:
            new_y = y - TILEY + 3
        else:
            new_y = self.target_y
        return new_y

    def _center_x(self, x):
        return utils.clamp(x - TILEX//2, 0, game.tilemap.width - TILEX)

    def _center_y(self, y):
        return utils.clamp(y - TILEY//2, 0, game.tilemap.height - TILEY)

    def set_xy(self, x, y):
        x = self._change_x(x)
        self.target_x = x
        y = self._change_y(y)
        self.target_y = y

    def force_xy(self, x, y):
        x = self._change_x(x)
        self.current_x = self.target_x = x
        y = self._change_y(y)
        self.current_y = self.target_y = y

    def set_center(self, x, y):
        x = self._center_x(x)
        self.target_x = x
        y = self._center_y(y)
        self.target_y = y

    def force_center(self, x, y):
        x = self._center_x(x)
        self.current_x = self.target_x = x
        y = self._center_y(y)
        self.current_y = self.target_y = y

    def set_center2(self, pos1, pos2):
        x1, y1 = pos1
        x2, y2 = pos2
        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2
        self.set_center(mid_x, mid_y)

    def get_x(self):
        return self.current_x

    def get_y(self):
        return self.current_y

    def get_xy(self):
        return self.current_x, self.current_y

    def at_rest(self):
        return self.current_x == self.target_x and self.current_y == self.target_y

    def set_target_limits(self, tilemap):
        if self.target_x < 0:
            self.target_x = 0
        elif self.target_x > tilemap.width - TILEX:
            self.target_x = tilemap.width - TILEX
        if self.target_y < 0:
            self.target_y = 0
        elif self.target_y > tilemap.height - TILEY:
            self.target_y = tilemap.height - TILEY

    def set_current_limits(self, tilemap):
        if self.current_x < 0:
            self.current_x = 0
        elif self.current_x > tilemap.width - TILEX:
            self.current_x = tilemap.width - TILEX
        if self.current_y < 0:
            self.current_y = 0
        elif self.current_y > tilemap.height - TILEY:
            self.current_y = tilemap.height - TILEY

    def update(self):
        # Make sure target is within bounds
        self.set_target_limits(game.tilemap)

        # Move camera around
        diff_x = self.target_x - self.current_x
        diff_y = self.target_y - self.current_y
        if self.pan_mode:
            self.current_x += self.pan_speed * utils.sign(diff_x)
            self.current_y += self.pan_speed * utils.sign(diff_y)
        elif diff_x or diff_y:
            dist = utils.distance((self.current_x, self.current_y), (self.target_x, self.target_y))
            total_speed = utils.clamp(dist / self.speed, min(dist, 0.25), 1.0)  # max of 0.5 is faithful to GBA, but I like the snappyness of 1.0
            angle = math.atan2(abs(diff_y), abs(diff_x))
            x_push = math.cos(angle)
            y_push = math.sin(angle)
            self.current_x += total_speed * x_push * utils.sign(diff_x)
            self.current_y += total_speed * y_push * utils.sign(diff_y)

        # If close enough to target, just make it so
        if abs(diff_x) <= 0.125:
            self.current_x = self.target_x
        if abs(diff_y) <= 0.125:
            self.current_y = self.target_y

        if self.pan_targets and self.at_rest():
            self.target_x, self.target_y = self.pan_targets.pop()

        # Make sure we do not go offscreen -- maybe shouldn't happen?
        # Could happen when map size changes?
        self.set_current_limits(game.tilemap)
