from functools import partial

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QToolButton, \
    QSpinBox, QLineEdit, QPushButton, QCheckBox, QVBoxLayout, \
    QGroupBox, QFormLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor, QPixmap

from app.editor.settings import MainSettingsController

from app.constants import WINWIDTH, WINHEIGHT
from app.resources.resources import RESOURCES

from app.editor.combat_animation_editor.frame_selector import FrameSelector
from app.extensions.color_icon import ColorIcon
from app.extensions.custom_gui import ComboBox

class CombatCommand(QWidget):
    def __init__(self, data, parent):
        super().__init__(parent)
        self._data = data
        self.window = parent

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        self.setLayout(hbox)

        self.setToolTip(self._data.desc)

        self.settings = MainSettingsController()
        theme = self.settings.get_theme(0)
        if theme == 0:
            icon_folder = 'icons/icons'
        else:
            icon_folder = 'icons/dark_icons'

        icon_label = QLabel()
        pixmap = QPixmap(f"{icon_folder}/command_%s.png" % self._data.tag)
        pixmap = pixmap.scaled(32, 32)
        icon_label.setPixmap(pixmap)
        hbox.addWidget(icon_label)

        name_label = QLabel(self._data.name)
        hbox.addWidget(name_label)

        self.create_editor(hbox)

        x_button = QToolButton(self)
        x_button.setIcon(QIcon(f"{icon_folder}/x.png"))
        x_button.setStyleSheet("QToolButton { border: 0px solid #575757; background-color: palette(base); }")
        x_button.clicked.connect(partial(self.window.remove_command_widget, self))
        hbox.addWidget(x_button, Qt.AlignRight)

    def create_editor(self, hbox):
        raise NotImplementedError

    def on_value_changed(self, val):
        self._data.value = val

    @property
    def data(self):
        return self._data

class BasicCommand(CombatCommand):
    def create_editor(self, hbox):
        pass

    def on_value_changed(self, val):
        pass

class BoolCommand(CombatCommand):
    def create_editor(self, hbox):
        self.editor = QCheckBox(self)
        self.editor.setChecked(self._data.value)
        self.editor.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self, val):
        self._data.value = bool(val)

class IntCommand(CombatCommand):
    def create_editor(self, hbox):
        label = QLabel("#")
        hbox.addWidget(label)

        self.editor = QSpinBox(self)
        self.editor.setMaximumWidth(40)
        self.editor.setRange(1, 1024)
        self.editor.setValue(self._data.value)
        self.editor.valueChanged.connect(self.on_value_changed)
        hbox.addWidget(self.editor)

    def on_value_changed(self, val):
        self._data.value = int(val)

class SoundCommand(CombatCommand):
    def create_editor(self, hbox):
        self.editor = ComboBox(self)
        self.editor.addItems([d.nid for d in RESOURCES.sfx])
        self.editor.setValue(self._data.value)
        self.editor.currentIndexChanged.connect(self.on_value_changed)
        hbox.addWidget(self.editor)

    def on_value_changed(self, idx):
        self._data.value = RESOURCES.sfx[idx].nid

class EffectCommand(CombatCommand):
    def create_editor(self, hbox):
        self.editor = ComboBox(self)
        self.editor.addItems([d.nid for d in RESOURCES.combat_effects])
        self.editor.currentIndexChanged.connect(self.on_value_changed)
        hbox.addWidget(self.editor)

    def on_value_changed(self, idx):
        self._data.value = RESOURCES.combat_effects[idx].nid

