#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrivacyMonitor - Datenschutz-Clipboard-Monitor
Basiert auf AmpelTool V6

Überwacht das Clipboard auf sensible Daten und sendet Status-Updates.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

logging.basicConfig(level=logging.INFO)


class PrivacyStatus(Enum):
    """Ampel-Status für Datenschutz"""
    GREEN = "green"     # Alles OK
    YELLOW = "yellow"   # Warnung (potenziell sensibel)
    RED = "red"         # Blockiert (sensible Daten erkannt)
    GRAY = "gray"       # Monitor inaktiv


@dataclass
class PrivacyAlert:
    """Datenschutz-Warnung"""
    status: PrivacyStatus
    message: str
    detected_patterns: List[str]
    original_text: str
    anonymized_text: str


# Eingebaute Regex-Patterns für sensible Daten
BUILTIN_PATTERNS = {
    "iban": {
        "name": "IBAN (Kontonummer)",
        "regex": r"\b[A-Z]{2}\d{2}[\s]?(?:\d{4}[\s]?){4,7}\d{0,2}\b",
        "description": "Deutsche/EU Kontonummern",
        "default": True,
        "severity": "high"
    },
    "email": {
        "name": "E-Mail Adressen",
        "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "description": "name@domain.de",
        "default": True,
        "severity": "medium"
    },
    "phone_de": {
        "name": "Telefonnummern (DE)",
        "regex": r"\b(?:\+49|0049|0)[\s.-]?(?:\d{2,4})[\s.-]?(?:\d{3,})[\s.-]?(?:\d{2,})\b",
        "description": "+49 170 1234567",
        "default": False,
        "severity": "medium"
    },
    "creditcard": {
        "name": "Kreditkarten",
        "regex": r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
        "description": "1234 5678 9012 3456",
        "default": False,
        "severity": "high"
    },
    "ssn_de": {
        "name": "Sozialversicherungsnr.",
        "regex": r"\b\d{2}\s?\d{6}\s?[A-Z]\s?\d{3}\b",
        "description": "Deutsche SVN",
        "default": False,
        "severity": "high"
    },
    "password_hint": {
        "name": "Passwort-Hinweise",
        "regex": r"(?i)(passwort|password|kennwort|pin|geheim)[\s:=]+\S+",
        "description": "Passwort: xyz",
        "default": False,
        "severity": "high"
    }
}


