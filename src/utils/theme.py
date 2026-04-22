
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

def apply_dark_theme(app: QApplication):
    """Apply generic Dark Theme using Fusion style"""
    app.setStyle("Fusion")
    
    palette = QPalette()
    
    # Base colors
    dark_gray = QColor(53, 53, 53)
    gray = QColor(128, 128, 128)
    black = QColor(25, 25, 25)
    blue = QColor(42, 130, 218)
    
    # Text colors
    white = QColor(255, 255, 255)
    
    palette.setColor(QPalette.Window, dark_gray)
    palette.setColor(QPalette.WindowText, white)
    palette.setColor(QPalette.Base, black)
    palette.setColor(QPalette.AlternateBase, dark_gray)
    palette.setColor(QPalette.ToolTipBase, white)
    palette.setColor(QPalette.ToolTipText, white)
    palette.setColor(QPalette.Text, white)
    palette.setColor(QPalette.Button, dark_gray)
    palette.setColor(QPalette.ButtonText, white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, blue)
    palette.setColor(QPalette.Highlight, blue)
    palette.setColor(QPalette.HighlightedText, black)
    
    # Disabled state
    palette.setColor(QPalette.Disabled, QPalette.Text, gray)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, gray)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, gray)
    
    app.setPalette(palette)
    
    # Optional: Stylesheet for specific improvements
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QDockWidget::title {
            background: #353535;
            text-align: center;
        }
        QListWidget {
            border: 1px solid #444;
            border-radius: 4px;
        }
    """)
