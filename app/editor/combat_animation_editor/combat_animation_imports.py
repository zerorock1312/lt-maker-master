import os, glob

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, qRgb, QColor, QPainter

from app import utilities
from app.resources.resources import RESOURCES
from app.resources import combat_anims, combat_commands, combat_palettes

import app.editor.utilities as editor_utilities

def import_from_lion_throne(current, fn):
    """
    Imports weapon animations from a Lion Throne formatted combat animation script file.

    Parameters
    ----------
    current: CombatAnimation
        Combat animation to install new weapon animation onto
    fn: str, filename
        "*-Script.txt" file to read from
    """

    print(fn)
    if '-Script.txt' not in fn:
        QMessageBox.critical(None, "Error", "Not a valid combat animation script file: %s" % fn)
        return
    kind = os.path.split(fn)[-1].replace('-Script.txt', '')
    print(kind)
    nid, weapon = kind.split('-')
    index_fn = fn.replace('-Script.txt', '-Index.txt')
    if not os.path.exists(index_fn):
        QMessageBox.critical(None, "Error", "Could not find associated index file: %s" % index_fn)
        return
    images = glob.glob(fn.replace('-Script.txt', '-*.png'))
    if not images:
        QMessageBox.critical(None, "Error", "Could not find any associated palettes")
        return

    # Propulate palettes
    for image_fn in images:
        palette_name = os.path.split(image_fn)[-1][:-4].split('-')[-1]
        palette_nid = nid + '_' + palette_name
        if palette_name not in [_[0] for _ in current.palettes]:
            if palette_nid not in RESOURCES.combat_palettes:
                # Need to create palette
                pix = QPixmap(image_fn)
                palette_colors = editor_utilities.find_palette(pix.toImage())
                new_palette = combat_palettes.Palette(palette_nid)
                colors = {(int(idx % 8), int(idx / 8)): color for idx, color in enumerate(palette_colors)}
                new_palette.colors = colors
                RESOURCES.combat_palettes.append(new_palette)
            current.palettes.append([palette_name, palette_nid])
    new_weapon = combat_anims.WeaponAnimation(weapon)

    # Now add frames to weapon animation
    with open(index_fn, encoding='utf-8') as index_fp:
        index_lines = [line.strip() for line in index_fp.readlines()]
        index_lines = [l.split(';') for l in index_lines]

    # Use the first palette
    palette_name, palette_nid = current.palettes[0]
    palette = RESOURCES.combat_palettes.get(palette_nid)
    colors = palette.colors

    # Need to convert to universal coord palette
    convert_dict = {qRgb(*color): qRgb(0, coord[0], coord[1]) for coord, color in colors.items()}
    main_pixmap = QPixmap(images[0])
    for i in index_lines:
        nid = i[0]
        x, y = [int(_) for _ in i[1].split(',')]
        width, height = [int(_) for _ in i[2].split(',')]
        offset_x, offset_y = [int(_) for _ in i[3].split(',')]
        new_pixmap = main_pixmap.copy(x, y, width, height)
        # Need to convert to universal base palette
        im = new_pixmap.toImage()
        im = editor_utilities.color_convert(im, convert_dict)
        new_pixmap = QPixmap.fromImage(im)
        new_frame = combat_anims.Frame(nid, (x, y, width, height), (offset_x, offset_y), pixmap=new_pixmap)
        new_weapon.frames.append(new_frame)

    # Need to build full image file now
    sprite_sheet = QPixmap(main_pixmap.width(), main_pixmap.height())
    sprite_sheet.fill(QColor(0, 0, 0))
    painter = QPainter()
    painter.begin(sprite_sheet)
    for frame in new_weapon.frames:
        x, y, width, height = frame.rect
        painter.drawPixmap(x, y, frame.pixmap)
    painter.end()
    new_weapon.pixmap = sprite_sheet

    # Now add poses to the weapon anim
    with open(fn, encoding='utf-8') as script_fp:
        script_lines = [line.strip() for line in script_fp.readlines()]
        script_lines = [line.split(';') for line in script_lines if line and not line.startswith('#')]
    current_pose = None
    for line in script_lines:
        if line[0] == 'pose':
            current_pose = combat_anims.Pose(line[1])
            new_weapon.poses.append(current_pose)
        else:
            command = combat_commands.parse_text(line)
            current_pose.timeline.append(command)
    # Actually add weapon to current
    if new_weapon.nid in current.weapon_anims.keys():
        current.weapon_anims.remove_key(new_weapon.nid)
    current.weapon_anims.append(new_weapon)
    print("Done!!! %s" % fn)

