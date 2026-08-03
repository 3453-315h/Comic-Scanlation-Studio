
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDockWidget, QPlainTextEdit, QVBoxLayout, QWidget


class QLogHandler(logging.Handler, QObject):
    """Custom logging handler sending logs to a signal"""
    log_signal = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

class LogConsole(QDockWidget):
    """Dockable Log Console"""

    def __init__(self, parent=None):
        super().__init__("Log Console", parent)
        self.setWidget(QWidget())
        self.init_ui()
        self.setup_logging()

    def init_ui(self):
        layout = QVBoxLayout(self.widget())
        layout.setContentsMargins(0, 0, 0, 0)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, "Courier New", monospace;
                font-size: 10pt;
                border: none;
            }
        """)
        layout.addWidget(self.text_edit)

    def setup_logging(self):
        self.handler = QLogHandler()
        self.handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.handler.log_signal.connect(self.append_log)

        # Attach to root logger
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.INFO)

    def append_log(self, msg):
        self.text_edit.appendPlainText(msg)
        self.text_edit.moveCursor(self.text_edit.textCursor().MoveOperation.End)
