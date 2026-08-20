import sys
from pathlib import Path

# Add src directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# from src.gui.main_window import MainWindow
from src.core.config import Config
from src.utils.logger import setup_logging


def main():
    """Main application entry point"""
    # Fix for "sys.stderr is None" in PyInstaller windowed mode
    if sys.stderr is None:
        LOG_FILE = Path("scanlation_tool.log")
        sys.stderr = open(LOG_FILE, "a")
        sys.stdout = open(LOG_FILE, "a")

    import faulthandler
    # Enable faulthandler, directing output to stderr (now safe)
    faulthandler.enable(file=sys.stderr)

    setup_logging()

    # Configure Model Cache (Force local storage for portability)
    # This ensures "Download Models" checks align with where models are actually stored
    import os
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent

    models_dir = base_dir / "models"
    hf_dir = models_dir / "huggingface"
    hf_dir.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(hf_dir)
    os.environ["TRANSFORMERS_CACHE"] = str(hf_dir)

    # Set Torch Hub and Ultralytics dirs
    torch_dir = models_dir / "torch"
    torch_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TORCH_HOME"] = str(torch_dir)

    yolo_dir = models_dir / "yolo"
    yolo_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(yolo_dir)  # Redirect Ultralytics settings

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    # Show Splash Screen
    from src.gui.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    splash.show_message("Initializing configuration...")

    # Initialize Config and theme (simulate heavy loading if fast)
    config = Config()
    config.initialize_dirs()

    from src.utils.theme import apply_dark_theme
    splash.show_message("Applying theme...")
    apply_dark_theme(app)

    # Load main window
    splash.show_message("Starting UI...")
    from src.gui.main_window import MainWindow
    window = MainWindow()

    # Simulate a brief moment to let user see splash if it's too fast
    import time
    time.sleep(1.5)

    window.show()
    splash.finish(window)

    sys.exit(app.exec())

if __name__ == "__main__":
    # CRITICAL: Fix for multiprocessing (PyTorch/YOLO) in frozen EXE
    # Without this, the app will spawn infinite new instances (restart loop)
    import multiprocessing
    multiprocessing.freeze_support()

    main()