# === IMPORT FROM GBA ========================================================
def update_weapon_anim_pixmap(weapon_anim):
    width_limit = 1200
    left = 0
    heights = []
    max_heights = []
    for frame in weapon_anim.frames:
        width, height = frame.pixmap.width(), frame.pixmap.height()
        if left + width > width_limit:
            max_heights.append(max(heights))
            frame.rect = (0, sum(max_heights), width, height)
            heights = [height]
            left = width
        else:
            frame.rect = (left, sum(max_heights), width, height)
            left += width
            heights.append(height)

    total_width = min(width_limit, sum(frame.rect[2] for frame in weapon_anim.frames))
    total_height = sum(max_heights)
    print(total_width, total_height)
    new_pixmap = QPixmap(total_width, total_height)
    new_pixmap.fill(QColor(editor_utilities.qCOLORKEY))
    painter = QPainter()
    painter.begin(new_pixmap)
    for frame in weapon_anim.frames:
        x, y, width, height = frame.rect
        painter.drawPixmap(x, y, frame.pixmap)
    painter.end()
    weapon_anim.pixmap = new_pixmap

def convert_gba(pixmap: QPixmap) -> QPixmap:
    im = pixmap.toImage()
    im.convertTo(QImage.Format_Indexed8)
    im = editor_utilities.convert_gba(im)
    pixmap = QPixmap.fromImage(im)
    return pixmap

def get_palette(pixmap: QPixmap) -> list:
    im = pixmap.toImage()
    w = im.width()
    # Image is always an extra 8 pixels wide, to accomodate palette!
    assert w == 248 or w == 448
    colors = []
    for x in range(w - 8, w, -1):  # Reverse
        for y in range(2):
            color = im.pixel(x, y)
            if color not in colors:
                colors.append(color)
    palette = [QColor(color) for color in colors]
    palette = [(c.red(), c.green(), c.blue()) for c in palette]
    return palette

def simple_crop(pixmap: QPixmap) -> QPixmap:
    if pixmap.width() == 248:
        pixmap = pixmap.copy(0, 0, 240, pixmap.height())
    elif pixmap.width() == 488:
        pixmap = pixmap.copy(0, 0, 480, pixmap.height())
    return pixmap

def split_doubles(pixmaps: dict) -> dict:
    new_pixmaps = {}
    for name in pixmaps.keys():
        pix = pixmaps[name]
        if pix.width == 480:
            pix1 = pix.copy(0, 0, 240, pix.height())
            pix2 = pix.copy(240, 0, 240, pix.height())
            new_pixmaps[name] = pix1
            new_pixmaps[name + '_under'] = pix2
    pixmaps.update(new_pixmaps)
    return pixmaps

def color_convert(pixmap: QPixmap, convert_dict: dict) -> QPixmap:
    im = pixmap.toImage()
    im = editor_utilities.color_convert(im, convert_dict)
    pixmap = QPixmap.fromImage(im)
    return pixmap

def find_empty_pixmaps(pixmaps: dict) -> set:
    empty_pixmaps = set()
    for name, pixmap in pixmaps.items():
        x, y, width, height = editor_utilities.get_bbox(pixmap.toImage())
        if width > 0 and height > 0:
            pass
        else:
            empty_pixmaps.add(name)
    return empty_pixmaps

