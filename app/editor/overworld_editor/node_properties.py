from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, \
    QWidget, QPushButton, QMessageBox, QLabel, QComboBox, QHBoxLayout, QDialog
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPixmap

from app.data.database import DB
from app.resources.resources import RESOURCES

from app.editor.icons import MapIconButton

from app.extensions.custom_gui import ComboBox, SimpleDialog, PropertyBox, PropertyCheckBox, QHLine
from app.utilities import str_utils
from app.editor.sound_editor import sound_tab
from app.editor.tile_editor import tile_tab

class NodePropertiesMenu(QWidget):    
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager
        
        self._initialize_components()
        
        # widget state
        self.current_node = None
        self.select_node(self.state_manager.state.selected_node)
        
        # subscriptions
        self.state_manager.subscribe_to_key(NodePropertiesMenu.__name__, 'selected_node', self.select_node)
        
    def select_node(self, node_nid):
        current_overworld = DB.overworlds.get(self.state_manager.state.selected_overworld)
        if(current_overworld):
            self.current_node = current_overworld.overworld_nodes.get(node_nid)
        else:
            self.current_node = None
        if(self.current_node):
            self.set_components_active(True)
            
            self.nid_box.edit.setText(self.current_node.nid)
            self.title_box.edit.setText(self.current_node.name)
            self.map_icon_selector.set_map_icon_object(RESOURCES.map_icons.get(self.current_node.icon))
            self._populate_level_combo_box(self.level_box.edit)
            self.level_box.edit.setCurrentIndex(self.level_box.edit.findData(self.current_node.level))
        else:
            self.set_components_active(False)
        
    def set_components_active(self, is_active):
        is_inactive = not is_active
        self.nid_box.setDisabled(is_inactive)
        self.title_box.setDisabled(is_inactive)
        self.level_box.setDisabled(is_inactive)
        self.map_icon_selector.setDisabled(is_inactive)
            
    def node_icon_changed(self, icon_nid):
        if(self.current_node):
            self.current_node.icon = icon_nid
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)

    def title_changed(self, text):
        if(self.current_node):
            self.current_node.name = text
            self.state_manager.change_and_broadcast('ui_refresh_signal', None)
        
    def level_changed(self, index):
        if(self.current_node):
            self.current_node.level = self.level_box.edit.itemData(index)
        
    def _initialize_components(self):
        self.setStyleSheet("font: 10pt;")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        
        self.nid_box = PropertyBox("Node ID", QLabel, self)
        self.layout.addWidget(self.nid_box) 

        self.title_box = PropertyBox("Location Name", QLineEdit, self)
        self.title_box.edit.textChanged.connect(self.title_changed)
        self.layout.addWidget(self.title_box)
        
        self.level_box = PropertyBox("Level", QComboBox, self)
        self.layout.addWidget(self.level_box)
        
        self.map_icon_selector = NodeIconSelector(self.node_icon_changed)
        self.layout.addWidget(self.map_icon_selector)
    
    def _populate_level_combo_box(self, level_combo_box):
        level_combo_box.clear()
        for level in DB.levels.values():
            level_combo_box.addItem(level.name, level.nid)
        level_combo_box.activated.connect(self.level_changed)
        return level_combo_box
    
class NodeIconSelector(QWidget):
    def __init__(self, on_icon_change):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        self.on_icon_change = on_icon_change
        self.map_icon_clickable_image_button = MapIconButton(self)
        self.map_icon_clickable_image_button.sourceChanged.connect(self.on_node_icon_changed)
        self.map_icon_name = QLabel("no_icon_selected", self)
        self.layout.addWidget(self.map_icon_clickable_image_button)
        self.layout.addWidget(self.map_icon_name)
        
    def set_map_icon_object(self, map_icon_object):
        self.map_icon_name.setText(map_icon_object.path)
        self.map_icon_clickable_image_button.set_current(map_icon_object.nid)
        
    def on_node_icon_changed(self, nid):
        self.on_icon_change(nid)