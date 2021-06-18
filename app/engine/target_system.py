from app.utilities import utils
from app.data.database import DB
from app.engine import pathfinding, skill_system, equations, \
    item_funcs, item_system, line_of_sight
from app.engine.game_state import game

# Consider making these sections faster
def get_shell(valid_moves: set, potential_range: set, width: int, height: int) -> set:
    valid_attacks = set()
    for valid_move in valid_moves:
        valid_attacks |= find_manhattan_spheres(potential_range, valid_move[0], valid_move[1])
    return {pos for pos in valid_attacks if 0 <= pos[0] < width and 0 <= pos[1] < height}

# Consider making these sections faster -- use memory?
def find_manhattan_spheres(rng: set, x: int, y: int) -> set:
    _range = range
    _abs = abs
    main_set = set()
    for r in rng:
        # Finds manhattan spheres of radius r
        for i in _range(-r, r + 1):
            magn = _abs(i)
            main_set.add((x + i, y + r - magn))
            main_set.add((x + i, y - r + magn))
    return main_set

def get_nearest_open_tile(unit, position):
    r = 0
    _abs = abs
    while r < 10:
        for x in range(-r, r + 1):
            magn = _abs(x)
            n1 = position[0] + x, position[1] + r - magn
            n2 = position[0] + x, position[1] - r + magn
            if game.movement.check_traversable(unit, n1) and not game.board.get_unit(n1):
                return n1
            elif game.movement.check_traversable(unit, n2) and not game.board.get_unit(n2):
                return n2
        r += 1
    return None

def distance_to_closest_enemy(unit, pos=None):
    if pos is None:
        pos = unit.position
    enemy_list = [u for u in game.units if u.position and skill_system.check_enemy(u, unit)]
    if not enemy_list:
        return 100  # No enemies
    dist_list = [utils.calculate_distance(enemy.position, pos) for enemy in enemy_list]
    return min(dist_list)

def get_adjacent_positions(pos):
    x, y = pos
    adjs = ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1))
    return [a for a in adjs if 0 <= a[0] < game.tilemap.width and 0 <= a[1] < game.tilemap.height]

def get_adj_units(unit) -> list:
    adj_positions = get_adjacent_positions(unit.position)
    adj_units = [game.board.get_unit(pos) for pos in adj_positions]
    adj_units = [_ for _ in adj_units if _]
    return adj_units

def get_adj_allies(unit) -> list:
    adj_units = get_adj_units(unit)
    adj_allies = [u for u in adj_units if skill_system.check_ally(unit, u)]
    return adj_allies

def get_attacks(unit, item=None, force=False) -> set:
    """
    Determines all possible positions the unit could attack
    Does not attempt to determine if an enemy is actually in that place
    """
    if not force and unit.has_attacked:
        return set()
    if not item:
        item = unit.get_weapon()
    if not item:
        return set()

    item_range = item_funcs.get_range(unit, item)
    attacks = get_shell({unit.position}, item_range, game.tilemap.width, game.tilemap.height)
    return attacks

def get_possible_attacks(unit, valid_moves) -> set:
    attacks = set()
    max_range = 0
    for item in get_all_weapons(unit):
        item_range = item_funcs.get_range(unit, item)
        max_range = max(max_range, max(item_range))
        attacks |= get_shell(valid_moves, item_range, game.tilemap.width, game.tilemap.height)

    if DB.constants.value('line_of_sight'):
        attacks = set(line_of_sight.line_of_sight(valid_moves, attacks, max_range))
    return attacks

def get_possible_spell_attacks(unit, valid_moves) -> set:
    attacks = set()
    max_range = 0
    for item in get_all_spells(unit):
        item_range = item_funcs.get_range(unit, item)
        max_range = max(max_range, max(item_range))
        attacks |= get_shell(valid_moves, item_range, game.tilemap.width, game.tilemap.height)

    if DB.constants.value('line_of_sight'):
        attacks = set(line_of_sight.line_of_sight(valid_moves, attacks, max_range))
    return attacks

# Uses all weapons the unit has access to to find its potential range
def find_potential_range(unit, weapon=True, spell=False, boundary=False) -> set:
    if weapon and spell:
        items = [item for item in unit.items if item_funcs.available(unit, item) and
                 item_system.is_weapon(unit, item) or item_system.is_spell(unit, item)]
    elif weapon:
        items = get_all_weapons(unit)
    elif spell:
        items = get_all_spells(unit)
    else:
        return set()
    potential_range = set()
    for item in items:
        for rng in item_funcs.get_range(unit, item):
            potential_range.add(rng)
    return potential_range

