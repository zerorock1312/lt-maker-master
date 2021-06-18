import time, random

from PyQt5.QtWidgets import QWidget, QHBoxLayout, \
    QVBoxLayout, QGridLayout, QPushButton, QSizePolicy, QFrame, QSplitter
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QIcon

from app.extensions.spinbox_xy import SpinBoxXY
from app.extensions.custom_gui import PropertyBox
from app.editor import timer
from app.editor.icon_editor.icon_view import IconView
from app.editor.portrait_editor import portrait_model
import app.editor.utilities as editor_utilities

class PortraitProperties(QWidget):
    width, height = 128, 112

    halfblink = (96, 48, 32, 16)
    fullblink = (96, 64, 32, 16)

    openmouth = (0, 96, 32, 16)
    halfmouth = (32, 96, 32, 16)
    closemouth = (64, 96, 32, 16)

    opensmile = (0, 80, 32, 16)
    halfsmile = (32, 80, 32, 16)
    closesmile = (64, 80, 32, 16)

    def __init__(self, parent, current=None):
        QWidget.__init__(self, parent)
        self.window = parent
        self._data = self.window._data

        # Populate resources
        for resource in self._data:
            resource.pixmap = QPixmap(resource.full_path)

        self.current = current

        self.smile_on = False
        self.talk_on = False
        # For talking
        self.talk_state = 0
        self.last_talk_update = 0
        self.next_talk_update = 0
        # For blinking
        self.blink_on = False
        self.blink_update = 0

        left_section = QGridLayout()

        self.portrait_view = IconView(self)
        self.portrait_view.setMinimumHeight(80 + 2)
        left_section.addWidget(self.portrait_view, 0, 0, 1, 3)

        self.smile_button = QPushButton(self)
        self.smile_button.setText("Smile")
        self.smile_button.setCheckable(True)
        self.smile_button.clicked.connect(self.smile_button_clicked)
        self.talk_button = QPushButton(self)
        self.talk_button.setText("Talk")
        self.talk_button.setCheckable(True)
        self.talk_button.clicked.connect(self.talk_button_clicked)
        self.blink_button = QPushButton(self)
        self.blink_button.setText("Blink")
        self.blink_button.setCheckable(True)
        self.blink_button.clicked.connect(self.blink_button_clicked)
        left_section.addWidget(self.smile_button)
        left_section.addWidget(self.talk_button)
        left_section.addWidget(self.blink_button)

        right_section = QVBoxLayout()
        self.blinking_offset = PropertyBox("Blinking Offset", SpinBoxXY, self)
        self.blinking_offset.edit.setSingleStep(8)
        self.blinking_offset.edit.coordsChanged.connect(self.blinking_changed)
        self.smiling_offset = PropertyBox("Smiling Offset", SpinBoxXY, self)
        self.smiling_offset.edit.setSingleStep(8)
        self.smiling_offset.edit.coordsChanged.connect(self.smiling_changed)
        right_section.addWidget(self.blinking_offset)
        right_section.addWidget(self.smiling_offset)
        self.auto_frame_button = QPushButton("Auto-guess Offsets")
        self.auto_frame_button.clicked.connect(self.auto_guess_offset)
        right_section.addWidget(self.auto_frame_button)
        right_section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        left_frame = QFrame(self)
        left_frame.setLayout(left_section)
        right_frame = QFrame(self)
        right_frame.setLayout(right_section)

        top_splitter = QSplitter(self)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.addWidget(left_frame)
        top_splitter.addWidget(right_frame)

        self.raw_view = PropertyBox("Raw Sprite", IconView, self)
        self.raw_view.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        final_splitter = QSplitter(self)
        final_splitter.setOrientation(Qt.Vertical)
        final_splitter.setChildrenCollapsible(False)
        final_splitter.addWidget(top_splitter)
        final_splitter.addWidget(self.raw_view)

        final_section = QHBoxLayout()
        self.setLayout(final_section)
        final_section.addWidget(final_splitter)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def set_current(self, current):
        self.current = current
        self.raw_view.edit.set_image(self.current.pixmap)
        self.raw_view.edit.show_image()

        bo = self.current.blinking_offset
        so = self.current.smiling_offset
        self.blinking_offset.edit.set_current(bo[0], bo[1])
        self.smiling_offset.edit.set_current(so[0], so[1])

        self.draw_portrait()

    def tick(self):
        self.draw_portrait()

    def update_talk(self):
        current_time = time.time()*1000
        # update mouth
        if self.talk_on and current_time - self.last_talk_update > self.next_talk_update:
            self.last_talk_update = current_time
            chance = random.randint(1, 10)
            if self.talk_state == 0:
                # 10% chance to skip to state 2    
                if chance == 1:
                    self.talk_state = 2
                    self.next_talk_update = random.randint(70, 160)
                else:
                    self.talk_state = 1
                    self.next_talk_update = random.randint(30, 50)
            elif self.talk_state == 1:
                # 10% chance to go back to state 0
                if chance == 1:
                    self.talk_state = 0
                    self.next_talk_update = random.randint(50, 100)
                else:
                    self.talk_state = 2
                    self.next_talk_update = random.randint(70, 160)
            elif self.talk_state == 2:
                # 10% chance to skip back to state 0
                # 10% chance to go back to state 1
                chance = random.randint(1, 10)
                if chance == 1:
                    self.talk_state = 0
                    self.next_talk_update = random.randint(50, 100)
                elif chance == 2:
                    self.talk_state = 1
                    self.next_talk_update = random.randint(30, 50)
                else:
                    self.talk_state = 3
                    self.next_talk_update = random.randint(30, 50)
            elif self.talk_state == 3:
                self.talk_state = 0
                self.next_talk_update = random.randint(50, 100)
        if not self.talk_on:
            self.talk_state = 0

    def draw_portrait(self):
        self.update_talk()
        if not self.current:
            return
        main_portrait = self.current.pixmap.copy(0, 0, 96, 80)
        main_portrait = main_portrait.toImage()
        # For smile image
        if self.smile_on:
            if self.talk_state == 0:
                mouth_image = self.current.pixmap.copy(*self.closesmile)
            elif self.talk_state == 1 or self.talk_state == 3:
                mouth_image = self.current.pixmap.copy(*self.halfsmile)
            elif self.talk_state == 2:
                mouth_image = self.current.pixmap.copy(*self.opensmile)
        else:
            if self.talk_state == 0:
                mouth_image = self.current.pixmap.copy(*self.closemouth)
            elif self.talk_state == 1 or self.talk_state == 3:
                mouth_image = self.current.pixmap.copy(*self.halfmouth)
            elif self.talk_state == 2:
                mouth_image = self.current.pixmap.copy(*self.openmouth)
        mouth_image = mouth_image.toImage()
        # For blink image
        if self.blink_on:
            time_passed = time.time()*1000 - self.blink_update
            if time_passed < 60:
                blink_image = self.current.pixmap.copy(*self.halfblink)
            else:
                blink_image = self.current.pixmap.copy(*self.fullblink)
        else:
            blink_image = None
        # Draw image
        painter = QPainter()
        painter.begin(main_portrait)
        if blink_image:
            blink_image = blink_image.toImage()
            painter.drawImage(self.current.blinking_offset[0], self.current.blinking_offset[1], blink_image)
        painter.drawImage(self.current.smiling_offset[0], self.current.smiling_offset[1], mouth_image)
        painter.end()

        final_pix = QPixmap.fromImage(editor_utilities.convert_colorkey(main_portrait))
        self.portrait_view.set_image(final_pix)
            
        self.portrait_view.show_image()

    def blinking_changed(self, x, y):
        self.current.blinking_offset = [x, y]

    def smiling_changed(self, x, y):
        self.current.smiling_offset = [x, y]

    def auto_guess_offset(self):
        portrait_model.auto_frame_portrait(self.current)
        self.set_current(self.current)

    def talk_button_clicked(self, checked):
        self.talk_on = checked

    def smile_button_clicked(self, checked):
        self.smile_on = checked

    def blink_button_clicked(self, checked):
        self.blink_update = time.time()*1000
        self.blink_on = checked
