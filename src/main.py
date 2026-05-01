#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro - Ein intelligenter Datei-Explorer
Fusion aus ProFiler, PythonBox, ProSync, AmpelTool, SoftwareCenter, ProfiPrompt

Version: 0.1.0
"""

import sys
import os
from pathlib import Path

# Encoding für Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app import ExplorerProApp


def load_app_icon() -> QIcon:
    candidates = [
        Path(sys.executable).with_name("ExplorerPro.ico") if getattr(sys, "frozen", False) else None,
        Path(__file__).resolve().parent.parent / "ExplorerPro.ico",
        Path(__file__).resolve().parent / "ExplorerPro.ico",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return QIcon(str(candidate))
    return QIcon()


def main():
    """Haupteinstiegspunkt für ExplorerPro"""
    # High DPI Support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("ExplorerPro")
    app.setOrganizationName("ExplorerPro")
    app.setApplicationVersion("0.1.0")
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    
    # Style
    app.setStyle("Fusion")
    
    # Dark Theme (optional)
    # from gui.themes import apply_dark_theme
    # apply_dark_theme(app)
    
    # Hauptfenster starten
    explorer = ExplorerProApp()
    if not icon.isNull():
        explorer.setWindowIcon(icon)
    explorer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
