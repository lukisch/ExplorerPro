#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StatusBar - Statusleiste mit Datenschutz-Ampel
"""

from PyQt6.QtWidgets import (
    QStatusBar, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class PrivacyIndicator(QLabel):
    """
    Ampel-Anzeige für Datenschutz-Status
    Basiert auf AmpelTool
    """
    
    clicked = pyqtSignal()
    
    # Status-Farben
    COLORS = {
        'green': '#2ecc71',   # Sicher
        'yellow': '#f1c40f',  # Warnung
        'red': '#e74c3c',     # Blockiert
        'gray': '#95a5a6',    # Inaktiv
    }
    
    TOOLTIPS = {
        'green': '🟢 Datenschutz: Alles OK\nClipboard ist sicher',
        'yellow': '🟡 Datenschutz: Warnung\nPotenziell sensible Daten erkannt',
        'red': '🔴 Datenschutz: Blockiert!\nSensible Daten wurden blockiert',
        'gray': '⚪ Datenschutz-Monitor inaktiv',
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = 'gray'
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_status('green')
    
    def set_status(self, status: str):
        """Setzt den Ampel-Status"""
        if status not in self.COLORS:
            status = 'gray'
        
        self._status = status
        color = self.COLORS[status]
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid {self._darken(color)};
            }}
        """)
        
        self.setToolTip(self.TOOLTIPS[status])
    
    def _darken(self, hex_color: str) -> str:
        """Dunkelt eine Farbe ab"""
        color = QColor(hex_color)
        color = color.darker(120)
        return color.name()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
    
    @property
    def status(self) -> str:
        return self._status


class StatusBarWidget(QStatusBar):
    """
    Erweiterte Statusleiste mit:
    - Datei-Anzahl
    - Speicherplatz
    - Datenschutz-Ampel
    - Sync-Status
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        # Linker Bereich: Pfad und Datei-Count
        self.path_label = QLabel("Bereit")
        self.addWidget(self.path_label, 1)
        
        # Trennlinie
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        self.addWidget(sep1)
        
        # Datei-Count
        self.file_count_label = QLabel("0 Dateien")
        self.addWidget(self.file_count_label)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        self.addWidget(sep2)
        
        # Speicherplatz
        self.space_label = QLabel("0 GB")
        self.addWidget(self.space_label)
        
        # Permanenter Bereich (rechts)
        
        # Sync-Status
        self.sync_label = QLabel("✓")
        self.sync_label.setToolTip("Synchronisierung: Aktuell")
        self.addPermanentWidget(self.sync_label)
        
        # Datenschutz-Ampel
        self.privacy_indicator = PrivacyIndicator()
        self.privacy_indicator.clicked.connect(self._on_privacy_clicked)
        self.addPermanentWidget(self.privacy_indicator)
    
    def update_path(self, path: str):
        """Aktualisiert den Pfad"""
        if len(path) > 60:
            path = "..." + path[-57:]
        self.path_label.setText(f"📁 {path}")
    
    def update_file_count(self, count: int, selected: int = 0):
        """Aktualisiert die Datei-Anzahl"""
        if selected > 0:
            self.file_count_label.setText(f"{selected} von {count} ausgewählt")
        else:
            self.file_count_label.setText(f"{count} Elemente")
    
    def update_space(self, used_bytes: int):
        """Aktualisiert die Speicheranzeige"""
        gb = used_bytes / (1024 ** 3)
        if gb < 1:
            mb = used_bytes / (1024 ** 2)
            self.space_label.setText(f"💾 {mb:.1f} MB")
        else:
            self.space_label.setText(f"💾 {gb:.2f} GB")
    
    def set_privacy_status(self, status: str):
        """Setzt den Datenschutz-Status"""
        self.privacy_indicator.set_status(status)
    
    def set_sync_status(self, syncing: bool):
        """Setzt den Sync-Status"""
        if syncing:
            self.sync_label.setText("🔄")
            self.sync_label.setToolTip("Synchronisierung läuft...")
        else:
            self.sync_label.setText("✓")
            self.sync_label.setToolTip("Synchronisierung: Aktuell")
    
    def _on_privacy_clicked(self):
        """Handler für Klick auf Ampel"""
        status = self.privacy_indicator.status
        # TODO: Privacy-Details-Dialog öffnen
        self.showMessage(f"Datenschutz-Status: {status.upper()}", 3000)
