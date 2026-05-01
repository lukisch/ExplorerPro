from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_sidebar_import() -> None:
    from gui.sidebar import Sidebar

    assert Sidebar.__name__ == "Sidebar"


def test_main_window_import() -> None:
    from gui.main_window import MainWindow

    assert MainWindow.__name__ == "MainWindow"


def test_app_import() -> None:
    from app import ExplorerProApp

    assert ExplorerProApp.__name__ == "ExplorerProApp"
