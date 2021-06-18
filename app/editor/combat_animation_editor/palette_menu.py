from PyQt5.QtWidgets import QWidget, QButtonGroup, QMenu, \
    QListWidgetItem, QRadioButton, QHBoxLayout, QListWidget, QAction, \
    QLineEdit
from PyQt5.QtCore import Qt

from app.utilities import str_utils
from app.resources.resources import RESOURCES
from app.extensions.custom_gui import ComboBox
from app.editor.combat_animation_editor.palette_model import PaletteModel

class PaletteWidget(QWidget):
    def __init__(self, idx, combat_anim, parent=None):
        super().__init__(parent)
        self.window = parent
        self.idx = idx
        self.current_combat_anim = combat_anim

        layout = QHBoxLayout()
        self.setLayout(layout)

        radio_button = QRadioButton()
        self.window.radio_button_group.addButton(radio_button, self.idx)
        radio_button.clicked.connect(lambda: self.window.set_palette(self.idx))

        self.name_label = QLineEdit(self)
        palette_name, palette_nid = self.current_combat_anim.palettes[self.idx]
        self.name_label.setText(palette_name)

        self.palette_box = ComboBox(self)
        model = PaletteModel(RESOURCES.combat_palettes, self)
        self.palette_box.setModel(model)
        self.palette_box.view().setUniformItemSizes(True)
        self.palette_box.setValue(palette_nid)

        layout.addWidget(radio_button)
        layout.addWidget(self.name_label)
        layout.addWidget(self.palette_box)

class PaletteMenu(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent
        self.uniformItemSizes = True

        self.radio_button_group = QButtonGroup()
        self.combat_anim = None
        self.palette_widgets = []

        self.current_idx = 0

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customMenuRequested)

    def customMenuRequested(self, pos):
        index = self.indexAt(pos)
        menu = QMenu(self)

        new_action = QAction("New", self, triggered=lambda: self.new(index))
        menu.addAction(new_action)
        if index.isValid():
            delete_action = QAction("Delete", self, triggered=lambda: self.delete(index))
            menu.addAction(delete_action)
            if len(self.palette_widgets) <= 1:  # Can't delete when only one palette left
                delete_action.setEnabled(False)

        menu.popup(self.viewport().mapToGlobal(pos))

    def set_current(self, combat_anim):
        self.clear()
        self.combat_anim = combat_anim

        for idx, palette in enumerate(combat_anim.palettes):
            palette_name, palette_nid = palette

            item = QListWidgetItem(self)
            pf = PaletteWidget(idx, combat_anim, self)
            self.palette_widgets.append(pf)
            item.setSizeHint(pf.minimumSizeHint())
            self.addItem(item)
            self.setItemWidget(item, pf)
            self.setMinimumWidth(self.sizeHintForColumn(0))

        if self.combat_anim.palettes:
            self.set_palette(0)

    def set_palette(self, idx):
        self.current_idx = idx
        self.radio_button_group.button(idx).setChecked(True)

    def get_palette(self):
        return self.combat_anim.palettes[self.current_idx][1]

    def get_palette_widget(self):
        return self.palette_widgets[self.current_idx]

    def clear(self):
        # Clear out old radio buttons
        buttons = self.radio_button_group.buttons()
        for button in buttons[:]:
            self.radio_button_group.removeButton(button)

        # for idx, l in reversed(list(enumerate(self.palette_widgets))):
        #     self.takeItem(idx)
        #     l.deleteLater()
        super().clear()
        self.palette_widgets.clear()
        self.current_idx = 0

    def new(self, index):
        palette_data = self.combat_anim.palettes
        new_name = str_utils.get_next_name("New", [p[0] for p in palette_data])
        palette_data.insert(index.row() + 1, [new_name, RESOURCES.combat_palettes[0]])

        self.set_current(self.combat_anim)
        self.set_palette(self.current_idx)

    def delete(self, index):
        palette_data = self.combat_anim.palettes
        palette_data.pop(index.row())

        self.set_current(self.combat_anim)
        self.set_palette(self.current_idx)
