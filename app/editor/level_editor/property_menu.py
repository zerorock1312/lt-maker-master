from functools import partial

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, \
    QWidget, QPushButton, QMessageBox, QLabel, QCheckBox
from PyQt5.QtCore import Qt

from app.data.database import DB

from app.extensions.custom_gui import SimpleDialog, PropertyBox, QHLine, PropertyCheckBox
from app.editor.custom_widgets import UnitBox, PartyBox
from app.utilities import str_utils
from app.editor.unit_editor import unit_tab
from app.editor.sound_editor import sound_tab
from app.editor.tile_editor import tile_tab

from app.editor import timer


class MusicDialog(SimpleDialog):
    def __init__(self, current):
        super().__init__()
        self.setWindowTitle("Level Music")
        self.current = current

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.boxes = {}
        for idx, key in enumerate(self.current.music.keys()):
            title = key.replace('_', ' ').title()
            box = PropertyBox(title, QLineEdit, self)
            box.edit.setReadOnly(True)
            box.add_button(QPushButton('...'))
            box.button.setMaximumWidth(40)
            box.button.clicked.connect(
                partial(self.access_music_resources, key))

            layout.addWidget(box)
            self.boxes[key] = box

        self.set_current(self.current)
        self.setMinimumWidth(300)

    def set_current(self, current):
        self.current = current
        for key, value in self.current.music.items():
            if value:
                self.boxes[key].edit.setText(value)

    def access_music_resources(self, key):
        res, ok = sound_tab.get_music()
        if ok and res:
            nid = res[0].nid
            self.current.music[key] = nid
            self.boxes[key].edit.setText(nid)


class PropertiesMenu(QWidget):
    def __init__(self, state_manager):
        super().__init__()

        self.state_manager = state_manager

        self.setStyleSheet("font: 10pt;")

        form = QVBoxLayout(self)
        form.setAlignment(Qt.AlignTop)

        self.nid_box = PropertyBox("Level ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        form.addWidget(self.nid_box)

        self.title_box = PropertyBox("Level Title", QLineEdit, self)
        self.title_box.edit.textChanged.connect(self.title_changed)
        form.addWidget(self.title_box)

        self.party_box = PartyBox(self)
        self.party_box.edit.activated.connect(self.party_changed)
        form.addWidget(self.party_box)

        self.music_button = QPushButton("Edit Level's Music...", self)
        self.music_button.clicked.connect(self.edit_music)
        form.addWidget(self.music_button)

        self.currently_playing = None
        self.currently_playing_label = QLabel("")
        form.addWidget(self.currently_playing_label)

        form.addWidget(QHLine())

        self.quick_display = PropertyBox("Objective Display", QLineEdit, self)
        self.quick_display.edit.editingFinished.connect(
            lambda: self.set_objective('simple'))
        form.addWidget(self.quick_display)

        self.win_condition = PropertyBox("Win Condition", QLineEdit, self)
        self.win_condition.edit.editingFinished.connect(
            lambda: self.set_objective('win'))
        form.addWidget(self.win_condition)

        self.loss_condition = PropertyBox("Loss Condition", QLineEdit, self)
        self.loss_condition.edit.editingFinished.connect(
            lambda: self.set_objective('loss'))
        form.addWidget(self.loss_condition)

        form.addWidget(QHLine())

        self.map_box = QPushButton("Select Tilemap...")
        self.map_box.clicked.connect(self.select_tilemap)
        form.addWidget(self.map_box)

        # Free roam stuff
        self.free_roam_box = PropertyCheckBox("Free Roam?", QCheckBox, self)
        self.free_roam_box.edit.stateChanged.connect(self.free_roam_changed)
        form.addWidget(self.free_roam_box)

        self.unit_box = UnitBox(self, button=True, title="Roaming Unit")
        self.unit_box.edit.currentIndexChanged.connect(self.unit_changed)
        self.unit_box.button.clicked.connect(self.access_units)
        form.addWidget(self.unit_box)

        self.set_current(self.state_manager.state.selected_level)
        self.state_manager.subscribe_to_key(
            PropertiesMenu.__name__, 'selected_level', self.set_current)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        self.party_box.model.layoutChanged.emit()

    def set_current(self, level_nid):
        self.current = DB.levels.get(level_nid)
        current = self.current
        if not current:
            return

        self.title_box.edit.setText(current.name)
        self.nid_box.edit.setText(current.nid)
        if current.party in DB.parties.keys():
            idx = DB.parties.index(current.party)
            self.party_box.edit.setCurrentIndex(idx)
            self.party_changed()
        else:
            self.party_box.edit.setCurrentIndex(0)
            self.party_changed()

        # Handle roaming
        if DB.units:
            self.unit_box.model._data = DB.units
            self.unit_box.model.layoutChanged.emit()
        self.free_roam_box.edit.setChecked(bool(current.roam))
        if current.roam_unit:
            self.unit_box.edit.setValue(current.roam_unit)
        elif DB.units:
            self.unit_box.edit.setValue(DB.units[0].nid)
        if bool(current.roam):
            self.unit_box.show()
        else:
            self.unit_box.hide()
        
        self.quick_display.edit.setText(current.objective['simple'])
        self.win_condition.edit.setText(current.objective['win'])
        self.loss_condition.edit.setText(current.objective['loss'])

    def nid_changed(self, text):
        self.current.nid = text
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def nid_done_editing(self):
        other_nids = [
            level.nid for level in DB.levels if level is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(
                self, 'Warning', 'Level ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_int(
                self.current.nid, other_nids)
        self.on_nid_changed(DB.levels.find_key(
            self.current), self.current.nid)
        DB.levels.update_nid(self.current, self.current.nid)
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def on_nid_changed(self, old_nid, new_nid):
        for event in DB.events:
            if event.level_nid == old_nid:
                event.level_nid = new_nid

    def title_changed(self, text):
        self.current.name = text
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def party_changed(self):
        idx = self.party_box.edit.currentIndex()
        if idx >= 0:
            party = DB.parties[idx]
            self.current.party = party.nid

    def edit_music(self):
        dlg = MusicDialog(self.current)
        dlg.exec_()

    def set_objective(self, key):
        if key == 'simple':
            self.current.objective[key] = self.quick_display.edit.text()
        elif key == 'win':
            self.current.objective[key] = self.win_condition.edit.text()
        elif key == 'loss':
            self.current.objective[key] = self.loss_condition.edit.text()

    def select_tilemap(self):
        res, ok = tile_tab.get_tilemaps()
        if ok and res:
            nid = res.nid
            self.current.tilemap = nid
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def access_units(self):
        unit, ok = unit_tab.get(self.current.roam_unit)
        if unit and ok:
            self.current.roam_unit = unit.nid
            self.unit_box.edit.setValue(self.current.roam_unit)

    def free_roam_changed(self, state):
        self.current.roam = bool(state)
        if self.current.roam:
            self.unit_box.show()
        else:
            self.unit_box.hide()

    def unit_changed(self, idx):
        self.current.roam_unit = DB.units[idx].nid
        self.unit_box.edit.setValue(self.current.roam_unit)
