#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SettingsManager - Einstellungsverwaltung für ExplorerPro
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from PyQt6.QtCore import QSettings, QStandardPaths


class SettingsManager:
    """
    Verwaltet alle Anwendungseinstellungen.
    Unterstützt sowohl QSettings (Registry/plist) als auch JSON-Dateien.
    """
    
    _instance = None
    
    # Standard-Einstellungen
    DEFAULTS = {
        "general": {
            "start_folder": "",  # Leer = Benutzer-Home
            "show_hidden_files": False,
            "confirm_delete": True,
            "remember_window_size": True,
        },
        "index": {
            "auto_index": True,
            "index_on_startup": False,
            "watched_folders": [],
            "excluded_patterns": ["*.tmp", "~*", "Thumbs.db", ".DS_Store"],
            "max_file_size_mb": 100,
        },
        "preview": {
            "show_preview": True,
            "preview_images": True,
            "preview_pdfs": True,
            "preview_code": True,
            "max_preview_size_mb": 10,
        },
        "privacy": {
            "enable_clipboard_monitor": True,
            "auto_block_sensitive": True,
            "blacklist_patterns": [],
            "show_notifications": True,
        },
        "appearance": {
            "theme": "system",  # system, light, dark
            "font_size": 10,
            "icon_size": 24,
        },
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._qsettings = QSettings("ExplorerPro", "ExplorerPro")
        self._config_path = self._get_config_path()
        self._settings: Dict[str, Any] = {}
        
        self._load_settings()
    
    def _get_config_path(self) -> Path:
        """Ermittelt den Konfigurationspfad"""
        config_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        if not config_dir:
            config_dir = os.path.expanduser("~/.explorerpro")
        path = Path(config_dir) / "ExplorerPro"
        path.mkdir(parents=True, exist_ok=True)
        return path / "settings.json"
    
    def _load_settings(self):
        """Lädt Einstellungen aus JSON-Datei"""
        self._settings = self._deep_copy(self.DEFAULTS)
        
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self._merge_settings(self._settings, saved)
            except Exception as e:
                print(f"Fehler beim Laden der Einstellungen: {e}")
    
    def _deep_copy(self, d: Dict) -> Dict:
        """Tiefe Kopie eines Dicts"""
        return json.loads(json.dumps(d))
    
    def _merge_settings(self, target: Dict, source: Dict):
        """Merged source in target (rekursiv)"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_settings(target[key], value)
            else:
                target[key] = value
    
    def save(self):
        """Speichert Einstellungen in JSON-Datei"""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Holt eine Einstellung"""
        try:
            return self._settings[section][key]
        except KeyError:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Setzt eine Einstellung"""
        if section not in self._settings:
            self._settings[section] = {}
        self._settings[section][key] = value
    
    def get_section(self, section: str) -> Dict:
        """Holt eine ganze Sektion"""
        return self._settings.get(section, {})
    
    @property
    def config_dir(self) -> Path:
        """Gibt das Konfigurationsverzeichnis zurück"""
        return self._config_path.parent
    
    @classmethod
    def instance(cls) -> 'SettingsManager':
        """Gibt die Singleton-Instanz zurück"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Globale Instanz
settings = SettingsManager.instance()
