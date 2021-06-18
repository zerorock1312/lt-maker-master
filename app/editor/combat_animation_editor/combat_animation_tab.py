from app.resources.resources import RESOURCES

from app.editor.base_database_gui import DatabaseTab
from app.editor.combat_animation_editor.combat_animation_display import CombatAnimProperties
from app.editor.combat_animation_editor.palette_tab import PaletteDatabase
from app.editor.combat_animation_editor.combat_animation_model import CombatAnimModel
from app.extensions.custom_gui import ResourceListView
from app.editor.data_editor import MultiResourceEditor

class CombatAnimDisplay(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = RESOURCES.combat_anims
        title = "Combat Animation"
        right_frame = CombatAnimProperties
        collection_model = CombatAnimModel
        deletion_criteria = None

        dialog = cls(data, title, right_frame, deletion_criteria,
                     collection_model, parent, button_text="Add New %s...",
                     view_type=ResourceListView)
        return dialog

def get_full_editor():
    editor = MultiResourceEditor((CombatAnimDisplay, PaletteDatabase),
                                 ('combat_anims', 'combat_palettes'))
    editor.setWindowTitle("Combat Animation Editor")
    return editor
