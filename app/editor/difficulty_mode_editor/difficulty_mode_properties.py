from PyQt5.QtWidgets import QWidget, QLineEdit, QMessageBox, \
    QVBoxLayout, QHBoxLayout, QSpinBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from app.sprites import SPRITES

from app.editor.stat_widget import StatListWidget
from app.extensions.custom_gui import PropertyBox, ComboBox
from app.utilities import str_utils

class PlayerStatListWidget(StatListWidget):
    def get_stat_lists(self, obj):
        return obj.get_player_stat_lists()

class EnemyStatListWidget(StatListWidget):
    def get_stat_lists(self, obj):
        return obj.get_enemy_stat_lists()

class BossStatListWidget(StatListWidget):
    def get_stat_lists(self, obj):
        return obj.get_boss_stat_lists()

class DifficultyModeProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = self.window._data

        self.current = current

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        
        self.name_box = PropertyBox("Display Name", QLineEdit, self)
        self.name_box.edit.setMaxLength(20)
        self.name_box.edit.textChanged.connect(self.name_changed)

        self.color_box = PropertyBox("Color", ComboBox, self)
        for color in ['blue', 'green', 'red']:
            icon = QIcon('sprites/menus/chapter_select_%s' % color)
            self.color_box.edit.addItem(icon, color)
        self.color_box.edit.setIconSize(QSize(192, 30))
        self.color_box.edit.currentIndexChanged.connect(self.color_changed)

        self.permadeath_choice = PropertyBox("Permadeath", ComboBox, self)
        self.permadeath_choice.edit.addItems(['Player Choice', 'Classic', 'Casual'])
        self.permadeath_choice.edit.currentIndexChanged.connect(self.permadeath_changed)

        self.growths_choice = PropertyBox("Growth method", ComboBox, self)
        self.growths_choice.edit.addItems(['Player Choice', 'Random', 'Fixed', 'Dynamic'])
        self.growths_choice.edit.currentIndexChanged.connect(self.growths_changed)

        self.rng_choice = PropertyBox("Method for resolving accuracy rolls", ComboBox, self)
        self.rng_choice.edit.addItems(["Classic", "True Hit", "True Hit+", "Grandmaster"])
        self.rng_choice.edit.currentIndexChanged.connect(self.rng_changed)

        self.player_stat_widget = PlayerStatListWidget(self.current, "Player Bonus Stats", average_button=False, parent=self)
        self.player_stat_widget.view.setFixedHeight(100)

        self.enemy_stat_widget = EnemyStatListWidget(self.current, "Enemy Bonus Stats", average_button=False, parent=self)
        self.enemy_stat_widget.view.setFixedHeight(100)

        self.boss_stat_widget = BossStatListWidget(self.current, "Boss Bonus Stats", average_button=False, parent=self)
        self.boss_stat_widget.view.setFixedHeight(100)

        self.player_autolevels = PropertyBox("Player Autolevels", QSpinBox, self)
        self.player_autolevels.edit.setAlignment(Qt.AlignRight)
        self.player_autolevels.edit.valueChanged.connect(self.player_autolevel_changed)
        self.enemy_autolevels = PropertyBox("Enemy Autolevels", QSpinBox, self)
        self.enemy_autolevels.edit.setAlignment(Qt.AlignRight)
        self.enemy_autolevels.edit.valueChanged.connect(self.enemy_autolevel_changed)
        self.boss_autolevels = PropertyBox("Boss Autolevels", QSpinBox, self)
        self.boss_autolevels.edit.setAlignment(Qt.AlignRight)
        self.boss_autolevels.edit.valueChanged.connect(self.boss_autolevel_changed)
        autolevel_section = QHBoxLayout()
        autolevel_section.addWidget(self.player_autolevels)
        autolevel_section.addWidget(self.enemy_autolevels)
        autolevel_section.addWidget(self.boss_autolevels)

        main_section = QVBoxLayout()
        main_section.addWidget(self.nid_box)
        main_section.addWidget(self.name_box)
        main_section.addWidget(self.color_box)
        main_section.addWidget(self.permadeath_choice)
        main_section.addWidget(self.growths_choice)
        main_section.addWidget(self.rng_choice)
        main_section.addWidget(self.player_stat_widget)
        main_section.addWidget(self.enemy_stat_widget)
        main_section.addWidget(self.boss_stat_widget)
        main_section.addLayout(autolevel_section)
        self.setLayout(main_section)
        
    def nid_changed(self, text):
        if self.current.name == self.current.nid:
            self.name_box.edit.setText(text)
        self.current.nid = text
        self.window.update_list()        

    def nid_done_editing(self):
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Difficulty Mode ID %s already in use' % self.current.nid)
        self.current.nid = str_utils.get_next_name(self.current.nid, other_nids)
        old_nid = self._data.find_key(self.current)
        self.window.left_frame.model.on_nid_changed(old_nid, self.current.nid)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def name_changed(self, text):
        self.current.name = text
        self.window.update_list()

    def color_changed(self, index):
        self.current.color = self.color_box.edit.currentText()

    def permadeath_changed(self, index):
        self.current.permadeath_choice = self.permadeath_choice.edit.currentText()

    def growths_changed(self, index):
        self.current.growths_choice = self.growths_choice.edit.currentText()

    def rng_changed(self, index):
        self.current.rng_choice = self.rng_choice.edit.currentText()

    def player_autolevel_changed(self, index):
        self.current.player_autolevels = self.player_autolevels.edit.value()

    def enemy_autolevel_changed(self, index):
        self.current.enemy_autolevels = self.enemy_autolevels.edit.value()

    def boss_autolevel_changed(self, index):
        self.current.boss_autolevels = self.boss_autolevels.edit.value()

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.name_box.edit.setText(current.name)
        self.color_box.edit.setValue(current.color)
        self.permadeath_choice.edit.setValue(current.permadeath_choice)
        self.growths_choice.edit.setValue(current.growths_choice)
        self.rng_choice.edit.setValue(current.rng_choice)

        self.player_stat_widget.update_stats()
        self.player_stat_widget.set_new_obj(current)
        self.enemy_stat_widget.update_stats()
        self.enemy_stat_widget.set_new_obj(current)
        self.boss_stat_widget.update_stats()
        self.boss_stat_widget.set_new_obj(current)

        self.player_autolevels.edit.setValue(current.player_autolevels)
        self.enemy_autolevels.edit.setValue(current.enemy_autolevels)
        self.boss_autolevels.edit.setValue(current.boss_autolevels)
