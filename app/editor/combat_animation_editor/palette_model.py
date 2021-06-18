from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon

from app.resources.resources import RESOURCES

from app.utilities.data import Data

from app.resources.combat_palettes import Palette
from app.extensions.custom_gui import DeletionDialog
from app.editor.base_database_gui import DragDropCollectionModel
from app.utilities import str_utils

def get_palette_pixmap(palette) -> QPixmap:
    # TODO
    return QPixmap()

class PaletteModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            palette = self._data[index.row()]
            text = palette.nid
            return text
        elif role == Qt.DecorationRole:
            palette = self._data[index.row()]
            pixmap = get_palette_pixmap(palette)
            if pixmap:
                return QIcon(pixmap)
        return None

    def create_new(self):
        nids = RESOURCES.combat_palettes.keys()
        nid = str_utils.get_next_name('New Palette', nids)
        new_palette = Palette(nid)
        RESOURCES.combat_palettes.append(new_palette)
        return new_palette

    def delete(self, idx):
        # Delete watchers
        res = self._data[idx]
        nid = res.nid
        affected_combat_anims = [anim for anim in RESOURCES.combat_anims if nid in anim.palettes]
        if affected_combat_anims:
            affected = Data(affected_combat_anims)
            from app.editor.combat_animation_editor.combat_animation_model import CombatAnimationModel
            model = CombatAnimationModel
            msg = "Deleting Palette <b>%s</b> would affect these combat animations."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        super().delete(idx)

    def on_nid_changed(self, old_nid, new_nid):
        # What uses combat palettes
        for combat_anim in RESOURCES.combat_anims:
            if old_nid in combat_anim.palettes:
                idx = combat_anim.palettes.index(old_nid)
                combat_anim.palettes.remove(old_nid)
                combat_anim.palettes.insert(idx, new_nid)
