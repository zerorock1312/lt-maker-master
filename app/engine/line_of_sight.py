from app.utilities import utils
from enum import IntEnum

from app.engine.game_state import game

class Visibility(IntEnum):
    Unknown = 0
    Dark = 1
    Lit = 2

def get_line(start: tuple, end: tuple) -> bool:
    if start == end:
        return True
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    x, y = x1, y1

    xstep, ystep = 1, 1
    if dy < 0:
        ystep = -1
        dy = -dy
    if dx < 0:
        xstep = -1
        dx = -dx
    ddy, ddx = 2*dy, 2*dx

    if ddx >= ddy:
        errorprev = error = dx
        for i in range(dx):
            x += xstep
            error += ddy
            # How far off the straight line to the right are you
            if error > ddx:
                y += ystep
                error -= ddx
                if error + errorprev < ddx:  # Bottom square
                    pos = x, y - ystep
                    if pos != end and game.board.get_opacity(pos):
                        return False
                elif error + errorprev > ddx:  # Left square
                    pos = x - xstep, y
                    if pos != end and game.board.get_opacity(pos):
                        return False
                else:  # Through the middle
                    pos1, pos2 = (x, y - ystep), (x - xstep, y)
                    if game.board.get_opacity(pos1) and game.board.get_opacity(pos2):
                        return False
            pos = x, y
            if pos != end and game.board.get_opacity(pos):
                return False
            errorprev = error
    else:
        errorprev = error = dy
        for i in range(dy):
            y += ystep
            error += ddx
            if error > ddy:
                x += xstep
                error -= ddy
                if error + errorprev < ddy:  # Bottom square
                    pos = x - xstep, y
                    if pos != end and game.board.get_opacity(pos):
                        return False
                elif error + errorprev > ddy:  # Left square
                    pos = x, y - ystep
                    if pos != end and game.board.get_opacity(pos):
                        return False
                else:  # Through the middle
                    pos1, pos2 = (x, y - ystep), (x - xstep, y)
                    if game.board.get_opacity(pos1) and game.board.get_opacity(pos2):
                        return False
            pos = x, y
            if pos != end and game.board.get_opacity(pos):
                return False
            errorprev = error
    assert x == x2 and y == y2
    return True

def line_of_sight(source_pos: list, dest_pos: list, max_range: int) -> list:
    all_tiles = {}
    for pos in dest_pos:
        if pos in source_pos:
            all_tiles[pos] = Visibility.Lit
        else:
            all_tiles[pos] = Visibility.Unknown

    # Iterate over remaining tiles
    for pos, vis in all_tiles.items():
        if vis == Visibility.Unknown:
            for s_pos in source_pos:
                if utils.calculate_distance(pos, s_pos) <= max_range and get_line(s_pos, pos):
                    all_tiles[pos] = Visibility.Lit
                    break
            else:
                all_tiles[pos] = Visibility.Dark

    lit_tiles = [pos for pos in dest_pos if all_tiles[pos] != Visibility.Dark]
    return lit_tiles

def simple_check(dest_pos: tuple, team: str, max_range: int) -> bool:
    """
    Returns true if can see position with line of sight
    """
    player_pos = [unit.position for unit in game.units if unit.position and unit.team == team]
    for s_pos in player_pos:
        if s_pos == dest_pos:
            return True
        elif utils.calculate_distance(dest_pos, s_pos) <= max_range and get_line(s_pos, dest_pos):
            return True
    return False
