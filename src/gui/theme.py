"""
Theme System - 8-bit-magic-wand Style

Dark/light mode theming matching the modern 8-bit-magic-wand aesthetic.
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

# Color definitions matching 8-bit-magic-wand
DARK_THEME = {
    "bg_color": "#1C1F21",
    "bg_secondary": "#101214",
    "accent_color": "#7FBBFF",
    "accent_hover": "#3B68FF",
    "border_color": "#37393c",
    "box_color": "#141619",
    "text_primary": "#FFFFFF",
    "text_secondary": "#8c8d8e",
    "input_color": "#404547",
    "success": "#4CAF50",
    "error": "#f44336",
    "warning": "#ff9800",
}

LIGHT_THEME = {
    "bg_color": "#F3F3F6",
    "bg_secondary": "#FFFFFF",
    "accent_color": "#2872E3",
    "accent_hover": "#2850D9",
    "border_color": "#C6C6C9",
    "box_color": "#FFFFFF",
    "text_primary": "#1E1E1E",
    "text_secondary": "#888D8F",
    "input_color": "#F9F9FC",
    "success": "#4CAF50",
    "error": "#d32f2f",
    "warning": "#ed6c02",
}


def get_stylesheet(dark: bool = True) -> str:
    """Generate Qt stylesheet for the application"""
    theme = DARK_THEME if dark else LIGHT_THEME
    
    return f"""
    /* Global Styles */
    QMainWindow, QWidget {{
        background-color: {theme['bg_color']};
        color: {theme['text_primary']};
        font-family: 'Segoe UI', 'Arial', sans-serif;
        font-size: 13px;
    }}
    
    /* Top Bar */
    #TopBar {{
        background-color: {theme['bg_secondary']};
        border-bottom: 1px solid {theme['border_color']};
        padding: 8px 12px;
    }}
    
    #TopBar QPushButton {{
        background: transparent;
        border: none;
        color: {theme['text_primary']};
        padding: 6px 12px;
        border-radius: 4px;
    }}
    
    #TopBar QPushButton:hover {{
        background-color: {theme['border_color']};
    }}
    
    #ProjectTitle {{
        font-weight: bold;
        font-size: 14px;
        color: {theme['text_primary']};
    }}
    
    /* Editor Panel (Right Sidebar) */
    #EditorPanel {{
        background-color: {theme['bg_color']};
        border-left: 1px solid {theme['border_color']};
        min-width: 280px;
        max-width: 360px;
    }}
    
    #EditorPanel QLabel {{
        color: {theme['text_secondary']};
        font-size: 11px;
        text-transform: uppercase;
        font-weight: bold;
        margin-top: 12px;
    }}
    
    /* Workflow Buttons */
    .workflow-button {{
        background-color: {theme['box_color']};
        border: 1px solid {theme['border_color']};
        border-radius: 8px;
        padding: 14px 20px;
        min-height: 48px;
        text-align: left;
        color: {theme['text_primary']};
    }}
    
    .workflow-button:hover {{
        border-color: {theme['accent_color']};
    }}
    
    .workflow-button:pressed {{
        background-color: {theme['accent_color']};
    }}
    
    .workflow-button-active {{
        border-color: {theme['accent_color']};
        background-color: {theme['accent_hover']};
    }}
    
    /* Primary Button */
    QPushButton#PrimaryButton {{
        background-color: {theme['accent_hover']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 14px 24px;
        font-weight: bold;
    }}
    
    QPushButton#PrimaryButton:hover {{
        background-color: {theme['accent_color']};
    }}
    
    /* Page Carousel (Bottom Bar) */
    #BottomBar {{
        background-color: {theme['bg_color']};
        border-top: 1px solid {theme['border_color']};
        padding: 12px;
    }}
    
    #PageCarousel {{
        background-color: transparent;
    }}
    
    #PageThumbnail {{
        border: 2px solid transparent;
        border-radius: 8px;
    }}
    
    #PageThumbnail:hover {{
        border-color: {theme['text_secondary']};
    }}
    
    #PageThumbnail[active="true"] {{
        border-color: {theme['accent_color']};
        border-width: 3px;
    }}
    
    /* Image Viewer */
    #ImageViewer {{
        background-color: {theme['bg_secondary']};
        border: none;
    }}
    
    /* Scroll Areas */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    QScrollBar:horizontal {{
        background-color: {theme['bg_color']};
        height: 8px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {theme['border_color']};
        border-radius: 4px;
        min-width: 40px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {theme['text_secondary']};
    }}
    
    QScrollBar:vertical {{
        background-color: {theme['bg_color']};
        width: 8px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {theme['border_color']};
        border-radius: 4px;
        min-height: 40px;
    }}
    
    /* Input Fields */
    QLineEdit, QTextEdit {{
        background-color: {theme['input_color']};
        border: 1px solid {theme['border_color']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {theme['text_primary']};
    }}
    
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {theme['accent_color']};
    }}
    
    /* Combo Box */
    QComboBox {{
        background-color: {theme['input_color']};
        border: 1px solid {theme['border_color']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {theme['text_primary']};
    }}
    
    QComboBox:hover {{
        border-color: {theme['accent_color']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    
    /* Menu Bar (kept for power users) */
    QMenuBar {{
        background-color: {theme['bg_secondary']};
        color: {theme['text_primary']};
        border-bottom: 1px solid {theme['border_color']};
        padding: 4px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {theme['border_color']};
    }}
    
    QMenu {{
        background-color: {theme['bg_color']};
        border: 1px solid {theme['border_color']};
        color: {theme['text_primary']};
        padding: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {theme['accent_color']};
    }}
    
    /* Status Bar */
    QStatusBar {{
        background-color: {theme['bg_secondary']};
        color: {theme['text_secondary']};
        border-top: 1px solid {theme['border_color']};
    }}
    
    /* Dock Widget */
    QDockWidget {{
        background-color: {theme['bg_color']};
        color: {theme['text_primary']};
        titlebar-close-icon: none;
    }}
    
    QDockWidget::title {{
        background-color: {theme['bg_secondary']};
        padding: 8px;
        border-bottom: 1px solid {theme['border_color']};
    }}
    
    /* Progress Bar */
    QProgressBar {{
        background-color: {theme['border_color']};
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}
    
    QProgressBar::chunk {{
        background-color: {theme['accent_color']};
        border-radius: 4px;
    }}
    
    /* Splitter */
    QSplitter::handle {{
        background-color: {theme['border_color']};
    }}
    
    QSplitter::handle:hover {{
        background-color: {theme['accent_color']};
    }}
    """


def apply_theme(app: QApplication, dark: bool = True):
    """Apply theme to the entire application"""
    stylesheet = get_stylesheet(dark)
    app.setStyleSheet(stylesheet)
    
    # Also set the palette for native widgets
    theme = DARK_THEME if dark else LIGHT_THEME
    palette = QPalette()
    
    palette.setColor(QPalette.ColorRole.Window, QColor(theme['bg_color']))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme['text_primary']))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme['input_color']))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme['bg_secondary']))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme['text_primary']))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme['box_color']))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme['text_primary']))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme['accent_color']))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#FFFFFF'))
    palette.setColor(QPalette.ColorRole.Link, QColor(theme['accent_color']))
    
    app.setPalette(palette)


def is_dark_mode_preferred() -> bool:
    """Check if system prefers dark mode"""
    try:
        # Windows 10+ dark mode detection
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        # Default to dark mode
        return True