class PrivacyMonitor(QObject):
    """
    Überwacht das Clipboard auf sensible Daten.
    Sendet Signale bei Änderungen des Datenschutz-Status.
    """
    
    # Signale
    status_changed = pyqtSignal(str)        # 'green', 'yellow', 'red', 'gray'
    warning = pyqtSignal(str)               # Warnmeldung
    alert = pyqtSignal(object)              # PrivacyAlert Objekt
    clipboard_processed = pyqtSignal(str, str)  # original, anonymized
    
    def __init__(self, config_dir: Optional[Path] = None):
        super().__init__()
        
        # Konfiguration
        self.config_dir = config_dir or Path.home() / ".explorerpro"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / "privacy_config.json"
        
        # Listen
        self.blacklist: Set[str] = set()    # Sensible Begriffe
        self.whitelist: Set[str] = set()    # Erlaubte Begriffe
        
        # Pattern-Status
        self.pattern_enabled: Dict[str, bool] = {
            key: info["default"] for key, info in BUILTIN_PATTERNS.items()
        }
        
        # Kompilierte Patterns
        self.compiled_patterns: List[re.Pattern] = []
        
        # Status
        self._enabled = True
        self._current_status = PrivacyStatus.GREEN
        self._clipboard_lock = False
        self._auto_clear = False  # Bei ROT automatisch löschen
        
        # Optionen
        self.case_sensitive = False
        self.whole_words = False
        
        # Clipboard
        self.clipboard = None
        
        # Laden & Kompilieren
        self._load_config()
        self._compile_patterns()
    
    def start(self):
        """Startet die Clipboard-Überwachung"""
        if self.clipboard is None:
            app = QApplication.instance()
            if app:
                self.clipboard = app.clipboard()
                self.clipboard.dataChanged.connect(self._on_clipboard_change)
                logging.info("PrivacyMonitor gestartet")
                self.status_changed.emit(self._current_status.value)
    
    def stop(self):
        """Stoppt die Überwachung"""
        if self.clipboard:
            try:
                self.clipboard.dataChanged.disconnect(self._on_clipboard_change)
            except:
                pass
        self._enabled = False
        self._current_status = PrivacyStatus.GRAY
        self.status_changed.emit('gray')
        logging.info("PrivacyMonitor gestoppt")
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        if value:
            self.start()
        else:
            self.stop()
    
    @property
    def status(self) -> str:
        return self._current_status.value
    
    # ===== Konfiguration =====
    
    def _load_config(self):
        """Lädt die Konfiguration"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                
                self.blacklist = set(cfg.get('blacklist', []))
                self.whitelist = set(cfg.get('whitelist', []))
                self.pattern_enabled = cfg.get('patterns', self.pattern_enabled)
                self.case_sensitive = cfg.get('case_sensitive', False)
                self.whole_words = cfg.get('whole_words', False)
                self._auto_clear = cfg.get('auto_clear', False)
                
                logging.info(f"Konfiguration geladen: {len(self.blacklist)} Blacklist, {len(self.whitelist)} Whitelist")
            except Exception as e:
                logging.error(f"Fehler beim Laden der Config: {e}")
    
    def save_config(self):
        """Speichert die Konfiguration"""
        cfg = {
            'blacklist': list(self.blacklist),
            'whitelist': list(self.whitelist),
            'patterns': self.pattern_enabled,
            'case_sensitive': self.case_sensitive,
            'whole_words': self.whole_words,
            'auto_clear': self._auto_clear
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            logging.info("Konfiguration gespeichert")
        except Exception as e:
            logging.error(f"Fehler beim Speichern: {e}")
    
    # ===== Pattern-Management =====
    
    def _compile_patterns(self):
        """Kompiliert alle aktiven Patterns"""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self.compiled_patterns = []
        
        # 1. Blacklist-Begriffe
        for item in self.blacklist:
            if item in self.whitelist:
                continue
            
            escaped = re.escape(item)
            pattern = rf"(?<!\w){escaped}(?!\w)" if self.whole_words else escaped
            
            try:
                self.compiled_patterns.append((
                    re.compile(pattern, flags),
                    "blacklist",
                    item
                ))
            except re.error:
                pass
        
        # 2. Eingebaute Patterns
        for key, enabled in self.pattern_enabled.items():
            if enabled and key in BUILTIN_PATTERNS:
                info = BUILTIN_PATTERNS[key]
                try:
                    self.compiled_patterns.append((
                        re.compile(info["regex"], flags),
                        info["severity"],
                        info["name"]
                    ))
                except re.error as e:
                    logging.error(f"Pattern-Fehler ({key}): {e}")
        
        logging.info(f"{len(self.compiled_patterns)} Patterns kompiliert")
    
    def set_pattern_enabled(self, pattern_key: str, enabled: bool):
        """Aktiviert/Deaktiviert ein Pattern"""
        if pattern_key in BUILTIN_PATTERNS:
            self.pattern_enabled[pattern_key] = enabled
            self._compile_patterns()
            self.save_config()
    
    # ===== Blacklist/Whitelist =====
    
    def add_to_blacklist(self, term: str):
        """Fügt einen Begriff zur Blacklist hinzu"""
        term = term.strip()
        if term:
            self.blacklist.add(term)
            self._compile_patterns()
            self.save_config()
    
    def remove_from_blacklist(self, term: str):
        """Entfernt einen Begriff aus der Blacklist"""
        self.blacklist.discard(term)
        self._compile_patterns()
        self.save_config()
    
    def add_to_whitelist(self, term: str):
        """Fügt einen Begriff zur Whitelist hinzu"""
        term = term.strip()
        if term:
            self.whitelist.add(term)
            self._compile_patterns()
            self.save_config()
    
    def remove_from_whitelist(self, term: str):
        """Entfernt einen Begriff aus der Whitelist"""
        self.whitelist.discard(term)
        self._compile_patterns()
        self.save_config()
    
    def import_blacklist(self, terms: List[str]):
        """Importiert mehrere Begriffe in die Blacklist"""
        for term in terms:
            term = term.strip()
            if term:
                self.blacklist.add(term)
        self._compile_patterns()
        self.save_config()
    
    # ===== Prüfung & Anonymisierung =====
    
    def check_text(self, text: str) -> PrivacyAlert:
        """
        Prüft einen Text auf sensible Daten.
        Gibt ein PrivacyAlert-Objekt zurück.
        """
        if not text or not self._enabled:
            return PrivacyAlert(
                status=PrivacyStatus.GREEN,
                message="OK",
                detected_patterns=[],
                original_text=text or "",
                anonymized_text=text or ""
            )
        
        detected = []
        anonymized = text
        
        # Whitelist-Check
        text_lower = text.lower()
        for white_term in self.whitelist:
            if white_term.lower() in text_lower:
                # Whitelisted → als sicher markieren
                pass
        
        # Pattern-Check
        for pattern, severity, name in self.compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                detected.append(f"{name}: {len(matches)}x")
                anonymized = pattern.sub("[***]", anonymized)
        
        # Status bestimmen
        if not detected:
            status = PrivacyStatus.GREEN
            message = "Keine sensiblen Daten erkannt"
        else:
            # Prüfe Severity
            has_high = any(sev == "high" for _, sev, _ in self.compiled_patterns 
                          if any(pat.search(text) for pat, s, n in [(_, sev, _)] 
                                if s == "high"))
            
            if has_high or len(detected) > 2:
                status = PrivacyStatus.RED
                message = f"WARNUNG: {len(detected)} sensible Muster erkannt!"
            else:
                status = PrivacyStatus.YELLOW
                message = f"Hinweis: {len(detected)} Muster erkannt"
        
        return PrivacyAlert(
            status=status,
            message=message,
            detected_patterns=detected,
            original_text=text,
            anonymized_text=anonymized
        )
    
    def anonymize(self, text: str) -> str:
        """Anonymisiert einen Text"""
        if not text:
            return ""
        
        result = text
        for pattern, severity, name in self.compiled_patterns:
            result = pattern.sub("[***]", result)
        
        return result
    
    # ===== Clipboard-Überwachung =====
    
    def _on_clipboard_change(self):
        """Handler für Clipboard-Änderungen"""
        if self._clipboard_lock or not self._enabled:
            return
        
        if not self.clipboard:
            return
        
        mime_data = self.clipboard.mimeData()
        if not mime_data.hasText():
            return
        
        text = mime_data.text()
        if not text:
            return
        
        # Text prüfen
        alert = self.check_text(text)
        
        # Status aktualisieren
        if alert.status != self._current_status:
            self._current_status = alert.status
            self.status_changed.emit(alert.status.value)
        
        # Warnung senden
        if alert.status in (PrivacyStatus.YELLOW, PrivacyStatus.RED):
            self.warning.emit(alert.message)
            self.alert.emit(alert)
            
            # Bei ROT und auto_clear: Clipboard leeren
            if alert.status == PrivacyStatus.RED and self._auto_clear:
                self._clipboard_lock = True
                self.clipboard.clear()
                self._clipboard_lock = False
                logging.warning(f"Clipboard geleert: {alert.message}")
        
        # Verarbeitetes Signal
        self.clipboard_processed.emit(text, alert.anonymized_text)
    
    def clear_clipboard(self):
        """Leert das Clipboard"""
        if self.clipboard:
            self._clipboard_lock = True
            self.clipboard.clear()
            self._clipboard_lock = False
    
    # ===== Hilfsmethoden =====
    
    def get_pattern_info(self) -> Dict[str, dict]:
        """Gibt Informationen über alle Patterns zurück"""
        info = {}
        for key, pattern_info in BUILTIN_PATTERNS.items():
            info[key] = {
                **pattern_info,
                "enabled": self.pattern_enabled.get(key, pattern_info["default"])
            }
        return info
    
    def get_stats(self) -> dict:
        """Gibt Statistiken zurück"""
        return {
            "blacklist_count": len(self.blacklist),
            "whitelist_count": len(self.whitelist),
            "active_patterns": sum(1 for v in self.pattern_enabled.values() if v),
            "total_patterns": len(BUILTIN_PATTERNS),
            "status": self._current_status.value
        }
