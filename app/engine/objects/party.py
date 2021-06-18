from app.utilities.data import Prefab

from app.engine.game_state import game

class PartyObject(Prefab):
    def __init__(self, nid, name, leader_nid, units=None, money=0, convoy=None, bexp=0):
        self.nid = nid
        self.name = name
        self.leader_nid = leader_nid
        self.units = units or []  # Unit nids
        self.money = money
        if convoy:
            self.convoy = [game.get_item(item_uid) for item_uid in convoy]
            self.convoy = [i for i in self.convoy if i]
        else:
            self.convoy = []
        self.bexp = bexp

    def save(self):
        return {'nid': self.nid, 
                'name': self.name, 
                'leader_nid': self.leader_nid,
                'units': self.units,
                'money': self.money,
                'convoy': [item.uid for item in self.convoy],
                'bexp': self.bexp}

    @classmethod
    def restore(cls, s_dict):
        party = cls(s_dict['nid'], s_dict['name'], s_dict['leader_nid'], s_dict['units'], s_dict['money'], s_dict['convoy'], s_dict['bexp'])
        return party
