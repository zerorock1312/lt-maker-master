import os
import shutil

from app.resources.base_catalog import ManifestCatalog
from app.resources import combat_commands
from app.utilities.data import Data

required_poses = ('Stand', 'Hit', 'Miss', 'Dodge')
other_poses = ('RangedStand', 'RangedDodge', 'Critical')

class Pose():
    def __init__(self, nid):
        self.nid = nid
        self.timeline = []

    def save(self):
        return (self.nid, [command.save() for command in self.timeline])

    @classmethod
    def restore(cls, s_tuple):
        self = cls(s_tuple[0])
        for command_save in s_tuple[1]:
            nid, value = command_save
            command = combat_commands.get_command(nid)
            command.value = value
            self.timeline.append(command)
        return self

class Frame():
    def __init__(self, nid, rect, offset, pixmap=None, image=None):
        self.nid = nid

        self.rect = rect
        self.offset = offset

        self.pixmap = pixmap
        self.image = image

    def save(self):
        return (self.nid, self.rect, self.offset)

    @classmethod
    def restore(cls, s_tuple):
        self = cls(*s_tuple)
        return self

class WeaponAnimation():
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.full_path = full_path
        self.poses = Data()
        self.frames = Data()
        self.weapon_type = None
        self.weapon_kind = None

        self.pixmap = None
        self.image = None

    def set_full_path(self, full_path):
        self.full_path = full_path

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['poses'] = [pose.save() for pose in self.poses]
        s_dict['frames'] = [frame.save() for frame in self.frames]
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        for frame_save in s_dict['frames']:
            self.frames.append(Frame.restore(frame_save))
        for pose_save in s_dict['poses']:
            self.poses.append(Pose.restore(pose_save))
        return self

class CombatAnimation():
    def __init__(self, nid):
        self.nid = nid
        self.weapon_anims = Data()
        self.palettes = []  # Palette name -> Palette nid

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['weapon_anims'] = [weapon_anim.save() for weapon_anim in self.weapon_anims]
        s_dict['palettes'] = self.palettes[:]
        return s_dict 

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        self.palettes = []
        for palette_name, palette_nid in s_dict['palettes'][:]:
            self.palettes.append([palette_name, palette_nid])
        for weapon_anim_save in s_dict['weapon_anims']:
            self.weapon_anims.append(WeaponAnimation.restore(weapon_anim_save))
        return self

class CombatCatalog(ManifestCatalog):
    manifest = 'combat_anims.json'
    title = 'Combat Animations'

    def load(self, loc):
        combat_dict = self.read_manifest(os.path.join(loc, self.manifest))
        for s_dict in combat_dict:
            new_combat_anim = CombatAnimation.restore(s_dict)
            for weapon_anim in new_combat_anim.weapon_anims:
                short_path = "%s-%s.png" % (new_combat_anim.nid, weapon_anim.nid)
                weapon_anim.set_full_path(os.path.join(loc, short_path))
            self.append(new_combat_anim)

    def save(self, loc):
        for combat_anim in self:
            for weapon_anim in combat_anim.weapon_anims:
                short_path = "%s-%s.png" % (combat_anim.nid, weapon_anim.nid)
                new_full_path = os.path.join(loc, short_path)
                if not weapon_anim.full_path:
                    weapon_anim.pixmap.save(new_full_path, "PNG")
                elif os.path.abspath(weapon_anim.full_path) != os.path.abspath(new_full_path):
                    self.make_copy(weapon_anim.full_path, new_full_path)
                    weapon_anim.set_full_path(new_full_path)
        self.dump(loc)

    def clean(self, loc):
        pass  # TODO implement

class CombatEffectCatalog(ManifestCatalog):
    manifest = 'combat_effects.json'
    title = 'Combat Effects'

    def load(self, loc):
        effect_dict = self.read_manifest(os.path.join(loc, self.manifest))
        for s_dict in effect_dict:
            new_effect_anim = WeaponAnimation.restore(s_dict)
            full_path = os.path.join(loc, new_effect_anim.nid + '.png')
            new_effect_anim.set_full_path(os.path.join(loc, full_path))
            self.append(new_effect_anim)

    def save(self, loc):
        for effect_anim in self:
            full_path = os.path.join(loc, effect_anim.nid)
            if os.path.abspath(effect_anim.full_path) != os.path.abspath(full_path):
                shutil.copy(effect_anim.full_path, full_path)
                effect_anim.set_full_path(full_path)
        self.dump(loc)

    def clean(self, loc):
        pass  # TODO implement