class WaitForHitCommand(CombatCommand):
    def create_editor(self, hbox):
        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()
        vbox = QVBoxLayout()

        self.editor1 = QLineEdit(self)
        self.editor1.setPlaceholderText('Frame Drawn Over Enemy')
        self.editor1.setMaximumWidth(100)
        self.editor1.setReadOnly(True)
        if self._data.value[0]:
            self.frame.setText(self._data.value[0])
        self.editor1.textChanged.connect(self.on_value_changed)
        hbox1.addWidget(self.editor1)

        self.button1 = QPushButton('...')
        self.button1.setMaximumWidth(40)
        self.button1.clicked.connect(self.select_frame1)
        hbox1.addWidget(self.button1)

        self.editor2 = QLineEdit(self)
        self.editor2.setPlaceholderText('Frame Drawn Under Enemy')
        self.editor2.setMaximumWidth(100)
        self.editor2.setReadOnly(True)
        if self._data.value[1]:
            self.frame.setText(self._data.value[1])
        self.editor2.textChanged.connect(self.on_value_changed)
        hbox2.addWidget(self.editor2)

        self.button2 = QPushButton('...')
        self.button2.setMaximumWidth(40)
        self.button2.clicked.connect(self.select_frame2)
        hbox2.addWidget(self.button2)

        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        hbox.addLayout(vbox)

    def on_value_changed(self, text):
        self._data.value = (self.editor1.text(), self.editor2.text())

    def select_frame1(self):
        combat_anim_editor = self.window.window
        weapon_anim = combat_anim_editor.get_current_weapon_anim()
        res, ok = FrameSelector.get(combat_anim_editor.current, weapon_anim)
        if ok:
            self.editor1.setText(res)

    def select_frame2(self):
        combat_anim_editor = self.window.window
        weapon_anim = combat_anim_editor.get_current_weapon_anim()
        res, ok = FrameSelector.get(combat_anim_editor.current, weapon_anim)
        if ok:
            self.editor2.setText(res)

class FrameCommand(CombatCommand):
    def create_editor(self, hbox):
        label = QLabel("#")
        hbox.addWidget(label)

        self.num_frames = QSpinBox(self)
        self.num_frames.setMaximumWidth(40)
        self.num_frames.setRange(1, 1024)
        self.num_frames.setValue(self._data.value[0])
        self.num_frames.valueChanged.connect(self.on_value_changed)
        hbox.addWidget(self.num_frames)

        self.frame = QLineEdit(self)
        self.frame.setMaximumWidth(100)
        self.frame.setPlaceholderText(self._data.name[8:])
        self.frame.setReadOnly(True)
        if self._data.value[1]:
            self.frame.setText(self._data.value[1])
        self.frame.textChanged.connect(self.on_value_changed)
        hbox.addWidget(self.frame)

        self.button = QPushButton('...')
        self.button.setMaximumWidth(40)
        self.button.clicked.connect(self.select_frame)
        hbox.addWidget(self.button)

    def on_value_changed(self, val):
        num_frames = int(self.num_frames.value())
        frame = self.frame.text()
        self._data.value = (num_frames, frame)

    def select_frame(self):
        combat_anim_editor = self.window.window
        weapon_anim = combat_anim_editor.get_current_weapon_anim()
        res, ok = FrameSelector.get(combat_anim_editor.current, weapon_anim)
        if ok:
            self.frame.setText(res.nid)

class DualFrameCommand(CombatCommand):
    def create_editor(self, hbox):
        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()
        vbox = QVBoxLayout()

        self.num_frames = QSpinBox(self)
        self.num_frames.setMaximumWidth(40)
        self.num_frames.setRange(1, 1024)
        self.num_frames.setValue(self._data.value[0])
        self.num_frames.valueChanged.connect(self.on_value_changed)
        hbox.addWidget(self.num_frames)

        self.editor1 = QLineEdit(self)
        self.editor1.setPlaceholderText('Frame Drawn Over Enemy')
        self.editor1.setMaximumWidth(100)
        self.editor1.setReadOnly(True)
        if self._data.value[1]:
            self.frame.setText(self._data.value[1])
        self.editor1.textChanged.connect(self.on_value_changed)
        hbox1.addWidget(self.editor1)

        self.button1 = QPushButton('...')
        self.button1.setMaximumWidth(40)
        self.button1.clicked.connect(self.select_frame1)
        hbox1.addWidget(self.button1)

        self.editor2 = QLineEdit(self)
        self.editor2.setPlaceholderText('Frame Drawn Under Enemy')
        self.editor2.setMaximumWidth(100)
        self.editor2.setReadOnly(True)
        if self._data.value[2]:
            self.frame.setText(self._data.value[2])
        self.editor2.textChanged.connect(self.on_value_changed)
        hbox2.addWidget(self.editor2)

        self.button2 = QPushButton('...')
        self.button2.setMaximumWidth(40)
        self.button2.clicked.connect(self.select_frame2)
        hbox2.addWidget(self.button2)

        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        hbox.addLayout(vbox)

    def on_value_changed(self, text):
        num_frames = int(self.num_frames.value())
        self._data.value = (num_frames, self.editor1.text(), self.editor2.text())

    def select_frame1(self):
        combat_anim_editor = self.window.window
        weapon_anim = combat_anim_editor.get_current_weapon_anim()
        res, ok = FrameSelector.get(combat_anim_editor.current, weapon_anim)
        if ok:
            self.editor1.setText(res)

    def select_frame2(self):
        combat_anim_editor = self.window.window
        weapon_anim = combat_anim_editor.get_current_weapon_anim()
        res, ok = FrameSelector.get(combat_anim_editor.current, weapon_anim)
        if ok:
            self.editor2.setText(res)