def import_from_gba(current, fn):
    """
    Imports weapon animations from GBA formatted combat animation script file.

    Parameters
    ----------
    current: CombatAnimation
        Combat animation to install new weapon animation onto
    fn: str, filename
        "*.txt" file to read from
    """
    weapon_types = {'Sword', 'Lance', 'Axe', 'Disarmed', 'Unarmed', 'Handaxe',
                    'Bow', 'Magic', 'Staff', 'Monster', 'Dragonstone', 'Refresh'}
    print(fn)
    head, tail = os.path.split(fn)
    print(tail)
    tail = tail.replace('_without_comment', '')
    
    weapon_type = tail[:-4]
    if weapon_type not in weapon_types:
        QMessageBox.critical(None, "Error", "Weapon type %s not a supported weapon type!" % weapon_type)
        return
    if weapon_type == 'Disarmed':
        weapon_type = 'Unarmed'
    elif weapon_type == 'Monster':
        weapon_type = 'Neutral'

    image_paths = os.path.join(head, '*.png')
    images = glob.glob(image_paths)
    # Convert to pixmaps
    pixmaps = {os.path.split(path)[-1][:-4]: QPixmap(path) for path in images}
    # Convert to GBA colors
    pixmaps = {name: convert_gba(pix) for name, pix in pixmaps.items()}
    # Find palette
    palette = get_palette(list(pixmaps.values())[0])
    palette_nid = utilities.get_next_name("GenericBlue", current.palettes.keys())
    new_palette = combat_anims.Palette(palette_nid, palette)
    current.palettes.append(new_palette)
    # Now do a simple crop to get rid of palette extras
    pixmaps = {name: simple_crop(pix) for name, pix in pixmaps.items()}
    # Split double images into "_under" image
    pixmaps = split_doubles(pixmaps)
    # Convert pixmaps to new palette colors
    base_colors = combat_anims.base_palette.colors
    convert_dict = {qRgb(*a): qRgb(*b) for a, b in zip(palette, base_colors)}
    pixmaps = {name: color_convert(pixmap, convert_dict) for name, pixmap in pixmaps.items()}
    # Determine which pixmaps should be replaced by "wait" commands
    empty_pixmaps = find_empty_pixmaps(pixmaps)

    # So now we have melee_anim and ranged_anim with all poses
    melee_weapon_anim, ranged_weapon_anim = parse_gba_script(fn, pixmaps, weapon_type, empty_pixmaps)

    # Animation collation
    update_weapon_anim_pixmap(melee_weapon_anim)
    update_weapon_anim_pixmap(ranged_weapon_anim)

    def unarmed_pose_setup(weapon_anim):
        stand_pose = weapon_anim.poses.get('Stand')
        dodge_pose = weapon_anim.poses.get('Dodge')
        weapon_anim.poses.clear()
        weapon_anim.poses.append(stand_pose)
        weapon_anim.poses.append(dodge_pose)

    def add_weapon(weapon_anim):
        if weapon_anim.nid in current.weapon_anims.keys():
            current.weapon_anims.remove_key(weapon_anim.nid)
        current.weapon_anims.append(weapon_anim)

    # Now write scripts
    if weapon_type == 'Sword':
        melee_weapon_anim.nid = "Sword"
        ranged_weapon_anim.nid = "MagicSword"
        add_weapon(melee_weapon_anim)
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Lance':
        melee_weapon_anim.nid = "Lance"
        ranged_weapon_anim.nid = "RangedLance"
        add_weapon(melee_weapon_anim)
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Axe':
        melee_weapon_anim.nid = "Axe"
        ranged_weapon_anim.nid = "MagicAxe"
        add_weapon(melee_weapon_anim)
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Handaxe':
        ranged_weapon_anim.nid = "RangedAxe"
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Bow':
        ranged_weapon_anim.nid = "RangedBow"
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Unarmed':
        melee_weapon_anim.nid = "Unarmed"
        # Make sure we only use stand and dodge poses
        unarmed_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    elif weapon_type == 'Magic':
        ranged_weapon_anim.nid = "MagicGeneric"
        add_weapon(ranged_weapon_anim)
        melee_weapon_anim.nid = "Unarmed"
        unarmed_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    elif weapon_type == 'Staff':
        ranged_weapon_anim.nid = "MagicStaff"
        add_weapon(ranged_weapon_anim)
    elif weapon_type == 'Neutral':
        melee_weapon_anim.nid = "Neutral"
        add_weapon(melee_weapon_anim)
        ranged_weapon_anim.nid = "RangedNeutral"
        add_weapon(ranged_weapon_anim)
    elif weapon_type == 'Dragonstone':
        ranged_weapon_anim.nid = "Dragonstone"
        add_weapon(ranged_weapon_anim)
    elif weapon_type == 'Refresh':
        ranged_weapon_anim.nid = "Refresh"
        add_weapon(ranged_weapon_anim)
        melee_weapon_anim.nid = "Unarmed"
        unarmed_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    print("Done!!! %s" % fn)

