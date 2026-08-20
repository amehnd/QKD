import sys
from PySide6.QtGui import QTextCursor


class Logger:

    def __init__(self):
        self.enabled = True
        self.widgets = []

    def attach(self, widget):
        if widget not in self.widgets:
            self.widgets.append(widget)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def clear(self):
        for widget in self.widgets:
            widget.clear()

    def write(self, text):
        if not self.enabled or not text:
            return

        for widget in self.widgets:
            widget.moveCursor(QTextCursor.End)
            widget.insertPlainText(text)
            widget.ensureCursorVisible()

    def flush(self):
        pass


logger = Logger()
