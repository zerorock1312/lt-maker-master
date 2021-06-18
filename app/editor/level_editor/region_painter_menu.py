from PyQt5.QtWidgets import QPushButton, QLineEdit, \
    QWidget, QVBoxLayout, QMessageBox, QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor, QPixmap

from app.data.database import DB

from app.utilities import utils, str_utils
from app.utilities.data import Data

from app.extensions.custom_gui import PropertyBox, PropertyCheckBox, ComboBox, RightClickListView
from app.editor.base_database_gui import DragDropCollectionModel
from app.editor.custom_widgets import SkillBox
from app.events import regions

from app.editor import timer


class RegionMenu(QWidget):
    def __init__(self, state_manager, map_view):
        super().__init__()
        self.state_manager = state_manager
        self.map_view = map_view
        self.current_level = DB.levels.get(
            self.state_manager.state.selected_level)
        if self.current_level:
            self._data = self.current_level.regions
        else:
            self._data = Data()

        grid = QVBoxLayout()
        self.setLayout(grid)

        def duplicate_func(model, index):
            return False

        self.view = RightClickListView(
            (None, None, None), parent=self)
        self.view.currentChanged = self.on_item_changed

        self.model = RegionModel(self._data, self)
        self.view.setModel(self.model)

        grid.addWidget(self.view)

        self.create_button = QPushButton("Create Region...")
        self.create_button.clicked.connect(self.create_region)
        grid.addWidget(self.create_button)

        self.modify_region_widget = ModifyRegionWidget(self._data, self)
        grid.addWidget(self.modify_region_widget)

        if not len(self._data):
            self.modify_region_widget.setEnabled(False)

        self.last_touched_region = None
        self.display = self.modify_region_widget

        self.state_manager.subscribe_to_key(
            RegionMenu.__name__, 'selected_level', self.set_current_level)
        self.state_manager.subscribe_to_key(
            RegionMenu.__name__, 'ui_refresh_signal', self._refresh_view)
        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        status_box = self.modify_region_widget.status_box
        status_box.model.layoutChanged.emit()

    def _refresh_view(self, _=None):
        self.model.layoutChanged.emit()

    def update_list(self):
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def set_current_level(self, level_nid):
        level = DB.levels.get(level_nid)
        self.current_level = level
        self._data = self.current_level.regions
        self.model._data = self._data
        self.model.update()
        self.modify_region_widget._data = self._data
        if len(self._data):
            self.modify_region_widget.setEnabled(True)
            reg = self._data[0]
            if reg.position:
                self.map_view.center_on_pos(reg.center)
            self.modify_region_widget.set_current(reg)
        else:
            self.modify_region_widget.setEnabled(False)

    def select(self, idx):
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)

    def deselect(self):
        self.view.clearSelection()

    def on_item_changed(self, curr, prev):
        if self._data:
            reg = self._data[curr.row()]
            if reg.position:
                self.map_view.center_on_pos(reg.center)
            self.modify_region_widget.set_current(reg)

    def get_current(self):
        for index in self.view.selectionModel().selectedIndexes():
            idx = index.row()
            if len(self._data) > 0 and idx < len(self._data):
                return self._data[idx]
        return None

    def create_region(self, example=None):
        nid = str_utils.get_next_name('New Region', self._data.keys())
        created_region = regions.Region(nid)
        self._data.append(created_region)
        self.modify_region_widget.setEnabled(True)
        self.model.update()
        # Select the region
        idx = self._data.index(created_region.nid)
        index = self.model.index(idx)
        self.view.setCurrentIndex(index)
        self.state_manager.change_and_broadcast('ui_refresh_signal', None)
        return created_region


class RegionModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            reg = self._data[index.row()]
            text = reg.nid + ': ' + reg.region_type
            if reg.region_type == 'status':
                if reg.sub_nid:
                    text += ' ' + reg.sub_nid
            elif reg.region_type == 'event':
                if reg.sub_nid:
                    text += ' ' + reg.sub_nid
                if reg.condition:
                    text += '\n' + reg.condition
            return text
        elif role == Qt.DecorationRole:
            reg = self._data[index.row()]
            color = utils.hash_to_color(utils.strhash(reg.nid))
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(*color))
            return QIcon(pixmap)
        return None

    def new(self, idx):
        ok = self.window.create_region()
        if ok:
            self._data.move_index(len(self._data) - 1, idx + 1)
            self.layoutChanged.emit()

    def duplicate(self, idx):
        view = self.window.view
        obj = self._data[idx]
        new_nid = str_utils.get_next_name(obj.nid, self._data.keys())
        serialized_obj = obj.save()
        new_obj = regions.Region.restore(serialized_obj)
        new_obj.nid = new_nid
        self._data.insert(idx + 1, new_obj)
        self.layoutChanged.emit()
        new_index = self.index(idx + 1)
        view.setCurrentIndex(new_index)
        return new_index

class ModifyRegionWidget(QWidget):
    def __init__(self, data, parent=None, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = data

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.current = current

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        layout.addWidget(self.nid_box)

        self.region_type_box = PropertyBox("Region Type", ComboBox, self)
        self.region_type_box.edit.addItems(regions.region_types)
        # self.region_type_box.edit.setValue(self.current.region_type)
        self.region_type_box.edit.currentIndexChanged.connect(
            self.region_type_changed)
        layout.addWidget(self.region_type_box)

        self.sub_nid_box = PropertyBox("Event Name", QLineEdit, self)
        # if self.current.sub_nid and self.current.region_type == 'Event':
        #     self.sub_nid_box.edit.setText(self.current.sub_nid)
        self.sub_nid_box.edit.textChanged.connect(self.sub_nid_changed)
        layout.addWidget(self.sub_nid_box)

        self.condition_box = PropertyBox("Condition", QLineEdit, self)
        # self.condition_box.edit.setText(self.current.condition)
        self.condition_box.edit.textChanged.connect(self.condition_changed)
        layout.addWidget(self.condition_box)

        self.only_once_box = PropertyCheckBox("Only once?", QCheckBox, self)
        self.only_once_box.edit.stateChanged.connect(self.only_once_changed)
        layout.addWidget(self.only_once_box)

        self.status_box = SkillBox(self)
        # if self.current.sub_nid and self.current.region_type == 'Status':
        #     self.status_box.edit.setText(self.current.sub_nid)
        self.status_box.edit.currentIndexChanged.connect(self.status_changed)
        layout.addWidget(self.status_box)

        self.sub_nid_box.hide()
        self.condition_box.hide()
        self.only_once_box.hide()
        self.status_box.hide()

    def nid_changed(self, text):
        if self.current:
            self.current.nid = text
            self.window.update_list()

    def nid_done_editing(self):
        if not self.current:
            return
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values()
                      if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning',
                                'Region ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_name(
                self.current.nid, other_nids)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def region_type_changed(self, index):
        if not self.current:
            return
        self.current.region_type = self.region_type_box.edit.currentText().lower()
        if self.current.region_type in ('normal', 'formation'):
            self.sub_nid_box.hide()
            self.condition_box.hide()
            self.only_once_box.hide()
            self.status_box.hide()
        elif self.current.region_type == 'status':
            self.sub_nid_box.hide()
            self.condition_box.hide()
            self.only_once_box.hide()
            self.status_box.show()
        elif self.current.region_type == 'event':
            self.sub_nid_box.show()
            self.condition_box.show()
            self.only_once_box.show()
            self.status_box.hide()

    def sub_nid_changed(self, text):
        self.current.sub_nid = text
        self.window.update_list()

    def condition_changed(self, text):
        self.current.condition = text
        self.window.update_list()

    def only_once_changed(self, state):
        self.current.only_once = bool(state)

    def status_changed(self, index):
        self.current.sub_nid = self.status_box.edit.currentText()
        self.window.update_list()

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.region_type_box.edit.setValue(current.region_type)
        self.condition_box.edit.setText(current.condition)
        self.only_once_box.edit.setChecked(bool(current.only_once))
        if current.region_type == 'status':
            self.status_box.edit.setValue(current.sub_nid)
        elif current.region_type == 'event':
            self.sub_nid_box.edit.setText(current.sub_nid)
        else:
            self.sub_nid_box.edit.setText('')
