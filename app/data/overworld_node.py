from collections import OrderedDict

from app.utilities.data import Data, Prefab
from app.data.level_units import UnitGroup
from app.resources.map_icons import MapIconCatalog

class OverworldNodePrefab(Prefab):
    def __init__(self, nid, name, pos, icon=MapIconCatalog.DEFAULT()):
        self.nid = nid
        self.name = name
        self.pos = pos             # tuple of location pair
        self.icon = icon           # icon nid (see map_icons.json for a manifest)
        self.level = None          # level associated

    def save_attr(self, name, value):
        value = super().save_attr(name, value)
        return value

    def restore_attr(self, name, value):
        value = super().restore_attr(name, value)
        if(name == 'pos'):
            value = tuple(value)
        return value

    @classmethod
    def default(cls):
        return cls('0', 'Frelia Castle', (0, 0))

class OverworldNodeCatalog(Data[OverworldNodePrefab]):
    datatype = OverworldNodePrefab
