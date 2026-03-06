#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EventBus - Zentrale Event-Verteilung für ExplorerPro
Ermöglicht lose Kopplung zwischen Komponenten
"""

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, List, Callable


class EventBus(QObject):
    """
    Zentraler Event-Bus für die Anwendung.
    Singleton-Pattern für globalen Zugriff.
    """
    
    # Singleton-Instanz
    _instance = None
    
    # Standard-Events
    file_selected = pyqtSignal(str)           # Datei ausgewählt
    folder_changed = pyqtSignal(str)          # Ordner gewechselt
    search_requested = pyqtSignal(str)        # Suche angefordert
    search_results = pyqtSignal(list)         # Suchergebnisse
    index_updated = pyqtSignal()              # Index aktualisiert
    privacy_status_changed = pyqtSignal(str)  # Ampel-Status (green/yellow/red)
    file_indexed = pyqtSignal(str)            # Einzelne Datei indiziert
    error_occurred = pyqtSignal(str)          # Fehler aufgetreten
    status_message = pyqtSignal(str, int)     # Statusnachricht (text, timeout_ms)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._custom_handlers: Dict[str, List[Callable]] = {}
    
    @classmethod
    def instance(cls) -> 'EventBus':
        """Gibt die Singleton-Instanz zurück"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def emit_status(self, message: str, timeout: int = 3000):
        """Sendet eine Statusnachricht"""
        self.status_message.emit(message, timeout)
    
    def emit_error(self, message: str):
        """Sendet eine Fehlermeldung"""
        self.error_occurred.emit(message)
    
    # Custom Events für Erweiterbarkeit
    def register_handler(self, event_name: str, handler: Callable):
        """Registriert einen Handler für ein benutzerdefiniertes Event"""
        if event_name not in self._custom_handlers:
            self._custom_handlers[event_name] = []
        self._custom_handlers[event_name].append(handler)
    
    def unregister_handler(self, event_name: str, handler: Callable):
        """Entfernt einen Handler"""
        if event_name in self._custom_handlers:
            self._custom_handlers[event_name].remove(handler)
    
    def emit_custom(self, event_name: str, *args, **kwargs):
        """Sendet ein benutzerdefiniertes Event"""
        if event_name in self._custom_handlers:
            for handler in self._custom_handlers[event_name]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    self.emit_error(f"Handler-Fehler: {e}")


# Lazy globale Instanz - wird erst bei erstem Zugriff erstellt
_event_bus = None

def get_event_bus() -> EventBus:
    """Gibt die EventBus-Instanz zurück (lazy initialization)"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus.instance()
    return _event_bus
