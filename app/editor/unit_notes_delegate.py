from PyQt5.QtWidgets import QLineEdit, QItemDelegate

from app.extensions.list_models import DoubleListModel

class UnitNotesDelegate(QItemDelegate):
    category_column = 0
    entries_column = 1

    def createEditor(self, parent, option, index):
        if index.column() == self.category_column:
            editor = QLineEdit(parent)
            return editor
        elif index.column() == self.entries_column:
            editor = QLineEdit(parent)
            return editor
        else:
            return super().createEditor(parent, option, index)

class UnitNotesDoubleListModel(DoubleListModel):
    """
    Handles a simple list of 2-tuples/lists where
    both values are strings that can be edited
    """
    def create_new(self):
        new_category = "New Category"
        new_entry = "New Entry"
        self._data.append([new_category, new_entry])