class FrameWithOffsetCommand(CombatCommand):
    def create_editor(self, hbox):
        label = QLabel("#")
        hbox.addWidget(label)

        self.num_frames = QSpinBox(self)
        self.num_frames.setMaximumWidth(40)
        self.num_frames.setRange(1, 1024)
        self.num_frames.setValue(self._data.value[0])
        self.num_frames.valueChanged.connect(self.on_value_changed)
        hbox.addWidget(self.num_frames)

        self.frame = QLineEdit(self)
        self.frame.setMaximumWidth(100)
        self.frame.setPlaceholderText(self._data.name[8:])
        self.frame.setReadOnly(True)
        if self._data.value[1]:
            self.frame.setText(self._data.value[1])
        self.frame.textChanged.connect(self.on_value_changed)
        hbox.addWidget(self.frame)

        self.button = QPushButton('...')
        self.button.setMaximumWidth(40)
        self.button.clicked.connect(self.select_frame)
        hbox.addWidget(self.button)

        offset_section = QGroupBox(self)
        offset_section.setTitle("Offset")
        offset_layout = QFormLayout()
        self.x_box = QSpinBox()
        self.x_box.setValue(0)
        self.x_box.setRange(0, WINWIDTH)
        self.x_box.valueChanged.connect(self.on_value_changed)
        offset_layout.addRow("X:", self.x_box)
        self.y_box = QSpinBox()
        self.y_box.setValue(0)
        self.y_box.setRange(0, WINHEIGHT)
        self.y_box.valueChanged.connect(self.on_value_changed)
        offset_layout.addRow("Y:", self.y_box)
        offset_section.setLayout(offset_layout)
        hbox.addWidget(offset_section)

    def on_value_changed(self, val):
        num_frames = int(self.num_frames.value())
        frame = self.frame.text()
        x_val = int(self.x_box.value())
        y_val = int(self.y_box.value())
        self._data.value = (num_frames, frame, x_val, y_val)

    def select_frame(self):
        combat_anim_editor = self.window.window
        weapon_anim = combat_anim_editor.get_current_weapon_anim()
        res, ok = FrameSelector.get(combat_anim_editor.current, weapon_anim)
        if ok:
            self.frame.setText(res.nid)

class ColorTimeCommand(CombatCommand):
    def create_editor(self, hbox):
        label = QLabel("# Frames: ")
        hbox.addWidget(label)

        self.num_frames = QSpinBox(self)
        self.num_frames.setMaximumWidth(40)
        self.num_frames.setRange(1, 1024)
        self.num_frames.setValue(self._data.value[0])
        self.num_frames.valueChanged.connect(self.on_value_changed)
        hbox.addWidget(self.num_frames)

        self.color = ColorIcon(QColor(248, 248, 248), self)
        self.color.set_size(32)
        self.color.colorChanged.connect(self.on_value_changed)
        hbox.addWidget(self.color)

    def on_value_changed(self, val):
        num_frames = int(self.num_frame.value())
        color = self.color.color().getRgb()
        self._data.value = (num_frames, color)

def get_command_widget(command, parent):
    if command.attr is None:
        c = BasicCommand(command, parent)
    elif command.attr is bool:
        c = BoolCommand(command, parent)
    elif command.attr is int:
        c = IntCommand(command, parent)
    elif command.attr == 'sound':
        c = SoundCommand(command, parent)
    elif command.attr == 'effect':
        c = EffectCommand(command, parent)
    elif command.nid == 'wait_for_hit':
        c = WaitForHitCommand(command, parent)
    elif command.nid in ('frame', 'over_frame', 'under_frame'):
        c = FrameCommand(command, parent)
    elif command.nid == 'dual_frame':
        c = DualFrameCommand(command, parent)
    elif command.nid == 'frame_with_offset':
        c = FrameWithOffsetCommand(command, parent)
    elif command.attr[0] is int and command.attr[1] == 'color':
        c = ColorTimeCommand(command, parent)
    else:
        c = BasicCommand(command, parent)
    return c
