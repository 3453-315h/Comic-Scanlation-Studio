"""
Splash Screen - Comic Scanlation Studio

Displays the application logo during startup.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen


class SplashScreen(QSplashScreen):
    def __init__(self):
        # Load splash image
        splash_path = Path(__file__).parent.parent.parent / "assets" / "splash.png"
        if not splash_path.exists():
            # Fallback if no splash image
            pixmap = QPixmap(600, 400)
            pixmap.fill(QColor(40, 44, 52))
        else:
            pixmap = QPixmap(str(splash_path))

            # Scale if too large, but keep aspect ratio
            if pixmap.width() > 800:
                pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)

        super().__init__(pixmap)

        # UI settings
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.showMessage("Loading...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, QColor("white"))

    def show_message(self, message):
        """Update splash message"""
        self.showMessage(message, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, QColor("black"))
        QApplication.processEvents()
