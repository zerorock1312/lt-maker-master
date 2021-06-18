from app.utilities.data import Prefab

class DifficultyModeObject(Prefab):
    def __init__(self, nid, permadeath=False, growths='Fixed'):
        self.nid: str = nid
        self.permadeath: bool = permadeath
        self.growths: str = growths
        self.enemy_autolevels: int = 0
        self.enemy_truelevels: int = 0

    def save(self):
        return {'nid': self.nid, 
                'permadeath': self.permadeath, 
                'growths': self.growths,
                'enemy_autolevels': self.enemy_autolevels,
                'enemy_truelevels': self.enemy_truelevels,
                }

    @classmethod
    def restore(cls, s_dict):
        difficulty_mode = cls(s_dict['nid'], s_dict['permadeath'], s_dict['growths'])
        difficulty_mode.enemy_autolevels = s_dict.get('enemy_autolevels', 0)
        difficulty_mode.enemy_truelevels = s_dict.get('enemy_truelevels', 0)
        return difficulty_mode
