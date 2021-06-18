from PyQt5.QtWidgets import QWidget, QGridLayout, QLineEdit, \
    QMessageBox, QSpinBox, QHBoxLayout, QPushButton, QDialog, QSplitter, \
    QVBoxLayout, QTableView, QStyledItemDelegate, QTextEdit
from PyQt5.QtGui import QIcon, QFontMetrics
from PyQt5.QtCore import Qt, QItemSelection, QItemSelectionModel

from app.utilities import str_utils

from app.data.database import DB

from app.extensions.custom_gui import PropertyBox, QHLine, ComboBox
from app.extensions.multi_select_combo_box import MultiSelectComboBox
from app.extensions.list_models import VirtualListModel, ReverseDoubleListModel
from app.extensions.list_widgets import BasicSingleListWidget, AppendMultiListWidget

from app.editor.custom_widgets import ClassBox, AffinityBox
from app.editor.tag_widget import TagDialog
from app.editor.stat_widget import StatListWidget, StatAverageDialog, UnitStatAveragesModel
from app.editor.learned_skill_delegate import LearnedSkillDelegate
from app.editor.unit_notes_delegate import UnitNotesDelegate, UnitNotesDoubleListModel
from app.editor.item_list_widget import ItemListWidget
from app.editor.weapon_editor import weapon_model
from app.editor.icons import UnitPortrait

class WexpModel(VirtualListModel):
    def __init__(self, columns, data, parent=None):
        super().__init__(parent)
        self.window = parent
        self._columns = self._headers = columns
        self._data: dict = data

    def rowCount(self, parent=None):
        return 1

    def columnCount(self, parent=None):
        return len(self._headers)

    def set_new_data(self, wexp_gain: dict):
        self._data: dict = wexp_gain
        self.layoutChanged.emit()

    def update_column_header(self, columns):
        self._columns = self._headers = columns

    def headerData(self, idx, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            # return self._columns[idx].nid
            return None
        elif role == Qt.DecorationRole and orientation == Qt.Horizontal:
            weapon = self._columns[idx]
            pixmap = weapon_model.get_pixmap(weapon)
            if pixmap:
                return QIcon(pixmap)
        return None

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            weapon = self._columns[index.column()]
            wexp_gain = self._data.get(weapon.nid)
            if wexp_gain:
                return wexp_gain.wexp_gain
            else:
                return 0
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight + Qt.AlignVCenter

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        weapon = self._columns[index.column()]
        wexp_gain = self._data.get(weapon.nid)
        if not wexp_gain:
            self._data[weapon.nid] = DB.weapons.default()
            wexp_gain = self._data[weapon.nid]
        if value in DB.weapon_ranks.keys():
            value = DB.weapon_ranks.get(value).requirement
        elif str_utils.is_int(value):
            value = int(value)
        else:
            value = 0
        wexp_gain.wexp_gain = value
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        basic_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemNeverHasChildren | Qt.ItemIsEditable
        return basic_flags

class HorizWeaponListWidget(BasicSingleListWidget):
    def __init__(self, data, title, dlgate, parent=None):
        QWidget.__init__(self, parent)
        self.initiate(data, parent)

        self.model = WexpModel(DB.weapons, data, self)
        self.view = QTableView(self)
        self.view.setModel(self.model)
        self.view.setFixedHeight(60)
        delegate = dlgate(self.view)
        self.view.setItemDelegate(delegate)

        self.placement(data, title)

        for col in range(len(DB.weapons)):
            self.view.resizeColumnToContents(col)
            self.view.setColumnWidth(col, 20)

class HorizWeaponListDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, idnex):
        editor = ComboBox(parent)
        editor.setEditable(True)
        editor.addItem('0')
        for rank in DB.weapon_ranks:
            editor.addItem(rank.rank)
        return editor

