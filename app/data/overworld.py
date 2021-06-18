from ast import literal_eval as make_tuple
from collections import OrderedDict
from dataclasses import dataclass

from app.utilities.data import Data, Prefab
from app.data.level_units import UnitGroup
from app.data.overworld_node import OverworldNodePrefab, OverworldNodeCatalog

class OverworldPrefab(Prefab):
    def __init__(self, nid, name):
        self.nid = nid
        self.name = name
        self.tilemap = None               # Tilemap Nid - background\
        self.music = None                 # Music Nid
        self.overworld_nodes = OverworldNodeCatalog()
        self.map_paths = {}               # dict that maps string points_to_key(start_point, end_point) to a 
                                          # list of coords that define the road between those two nodes
                                          # (See points_to_key function below)

    def save_attr(self, name, value):
        if name == 'overworld_nodes':
            value = [node.save() for node in value]
        else:
            value = super().save_attr(name, value)
        return value

    def restore_attr(self, name, value):
        if name == 'overworld_nodes':
            value = Data([OverworldNodePrefab.restore(map_node) for map_node in value])
        else:
            value = super().restore_attr(name, value)
        return value

    @classmethod
    def default(cls):
        return cls('0', 'Magvel')
    
    @classmethod
    def points_to_key(cls, p1, p2):
        """Given two points, turns them into a string key

        Args:
            p1 Tuple(int, int): point 1 (in this context, usually starting point of a road)
            p2 Tuple(int, int): point 2 (usually end point)
        
        Return:
            A string key corresponding to these tuples
        """
        return str(p1) + '-' + str(p2)
    
    @classmethod
    def string_to_tuples(cls, tstring):
        """Given a string of format '(a, b)-(c, d)', converts them into two tuples:
        the counterpoint of the function above.
        Args:
            tstring (str): A string in the format '(a, b)-(c, d)'
        Return:
            A list of two tuples [(a,b), (c,d)]
        """
        spl = tstring.split('-')
        return [make_tuple(spl[0]), make_tuple(spl[1])]

class OverworldCatalog(Data[OverworldPrefab]):
    datatype = OverworldPrefab