def parse_gba_script(fn, pixmaps, weapon_type, empty_pixmaps):
    # Read script
    # Now add poses to the weapon anim
    with open(fn, encoding='utf-8') as script_fp:
        script_lines = [line.strip() for line in script_fp.readlines()]
        script_lines = [(line[:line.index('#')] if '#' in line else line) for line in script_lines]
        script_lines = [line for line in script_lines if line]

    current_mode: int = None
    current_anim: combat_anims.WeaponAnimation = None
    current_pose: combat_anims.Pose = None
    current_frame: combat_commands.CombatAnimationCommand = None
    melee_weapon_anim = combat_anims.WeaponAnimation('prototype')
    ranged_weapon_anim = combat_anims.WeaponAnimation('prototype')
    used_images = set()

    begin = False  # Whether this is the first frame
    crit = False  # Whether this is a critical hit
    start_hit = False  # Whether we need to append our start_hit command after the next frame
    dodge_front = False  # Whether we should use over frames
    throwing_axe = False  # Whether the next 01 command is catching the throwing axe
    shield_toss = False  # Whether the next 01 command ends the shield toss
    loop_end = False  # Whether the next 01 command ends the loop

    def get_pose_name(mode: int) -> (str, bool):
        """
        Determines what pose to use and whether to use
        the melee script or a ranged/magic script
        """
        # Ignore certain modes if magical
        if weapon_type in ('Magic', 'Staff', 'Refresh'):
            if mode not in (5, 6, 7, 8, 9, 11):
                return None, None
        # Only certain modes allowed for transforming and reverting
        if weapon_type in ('Transform', 'Revert'):
            if mode not in (1, 9, 11):
                return None, None
        if mode in (1, 2):
            return 'Attack', melee_weapon_anim
        elif mode in (3, 4):
            return 'Critical', melee_weapon_anim
        elif mode == 5:
            return 'Attack', ranged_weapon_anim
        elif mode == 6:
            return 'Critical', ranged_weapon_anim
        elif mode == 7:
            return 'Dodge', melee_weapon_anim
        elif mode == 8:
            return 'Dodge', ranged_weapon_anim
        elif mode in 9:
            return 'Stand', melee_weapon_anim
        elif mode == 11:
            return 'Stand', ranged_weapon_anim
        elif mode == 12:
            return 'Miss', melee_weapon_anim
        else:
            return None, None

    def parse_text(text):
        command = combat_commands.parse_text(text)
        # If there is a frame in the command,
        # add it to the set of used images
        if command.has_frames():
            frames = command.get_frames()
            if any(f in empty_pixmaps for f in frames):
                command = combat_commands.parse_text('wait;%d' % command.value[0])
            else:
                for frame in frames:
                    used_images.add(frame)
            global current_frame
            current_frame = command

        current_pose.timeline.append(command)

    def copy_frame(frame_command, num_frames):
        # combat_commands.CombatAnimationCommand.copy()
        new_command = frame_command.__class__.copy(frame_command)
        new_command.set_frame_count(num_frames)
        current_pose.timeline.append(new_command)

    def wait_for_hit(frame_command):
        if frame_command.nid in ('frame', 'over_frame', 'under_frame', 'frame_with_offset'):
            frame_name = frame_command.value[1]
            new_command = combat_commands.parse_text('wait_for_hit;%s' % frame_name)
            current_pose.timeline.append(new_command)
        elif frame_command.nid == 'dual_frame':
            frame_name1 = frame_command.value[1]
            frame_name2 = frame_command.value[2]
            new_command = combat_commands.parse_text('wait_for_hit;%s;%s' % (frame_name1, frame_name2))
            current_pose.timeline.append(new_command)
        else:
            return

    def save_images(current_pose):
        if current_anim:
            for frame_nid in used_images:
                if frame_nid in current_anim.frames.keys():
                    # Don't bother if already present
                    continue
                pixmap = pixmaps[frame_nid]
                x, y, width, height = editor_utilities.get_bbox(pixmap.toImage())
                if width > 0 and height > 0:
                    pixmap = pixmap.copy(x, y, width, height)
                    new_frame = combat_anims.Frame(frame_nid, (0, 0, width, height), (x, y), pixmap=pixmap)
                    current_anim.frames.append(new_frame) 
        used_images.clear()

    def cape_animation():
        parse_text('effect;Cape Animation')
        for name, pixmap in pixmaps.items():
            # Make sure to include the extra frames that may be necessary to do this
            used_images.add(name)
        print('Replace "effect;Cape Animation" with actual frames for cape animation in a loop')
        print("For instance:")
        print("start_loop")
        print("    frame;3;Magic033")
        print("    frame;3;Magic034")
        print("end_loop")

    for line in script_lines:
        if line.startswith('/// - '):
            if current_mode:
                save_images(current_pose)
            if line.startswith('/// - Mode '):
                current_mode = int(line[11:])
                pose_name, current_anim = get_pose_name(current_mode)
                current_pose = combat_anims.Pose(pose_name)
                if current_anim:
                    current_anim.poses.append(current_pose)
                current_frame = None

                dodge_front = False
                crit = False
                throwing_axe = False
                shield_toss = False
                loop_end = False
            else:
                break  # Done with reading script

        elif line.startswith('C'):
            command_code = line[1:3]
            write_extra_frame = True  # Most commands occur at the same time as the last frame
            if command_code == '01':
                if throwing_axe:
                    parse_text('start_loop')
                    copy_frame(current_frame)
                    parse_text('end_loop')
                    copy_frame(current_frame, 8)
                elif loop_end:
                    parse_text('end_loop')
                    loop_end = False
                elif current_pose.nid == 'Miss':
                    copy_frame(current_frame)
                    parse_text('miss')
                    copy_frame(current_frame, 30)
                elif current_mode == 5 or current_mode == 6:  # Ranged
                    parse_text('start_loop')
                    copy_frame(current_frame, 4)
                    parse_text('end_loop')
                    copy_frame(current_frame, 4)
                elif 'Dodge' in current_pose.nid:
                    # There are always 31 frames in a dodge
                    counter = 0
                    for command in current_pose.timeline:
                        if command.tag == 'frame':
                            counter += command.value[0]
                    copy_frame(current_frame, 31 - counter)
                elif current_mode in (1, 2, 3, 4):  # Hit or Crit
                    wait_for_hit(current_frame)
                    if shield_toss:
                        parse_text('end_child_loop')
                        shield_toss = False
                    else:
                        copy_frame(current_frame, 4)
                elif current_mode in (9, 10, 11):  # Stand??
                    copy_frame(current_frame, 3)
                write_extra_frame = False
            elif command_code == '02':  # Normally marks a dodge animation, but doesn't matter in LT script
                write_extra_frame = False
            elif command_code == '03':
                begin = True
            elif command_code == '04':  # Normally prepares some code for returning to stand
                write_extra_frame = False
            elif command_code == '05':  # Start spell
                if weapon_type == 'Lance':
                    parse_text('spell;Javelin')
                elif weapon_type in ('Axe', 'Handaxe'):
                    parse_text('spell;ThrowingAxe')
                elif weapon_type == 'Bow':
                    parse_text('spell;Arrow')
                else:
                    parse_text('spell')
                write_extra_frame = False
            elif command_code == '06':  # Normally starts enemy turn, but that doesn't happen in LT script
                write_extra_frame = False 
            elif command_code == '07':
                begin = True
            elif command_code in ('08', '09', '0A', '0B', '0C'):  # Start crit
                parse_text('enemy_flash_white;8')
                if current_frame:
                    copy_frame(current_frame)
                parse_text('foreground_blend;2;255,255,255')
                crit = True
                start_hit = True
                write_extra_frame = False
            elif command_code == '0D':  # End
                if current_frame:
                    copy_frame(current_frame)
                write_extra_frame = False
            elif command_code == '0E':  # Dodge Start
                write_extra_frame = False
            elif command_code == '13':  # Throwing Axe
                if current_frame:
                    parse_text('start_loop')
                    copy_frame(current_frame)
                    parse_text('end_loop')
                throwing_axe = True
            elif command_code == '14':
                parse_text('screen_shake')
            elif command_code == '15':
                parse_text('platform_shake')
            elif command_code == '18':
                dodge_front = True
                write_extra_frame = False
            elif command_code == '1A':  # Start hit
                parse_text('enemy_flash_white;8')
                if current_frame:
                    copy_frame(current_frame)
                parse_text('screen_flash_white;4')
                crit = False
                start_hit = True
            elif command_code in ('1F', '20', '21'):  # Actual hit
                write_extra_frame = False
            # Sounds and other effects
            elif command_code == '19':
                parse_text('sound;Bow')
            elif command_code == '1B':
                parse_text('sound;Foot Step')
            elif command_code == '1C':
                parse_text('sound;Horse Step 1')
            elif command_code == '1D':
                parse_text('sound;Horse Step 3')
            elif command_code == '1E':
                parse_text('sound;Horse Step 2')
            elif command_code == '22':
                parse_text('sound;Weapon Pull')
            elif command_code == '23':
                parse_text('sound;Weapon Push')
            elif command_code == '24':
                parse_text('sound;Weapon Swing')
            elif command_code == '25':
                parse_text('sound;Heavy Wing Flap')
            elif command_code in ('26', '27'):
                parse_text('effect;ShieldToss')
                shield_toss = True
            elif command_code == '28':
                parse_text('sound;ShamanRune')
            elif command_code == '28':
                parse_text('sound;ArmorShift')
            elif command_code == '2E':
                parse_text('sound;MageInit')
                print("Change MageInit effect to SageInit effect if working with Sage animations")
            elif command_code == '2F':
                parse_text('sound;MageCrit')
                print("Change MageCrit effect to SageCrit effect if working with Sage animations")
            elif command_code == '30':
                parse_text('effect;DirtKick')
            elif command_code == '33':
                parse_text('sound;Battle Cry')
            elif command_code == '34':
                parse_text('sound;Step Back 1')
            elif command_code == '35':
                parse_text('sound;Long Wing Flap')
            elif command_code == '36':
                parse_text('sound;Unsheathe')
            elif command_code == '37':
                parse_text('sound;Sheathe')
            elif command_code == '38':
                parse_text('sound;Heavy Spear Spin')
            elif command_code == '3A':
                parse_text('sound;RefreshDance')
            elif command_code == '3B':
                parse_text('sound;RefreshFlute')
            elif command_code == '3C':
                parse_text('sound;Sword Whoosh')
            elif command_code == '41':
                parse_text('sound;Axe Pull')
            elif command_code == '42':
                parse_text('sound;Axe Push')
            elif command_code == '43':
                parse_text('sound;Weapon Click')
            elif command_code == '44':
                parse_text('sound;Weapon Shine')
            elif command_code == '45':
                parse_text('sound;Neigh')
            elif command_code == '47':
                cape_animation()
            elif command_code == '49':
                parse_text('sound;SageRune')
            elif command_code == '4B':
                parse_text('sound;MonkRune')
            elif command_code == '4F':
                parse_text('sound;DruidCrit')
            elif command_code == '51':
                parse_text('screen_flash_white;4')
            elif command_code == '5A':
                parse_text('sound;MautheDoogGrowl')
            elif command_code == '5B':
                parse_text('sound;MautheDoogBark')
            elif command_code == '5C':
                parse_text('sound;MautheDoogHowl')
            elif command_code == '5D':
                parse_text('sound;MautheDoogWalk')
            elif command_code == '79':
                parse_text('sound;StrategistRune')
            elif command_code == '7A':
                parse_text('sound;StrategistCrit')
            elif command_code == '7B':
                parse_text('sound;ManaketeRoar')
            else:
                print("Unknown Command Code: C%s" % command_code)

            if write_extra_frame and current_frame:
                current_frame.increment_frame_count()

        elif line.startswith('~~~'):
            pass

        elif line == 'L':
            parse_text('start_loop')
            loop_end = True

        elif line.startswith('S'):
            print('Cannot parse "%s"! Skipping over this line...' % line)

        else:  # Frame
            try:
                num_frames, _, png_name = line.split()
            except ValueError:
                print('Cannot parse "%s"! Skipping over this line...' % line)
                continue
            num_frames = int(num_frames)
            name = png_name[:-4]
            if name not in pixmaps:
                print("%s frame not in pixmaps" % name)
            if begin:
                num_frames = 6
                begin = False

            def parse_frame(num_frames, name):
                if dodge_front:
                    parse_text('of;%d;%s' % (num_frames, name))
                elif name + '_under' in pixmaps:
                    parse_text('f;%d;%s;%s' % (num_frames, name, name + '_under'))
                else:
                    parse_text('f;%d;%s' % (num_frames, name))

            if start_hit:
                if crit:
                    parse_text('start_hit')
                    parse_frame(2, name)
                    parse_text('crit_spark')
                else:
                    parse_frame(num_frames + 2, name)
                    parse_text('hit_spark')
                    parse_text('start_hit')
                start_hit = False
            else:
                parse_frame(num_frames, name)

    return melee_weapon_anim, ranged_weapon_anim
