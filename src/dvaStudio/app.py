import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.styles import APP_QSS
from .ui.save_dialog import install_portuguese_translation


def _icon_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "Icone.png"
    return Path(__file__).parents[2] / "Icone.png"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("DVA Studio Desktop")
    install_portuguese_translation()
    app.setStyleSheet(APP_QSS)
    icon_path = _icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
