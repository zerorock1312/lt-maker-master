from app.engine import item_system
from app.engine.game_state import game

from app.engine.combat.simple_combat import SimpleCombat
from app.engine.combat.map_combat import MapCombat
from app.engine.combat.base_combat import BaseCombat
from app.engine.combat.animation_combat import AnimationCombat

from app.engine.objects.unit import UnitObject
from app.engine.objects.item import ItemObject

def has_animation(attacker, item, main_target, splash):
    return False

def engage(attacker: UnitObject, positions: list, main_item: ItemObject, skip: bool = False, script: list = None):
    """
    Builds the correct combat controller for this interaction

    Targets each of the positions in "positions" with the item
    Determines what kind of combat (Simple, Map, or Animation), should be used for this kind of interaction
    "positions" is a list. The subelements of positions can also be a list, if the item is a multitargeting item
    """
    target_positions = []
    main_targets = []
    splashes = []
    if main_item.sequence_item:
        items = main_item.subitems
    else:
        items = [main_item]
    for idx, position in enumerate(positions):
        item = items[idx]
        splash = set()
        if isinstance(position, list):
            for pos in position:
                main_target, s = item_system.splash(attacker, item, pos)
                if main_target:
                    splash.add(main_target)
                splash |= set(s)
            main_target = None
            target_positions.append(position[0])
        else:
            main_target, splash = item_system.splash(attacker, item, position)
            target_positions.append(position)
        main_targets.append(main_target)
        splashes.append(splash)

    if target_positions[0] is None:
        # If we are targeting None, (which means we're in base using an item)
        combat = BaseCombat(attacker, main_item, attacker, script)
    elif skip:
        # If we are skipping
        combat = SimpleCombat(attacker, main_item, items, target_positions, main_targets, splashes, script)
    elif len(positions) > 1 or len(items) > 1:
        combat = MapCombat(attacker, main_item, items, target_positions, main_targets, splashes, script)
    elif not main_targets[0] or splashes[0]:
        combat = MapCombat(attacker, main_item, items, target_positions, main_targets, splashes, script)
    elif has_animation(attacker, item, main_target, splash):
        combat = AnimationCombat(attacker, item, main_target, splash, script)
    else:
        combat = MapCombat(attacker, main_item, items, target_positions, main_targets, splashes, script)
    return combat

def start_combat(unit: UnitObject, target: tuple, item: ItemObject, 
                 ai_combat: bool = False, event_combat: bool = False, script: list = None):
    """
    Target is a position tuple
    """
    # Set up the target positions
    if item.sequence_item:
        targets = []
        for subitem in item.subitems:
            num_targets = item_system.num_targets(unit, subitem)
            if num_targets > 1:
                targets.append([target] * num_targets)
            else:
                targets.append(target)
    else:
        num_targets = item_system.num_targets(unit, item)
        if num_targets > 1:
            targets = [[target] * num_targets]
        else:
            targets = [target]

    combat = engage(unit, targets, item, script=script)
    combat.ai_combat = ai_combat # Must mark this so we can come back!
    combat.event_combat = event_combat # Must mark this so we can come back!
    game.combat_instance.append(combat)
    game.state.change('combat')