def get_valid_moves(unit, force=False) -> set:
    # Assumes unit is on the map
    if not force and unit.finished:
        return set()

    mtype = game.movement.get_movement_group(unit)
    grid = game.board.get_grid(mtype)
    width, height = game.tilemap.width, game.tilemap.height
    pass_through = skill_system.pass_through(unit)
    ai_fog_of_war = DB.constants.value('ai_fog_of_war')
    pathfinder = pathfinding.Djikstra(unit.position, grid, width, height, unit.team, pass_through, ai_fog_of_war)

    movement_left = equations.parser.movement(unit) if force else unit.movement_left

    valid_moves = pathfinder.process(game.board, movement_left)
    valid_moves.add(unit.position)
    return valid_moves

def get_path(unit, position, ally_block=False) -> list:
    mtype = game.movement.get_movement_group(unit)
    grid = game.board.get_grid(mtype)

    width, height = game.tilemap.width, game.tilemap.height
    pass_through = skill_system.pass_through(unit)
    ai_fog_of_war = DB.constants.value('ai_fog_of_war')
    pathfinder = pathfinding.AStar(unit.position, position, grid, width, height, unit.team, pass_through, ai_fog_of_war)

    path = pathfinder.process(game.board, ally_block=ally_block)
    if path is None:
        return []
    return path

def check_path(unit, path) -> bool:
    movement = equations.parser.movement(unit)
    prev_pos = None
    for pos in path[:-1]:  # Don't need to count the starting position
        if prev_pos and pos not in get_adjacent_positions(prev_pos):
            return False
        mcost = game.movement.get_mcost(unit, pos)
        movement -= mcost
        if movement < 0:
            return False
        prev_pos = pos
    return True

def travel_algorithm(path, moves, unit, grid):
    """
    Given a long path, travels along that path as far as possible
    """
    if not path:
        return unit.position

    moves_left = moves
    through_path = 0
    for position in path[::-1][1:]:  # Remove start position, travel backwards
        moves_left -= grid[position[0] * game.tilemap.height + position[1]].cost
        if moves_left >= 0:
            through_path += 1
        else:
            break
    # Don't move where a unit already is, and don't make through path < 0
    # Lower the through path by one, cause we can't move that far
    while through_path > 0 and any(other_unit.position == path[-(through_path + 1)] for other_unit in game.units if unit is not other_unit):
        through_path -= 1
    return path[-(through_path + 1)]  # Travel as far as we can

def get_valid_targets(unit, item=None) -> set:
    """
    Determines all the valid targets given use of the item
    item_system.valid_targets takes care of range
    """
    if not item:
        item = unit.get_weapon()
    if not item:
        return set()

    # Check sequence item targeting
    if item.sequence_item:
        all_targets = set()
        for subitem in item.subitems:
            valid_targets = get_valid_targets(unit, subitem)
            if not valid_targets:
                return set()
            all_targets |= valid_targets
        # If not enough legal targets, also no legal targets
        if not item_system.allow_same_target(unit, item) and len(all_targets) < len(item.subitems):
            return set()

    # Handle regular item targeting
    all_targets = item_system.valid_targets(unit, item)
    valid_targets = set()
    for position in all_targets:
        splash = item_system.splash(unit, item, position)
        valid = item_system.target_restrict(unit, item, *splash)
        if valid:
            valid_targets.add(position)
    # Fog of War
    if unit.team == 'player' or DB.constants.value('ai_fog_of_war'):
        valid_targets = {position for position in valid_targets if game.board.in_vision(position, unit.team)}
    # Line of Sight
    if DB.constants.value('line_of_sight'):
        max_item_range = max(item_funcs.get_range(unit, item))
        valid_targets = set(line_of_sight.line_of_sight([unit.position], valid_targets, max_item_range))
    return valid_targets

def get_all_weapons(unit) -> list:
    return [item for item in item_funcs.get_all_items(unit) if item_system.is_weapon(unit, item) and item_funcs.available(unit, item)]

def get_all_weapon_targets(unit) -> set:
    weapons = get_all_weapons(unit)
    targets = set()
    for weapon in weapons:
        targets |= get_valid_targets(unit, weapon)
    return targets

def get_all_spells(unit):
    return [item for item in item_funcs.get_all_items(unit) if item_system.is_spell(unit, item) and item_funcs.available(unit, item)]

def get_all_spell_targets(unit) -> set:
    spells = get_all_spells(unit)
    targets = set()
    for spell in spells:
        targets |= get_valid_targets(unit, spell)
    return targets