class UnitProperties(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.view = self.window.left_frame.view
        self.model = self.window.left_frame.model
        self._data = self.window._data
        self.current = None

        top_section = QHBoxLayout()

        main_section = QGridLayout()

        self.icon_edit = UnitPortrait(self)
        main_section.addWidget(self.icon_edit, 0, 0, 2, 1, Qt.AlignHCenter)
        # top_section.addWidget(self.icon_edit)

        # horiz_spacer = QSpacerItem(40, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        # top_section.addSpacerItem(horiz_spacer)

        # name_section = QVBoxLayout()

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        main_section.addWidget(self.nid_box, 0, 1)

        self.name_box = PropertyBox("Display Name", QLineEdit, self)
        self.name_box.edit.setMaxLength(13)
        self.name_box.edit.textChanged.connect(self.name_changed)
        main_section.addWidget(self.name_box, 0, 2)

        # top_section.addLayout(name_section)

        self.variant_box = PropertyBox("Animation Variant", QLineEdit, self)
        self.variant_box.edit.textChanged.connect(self.variant_changed)
        self.variant_box.edit.setPlaceholderText("No Variant")
        main_section.addWidget(self.variant_box, 1, 2)

        self.desc_box = PropertyBox("Description", QTextEdit, self)
        self.desc_box.edit.textChanged.connect(self.desc_changed)
        font_height = QFontMetrics(self.desc_box.edit.font())
        self.desc_box.edit.setFixedHeight(font_height.lineSpacing() * 3 + 20)
        main_section.addWidget(self.desc_box, 2, 0, 1, 3)

        self.level_box = PropertyBox("Level", QSpinBox, self)
        self.level_box.edit.setRange(1, 255)
        self.level_box.edit.setAlignment(Qt.AlignRight)
        self.level_box.edit.valueChanged.connect(self.level_changed)
        main_section.addWidget(self.level_box, 1, 1)

        self.class_box = ClassBox(self)
        self.class_box.edit.currentIndexChanged.connect(self.class_changed)
        main_section.addWidget(self.class_box, 3, 0)

        tag_section = QHBoxLayout()

        self.tag_box = PropertyBox("Personal Tags", MultiSelectComboBox, self)
        self.tag_box.edit.setPlaceholderText("No tag")
        self.tag_box.edit.addItems(DB.tags.keys())
        self.tag_box.edit.updated.connect(self.tags_changed)
        tag_section.addWidget(self.tag_box)

        self.tag_box.add_button(QPushButton('...'))
        self.tag_box.button.setMaximumWidth(40)
        self.tag_box.button.clicked.connect(self.access_tags)

        main_section.addLayout(tag_section, 3, 1, 1, 2)

        self.unit_stat_widget = StatListWidget(self.current, "Stats", reset_button=True, parent=self)
        self.unit_stat_widget.button.clicked.connect(self.display_averages)
        self.unit_stat_widget.reset_button.clicked.connect(self.reset_stats)
        self.unit_stat_widget.model.dataChanged.connect(self.stat_list_model_data_changed)
        self.unit_stat_widget.view.setFixedHeight(120)
        self.averages_dialog = None
        # self.unit_stat_widget.button.clicked.connect(self.access_stats)
        # Changing of stats done automatically by using model view framework within

        attrs = ("level", "skill_nid")
        self.personal_skill_widget = AppendMultiListWidget([], "Personal Skills", attrs, LearnedSkillDelegate, self, model=ReverseDoubleListModel)
        self.personal_skill_widget.view.setMaximumHeight(120)
        # Changing of Personal skills done automatically also
        # self.personal_skill_widget.activated.connect(self.learned_skills_changed)

        noteAttrs = ("Category", "Entries")
        self.unit_notes_widget = AppendMultiListWidget([], "Unit Notes", noteAttrs, UnitNotesDelegate, self, model=UnitNotesDoubleListModel)
        self.unit_notes_widget.view.setMaximumHeight(120)
        if not DB.constants.value('unit_notes'):
            self.unit_notes_widget.hide()

        default_weapons = {weapon_nid: DB.weapons.default() for weapon_nid in DB.weapons.keys()}
        self.wexp_gain_widget = HorizWeaponListWidget(
            default_weapons, "Starting Weapon Experience", HorizWeaponListDelegate, self)
        # Changing of Weapon Gain done automatically
        # self.wexp_gain_widget.activated.connect(self.wexp_gain_changed)

        item_section = QHBoxLayout()
        self.item_widget = ItemListWidget("Starting Items", self)
        self.item_widget.items_updated.connect(self.items_changed)
        # self.item_widget.setMaximumHeight(200)
        item_section.addWidget(self.item_widget)

        self.alternate_class_box = PropertyBox("Alternate Classes", MultiSelectComboBox, self)
        self.alternate_class_box.edit.setPlaceholderText("Class Change Options...")
        self.alternate_class_box.edit.addItems(DB.classes.keys())
        self.alternate_class_box.edit.updated.connect(self.alternate_class_changed)

        self.affinity_box = AffinityBox(self)
        self.affinity_box.edit.currentIndexChanged.connect(self.affinity_changed)

        total_section = QVBoxLayout()
        total_section.addLayout(top_section)
        total_section.addLayout(main_section)
        total_section.addWidget(QHLine())
        total_section.addWidget(self.unit_stat_widget)
        total_section.addWidget(self.wexp_gain_widget)
        total_widget = QWidget()
        total_widget.setLayout(total_section)

        right_section = QVBoxLayout()
        right_section.addLayout(item_section)
        right_section.addWidget(QHLine())
        right_section.addWidget(self.personal_skill_widget)
        right_section.addWidget(self.unit_notes_widget)
        right_section.addWidget(QHLine())
        right_section.addWidget(self.alternate_class_box)
        right_section.addWidget(self.affinity_box)
        right_widget = QWidget()
        right_widget.setLayout(right_section)

        self.splitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(total_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setStyleSheet("QSplitter::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eee, stop:1 #ccc); border: 1px solid #777; width: 13px; margin-top: 2px; margin-bottom: 2px; border-radius: 4px;}")

        final_section = QHBoxLayout()
        self.setLayout(final_section)
        final_section.addWidget(self.splitter)

    def nid_changed(self, text):
        # Also change name if they are identical
        if self.current.name == self.current.nid:
            self.name_box.edit.setText(text)
        self.current.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Unit ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_name(self.current.nid, other_nids)
        self.model.on_nid_changed(self._data.find_key(self.current), self.current.nid)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def name_changed(self, text):
        self.current.name = text

    def desc_changed(self, text=None):
        self.current.desc = self.desc_box.edit.toPlainText()
        # self.current.desc = text

    def level_changed(self, val):
        self.current.level = int(val)
        if self.averages_dialog:
            self.averages_dialog.update()

    def class_changed(self, index):
        self.current.klass = self.class_box.edit.currentText()
        # self.level_box.edit.setMaximum(DB.classes.get(self.current.klass).max_level)
        if self.averages_dialog:
            self.averages_dialog.update()

    def tags_changed(self):
        self.current.tags = self.tag_box.edit.currentText()

    def reset_stats(self):
        model = self.unit_stat_widget.model
        view = self.unit_stat_widget.view
        selected_indexes = view.selectionModel().selectedIndexes()
        my_klass = DB.classes.get(self.current.klass)
        
        if not selected_indexes:
            # Select all
            topLeft = model.index(0, 0)
            bottomRight = model.index(model.rowCount() - 1, model.columnCount() - 1)
            selection = QItemSelection(topLeft, bottomRight)
            view.selectionModel().select(selection, QItemSelectionModel.Select)
            selected_indexes = view.selectionModel().selectedIndexes()

        for index in selected_indexes:
            stat_nid = DB.stats[index.column()].nid
            if index.row() == 0:
                class_value = my_klass.bases.get(stat_nid, 0)
            else:
                class_value = my_klass.growths.get(stat_nid, 0)
            model.setData(index, class_value, Qt.EditRole)

    def display_averages(self):
        # Modeless dialog
        if not self.averages_dialog:
            self.averages_dialog = StatAverageDialog(self.current, "Unit", UnitStatAveragesModel, self)
        self.averages_dialog.show()
        self.averages_dialog.raise_()
        self.averages_dialog.activateWindow()

    def close_averages(self):
        if self.averages_dialog:
            self.averages_dialog.done(0)
            self.averages_dialog = None

    def stat_list_model_data_changed(self, index1, index2):
        if self.averages_dialog:
            self.averages_dialog.update()

    # def learned_skills_changed(self):
    #     pass

    # def wexp_gain_changed(self):
    #     pass

    def items_changed(self):
        self.current.starting_items = self.item_widget.get_items()

    def access_tags(self):
        dlg = TagDialog.create(self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            self.tag_box.edit.clear()
            self.tag_box.edit.addItems(DB.tags.keys())
            self.tag_box.edit.setCurrentTexts(self.current.tags)
        else:
            pass

    def variant_changed(self, text):
        self.current.variant = text

    def alternate_class_changed(self):
        self.current.alternate_classes = self.alternate_class_box.edit.currentText()

    def affinity_changed(self, index):
        self.current.affinity = self.affinity_box.edit.currentText()

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.name_box.edit.setText(current.name)
        self.desc_box.edit.setText(current.desc)
        self.level_box.edit.setValue(int(current.level))
        self.class_box.edit.setValue(current.klass)
        tags = current.tags[:]
        self.tag_box.edit.clear()
        self.tag_box.edit.addItems(DB.tags.keys())
        self.tag_box.edit.setCurrentTexts(tags)

        self.unit_stat_widget.update_stats()
        self.unit_stat_widget.set_new_obj(current)
        if self.averages_dialog:
            self.averages_dialog.set_current(current)

        self.personal_skill_widget.set_current(current.learned_skills)
        self.unit_notes_widget.set_current(current.unit_notes)
        self.wexp_gain_widget.set_current(current.wexp_gain)
        self.item_widget.set_current(current.starting_items)

        if current.variant:
            self.variant_box.edit.setText(current.variant)
        else:
            self.variant_box.edit.clear()

        self.alternate_class_box.edit.clear()
        self.alternate_class_box.edit.addItems(DB.classes.keys())
        if current.alternate_classes:
            alternate_classes = current.alternate_classes[:]
            self.alternate_class_box.edit.setCurrentTexts(alternate_classes)
        if current.affinity:
            self.affinity_box.edit.setValue(current.affinity)
        else:
            self.affinity_box.edit.setValue("None")

        self.icon_edit.set_current(current.portrait_nid)

    def hideEvent(self, event):
        self.close_averages()
