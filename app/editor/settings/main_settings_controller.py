from PyQt5.QtCore import QSettings, QDir
from .component_settings_controller import ComponentSettingsController

class MainSettingsController():
    """
    # Provides an interface for interacting with editor settings.
    # Contains general application-wide settings. Also contains
    # specific setting controllers for more tailored settings.
    """

    def __init__(self, company='rainlash', product='Lex Talionis'):
        QSettings.setDefaultFormat(QSettings.IniFormat)
        self.state = QSettings(company, product)
        self.component_controller = ComponentSettingsController()

    def fileName(self):
        return self.state.fileName()

    """========== General Settings =========="""

    def set_current_project(self, value):
        self.state.setValue("current_proj", value)

    def get_current_project(self, fallback=""):
        return self.state.value("current_proj", fallback)

    def set_last_open_path(self, value):
        self.state.setValue("last_open_path", value)

    def get_last_open_path(self, fallback=""):
        if not fallback:
            fallback = QDir.currentPath()
        return str(self.state.value("last_open_path", fallback))

    """========== General UI Settings =========="""

    def set_theme(self, value):
        self.state.setValue("theme", value)
    
    def get_theme(self, fallback=0):
        return self.state.value("theme", fallback)

    def set_event_autocomplete(self, value):
        self.state.setValue("event_autocomplete", value)

    def get_event_autocomplete(self, fallback=True):
        return self.state.value("event_autocomplete", fallback)

    def set_autosave_time(self, value):
        self.state.setValue("autosave_time", value)

    def get_autosave_time(self, fallback=5):
        return float(self.state.value("autosave_time", fallback))

    """========== General Control Settings =========="""

    def set_place_button(self, value):
        self.state.setValue("place_button", value)
    
    def get_place_button(self, fallback=None):
        return self.state.value('place_button', fallback)

    def set_select_button(self, value):
        self.state.setValue('select_button', value)
    
    def get_select_button(self, fallback=None):
        return self.state.value('select_button', fallback)
