from PyQt5.QtWidgets import QDialog, QGridLayout, QDialogButtonBox, QTabWidget, \
    QSizePolicy
from PyQt5.QtCore import Qt

from app.resources.resources import RESOURCES
from app.data.database import DB

from app.editor.settings import MainSettingsController

class SingleDatabaseEditor(QDialog):
    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self.window = parent
        self.main_editor = self.window

        self.set_up()

        self.tab = tab.create(self)
        self.grid.addWidget(self.tab, 0, 0, 1, 2)

        self.setWindowTitle(self.tab.windowTitle())

        # Restore Geometry
        self.settings = MainSettingsController()
        geometry = self.settings.component_controller.get_geometry(self._type())
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.component_controller.get_state(self._type())
        if state:
            self.tab.splitter.restoreState(state)

    def set_up(self):
        self.setStyleSheet("font: 10pt;")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)

        self.save()

        self.grid = QGridLayout(self)
        self.setLayout(self.grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply, Qt.Horizontal, self)
        self.grid.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.buttonbox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)

    def on_tab_close(self):
        self.tab.on_tab_close()

    def accept(self):
        current_proj = self.settings.get_current_project()
        self.save_geometry()
        self.on_tab_close()
        # if current_proj:
        #     DB.serialize(current_proj)
        super().accept()

    def reject(self):
        self.restore()
        current_proj = self.settings.get_current_project()
        self.save_geometry()
        self.on_tab_close()
        # if current_proj:
        #     DB.serialize(current_proj)
        super().reject()

    def save(self):
        self.saved_data = DB.save()
        return self.saved_data

    def restore(self):
        DB.restore(self.saved_data)
        # Make sure we use the new restored database as the level 
        # in the level editors
        if self.main_editor:
            state_manager = self.main_editor.app_state_manager
            current_level_nid = state_manager.state.selected_level
            state_manager.change_and_broadcast(
                'selected_level', current_level_nid)
        
    def apply(self):
        self.save()

    def closeEvent(self, event):
        self.save_geometry()
        self.on_tab_close()
        super().closeEvent(event)

    def _type(self):
        return self.tab.__class__.__name__

    def save_geometry(self):
        self.settings.component_controller.set_geometry(self._type(), self.saveGeometry())
        self.settings.component_controller.set_state(self._type(), self.tab.splitter.saveState())

class MultiDatabaseEditor(SingleDatabaseEditor):
    def __init__(self, tabs, parent=None):
        QDialog.__init__(self, parent)
        self.window = parent
        self.main_editor = self.window

        self.set_up()

        self.tab_bar = QTabWidget(self)
        self.grid.addWidget(self.tab_bar, 0, 0, 1, 2)
        self.tabs = []
        for tab in tabs:
            new_tab = tab.create(self)
            self.tabs.append(new_tab)
            self.tab_bar.addTab(new_tab, new_tab.windowTitle())

        self.current_tab = self.tab_bar.currentWidget()
        self.tab_bar.currentChanged.connect(self.on_tab_changed)

        # Restore Geometry
        self.settings = MainSettingsController()
        geometry = self.settings.component_controller.get_geometry(self._type())
        if geometry:
            self.restoreGeometry(geometry)
        for tab in self.tabs:
            _type = tab.__class__.__name__
            state = self.settings.component_controller.get_state(_type)
            if state and tab.splitter:
                tab.splitter.restoreState(state)

    def on_tab_changed(self, idx):
        # Make each tab individually resizable
        for i in range(self.tab_bar.count()):
            if i == idx:
                self.tab_bar.widget(i).setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            else:
                self.tab_bar.widget(i).setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        new_tab = self.tab_bar.currentWidget()
        self.current_tab = new_tab
        self.current_tab.update_list()
        self.current_tab.reset()

    def _type(self):
        s = ''
        for tab in self.tabs:
            s += tab.__class__.__name__
        return s

    def on_tab_close(self, event=None):
        if event:
            for tab in self.tabs:
                tab.closeEvent(event)

    def save_geometry(self):
        self.settings.component_controller.set_geometry(self._type(), self.saveGeometry())
        for tab in self.tabs:
            _type = tab.__class__.__name__
            if tab.splitter:
                self.settings.component_controller.set_state(_type, tab.splitter.saveState())

    def closeEvent(self, event):
        self.save_geometry()
        self.on_tab_close(event)
        super().closeEvent(event)

class SingleResourceEditor(QDialog):
    def __init__(self, tab, resource_types=None, parent=None):
        super().__init__(parent)
        self.window = parent
        self.resource_types = resource_types
        self.setStyleSheet("font: 10pt;")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)

        self.grid = QGridLayout(self)
        self.setLayout(self.grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.grid.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.tab = tab.create(self)
        self.grid.addWidget(self.tab, 0, 0, 1, 2)

        self.setWindowTitle(self.tab.windowTitle())

        # Restore Geometry
        self.settings = MainSettingsController()
        geometry = self.settings.component_controller.get_geometry(self._type())
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.component_controller.get_state(self._type())
        if state:
            self.tab.splitter.restoreState(state)

    def accept(self):
        current_proj = self.settings.get_current_project()
        if current_proj:
            RESOURCES.save(current_proj, self.resource_types)
        self.save_geometry()
        super().accept()
        self.close()

    def reject(self):
        current_proj = self.settings.get_current_project()
        if current_proj:
            RESOURCES.load(current_proj)
        self.save_geometry()
        super().reject()
        self.close()

    def closeEvent(self, event):
        self.save_geometry()
        super().closeEvent(event)

    def _type(self):
        return self.tab.__class__.__name__

    def save_geometry(self):
        self.settings.component_controller.set_geometry(self._type(), self.saveGeometry())
        if hasattr(self.tab, 'splitter'):
            self.settings.component_controller.set_state(self._type(), self.tab.splitter.saveState())

class MultiResourceEditor(SingleResourceEditor):
    def __init__(self, tabs, resource_types, parent=None):
        QDialog.__init__(self, parent)
        self.window = parent
        self.resource_types = resource_types
        self.setWindowTitle("Resource Editor")
        self.setStyleSheet("font: 10pt;")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)

        self.grid = QGridLayout(self)
        self.setLayout(self.grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.grid.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.tab_bar = QTabWidget(self)
        self.grid.addWidget(self.tab_bar, 0, 0, 1, 2)
        self.tabs = []
        for tab in tabs:
            new_tab = tab.create(self)
            self.tabs.append(new_tab)
            self.tab_bar.addTab(new_tab, new_tab.windowTitle())

        self.current_tab = self.tab_bar.currentWidget()
        self.tab_bar.currentChanged.connect(self.on_tab_changed)

        # Restore Geometry
        self.settings = MainSettingsController()
        geometry = self.settings.component_controller.get_geometry(self._type())
        if geometry:
            self.restoreGeometry(geometry)

    def on_tab_changed(self, idx):
        # Make each tab individually resizable
        for i in range(self.tab_bar.count()):
            if i == idx:
                self.tab_bar.widget(i).setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            else:
                self.tab_bar.widget(i).setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        new_tab = self.tab_bar.currentWidget()
        self.current_tab = new_tab
        self.current_tab.update_list()
        self.current_tab.reset()

    def _type(self):
        s = ''
        for tab in self.tabs:
            s += tab.__class__.__name__
        return s

    def save_geometry(self):
        self.settings.component_controller.set_geometry(self._type(), self.saveGeometry())

    def closeEvent(self, event):
        self.save_geometry()
        for tab in self.tabs:
            tab.closeEvent(event)
        super().closeEvent(event)
