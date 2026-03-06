#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SyncManager - Datei-Synchronisation (ProSync-Integration)
Phase 5: Extras
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QFileDialog, QMessageBox, QToolButton, QProgressBar,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QCursor
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
import shutil


class SyncDirection(Enum):
    """Synchronisations-Richtung"""
    SOURCE_TO_TARGET = "source_to_target"
    TARGET_TO_SOURCE = "target_to_source"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(Enum):
    """Konflikt-Lösung"""
    NEWER_WINS = "newer_wins"
    LARGER_WINS = "larger_wins"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    ASK = "ask"


@dataclass
class SyncPair:
    """Repräsentiert ein Sync-Paar"""
    id: str
    name: str
    source: str
    target: str
    direction: str = "source_to_target"
    conflict_resolution: str = "newer_wins"
    exclude_patterns: List[str] = field(default_factory=list)
    include_hidden: bool = False
    enabled: bool = True
    last_sync: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"sync_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        if not self.exclude_patterns:
            self.exclude_patterns = ["*.tmp", "*.bak", "~*", "Thumbs.db", ".DS_Store"]


@dataclass  
class SyncAction:
    """Eine durchzuführende Sync-Aktion"""
    source_path: str
    target_path: str
    action: str  # 'copy', 'delete', 'conflict'
    direction: str  # 'to_target', 'to_source'
    reason: str
    size: int = 0


class SyncWorker(QThread):
    """Background-Thread für Synchronisation"""
    
    progress = pyqtSignal(int, int, str)  # current, total, current_file
    action_found = pyqtSignal(object)      # SyncAction
    finished_scan = pyqtSignal(list)       # List[SyncAction]
    finished_sync = pyqtSignal(int, int)   # synced, errors
    error = pyqtSignal(str)
    
    def __init__(self, sync_pair: SyncPair, dry_run: bool = True):
        super().__init__()
        self.sync_pair = sync_pair
        self.dry_run = dry_run
        self._cancelled = False
        self.actions: List[SyncAction] = []
    
    def run(self):
        try:
            # Phase 1: Analyse
            self._analyze()
            
            if self._cancelled:
                return
            
            self.finished_scan.emit(self.actions)
            
            # Phase 2: Ausführen (wenn kein dry_run)
            if not self.dry_run:
                self._execute()
        
        except Exception as e:
            self.error.emit(str(e))
    
    def _analyze(self):
        """Analysiert Unterschiede zwischen Source und Target"""
        source = Path(self.sync_pair.source)
        target = Path(self.sync_pair.target)
        
        if not source.exists():
            self.error.emit(f"Quellordner existiert nicht: {source}")
            return
        
        # Alle Dateien sammeln
        source_files = self._get_files(source)
        target_files = self._get_files(target) if target.exists() else {}
        
        total = len(source_files) + len(target_files)
        current = 0
        
        # Source -> Target prüfen
        for rel_path, source_info in source_files.items():
            if self._cancelled:
                return
            
            current += 1
            self.progress.emit(current, total, str(rel_path))
            
            target_path = target / rel_path
            target_info = target_files.get(rel_path)
            
            if target_info is None:
                # Datei existiert nicht im Ziel
                action = SyncAction(
                    source_path=str(source / rel_path),
                    target_path=str(target_path),
                    action='copy',
                    direction='to_target',
                    reason='Neu in Quelle',
                    size=source_info['size']
                )
                self.actions.append(action)
                self.action_found.emit(action)
            
            elif source_info['mtime'] > target_info['mtime']:
                # Quelle ist neuer
                action = SyncAction(
                    source_path=str(source / rel_path),
                    target_path=str(target_path),
                    action='copy',
                    direction='to_target',
                    reason='Quelle neuer',
                    size=source_info['size']
                )
                self.actions.append(action)
                self.action_found.emit(action)
            
            elif source_info['mtime'] < target_info['mtime'] and \
                 self.sync_pair.direction == 'bidirectional':
                # Ziel ist neuer (bei bidirektional)
                action = SyncAction(
                    source_path=str(source / rel_path),
                    target_path=str(target_path),
                    action='copy',
                    direction='to_source',
                    reason='Ziel neuer',
                    size=target_info['size']
                )
                self.actions.append(action)
                self.action_found.emit(action)
        
        # Target -> Source prüfen (für neue Dateien im Ziel bei bidirektional)
        if self.sync_pair.direction == 'bidirectional':
            for rel_path, target_info in target_files.items():
                if self._cancelled:
                    return
                
                if rel_path not in source_files:
                    current += 1
                    self.progress.emit(current, total, str(rel_path))
                    
                    action = SyncAction(
                        source_path=str(source / rel_path),
                        target_path=str(target / rel_path),
                        action='copy',
                        direction='to_source',
                        reason='Neu in Ziel',
                        size=target_info['size']
                    )
                    self.actions.append(action)
                    self.action_found.emit(action)
    
    def _get_files(self, folder: Path) -> Dict[str, dict]:
        """Sammelt alle Dateien in einem Ordner"""
        files = {}
        
        for path in folder.rglob('*'):
            if path.is_file():
                # Exclude-Patterns prüfen
                if self._should_exclude(path.name):
                    continue
                
                # Hidden-Files prüfen
                if not self.sync_pair.include_hidden and path.name.startswith('.'):
                    continue
                
                rel_path = path.relative_to(folder)
                try:
                    stat = path.stat()
                    files[rel_path] = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    }
                except:
                    pass
        
        return files
    
    def _should_exclude(self, filename: str) -> bool:
        """Prüft ob Datei ausgeschlossen werden soll"""
        import fnmatch
        for pattern in self.sync_pair.exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False
    
    def _execute(self):
        """Führt die Sync-Aktionen aus"""
        synced = 0
        errors = 0
        
        total = len(self.actions)
        
        for i, action in enumerate(self.actions):
            if self._cancelled:
                break
            
            self.progress.emit(i + 1, total, action.source_path)
            
            try:
                if action.action == 'copy':
                    if action.direction == 'to_target':
                        # Zielordner erstellen
                        target_dir = Path(action.target_path).parent
                        target_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(action.source_path, action.target_path)
                    else:
                        # Source aus Target kopieren
                        source_dir = Path(action.source_path).parent
                        source_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(action.target_path, action.source_path)
                    
                    synced += 1
                
                elif action.action == 'delete':
                    os.remove(action.target_path if action.direction == 'to_target' 
                              else action.source_path)
                    synced += 1
            
            except Exception as e:
                errors += 1
        
        self.finished_sync.emit(synced, errors)
    
    def cancel(self):
        self._cancelled = True


class SyncPairDialog(QDialog):
    """Dialog zum Erstellen/Bearbeiten eines Sync-Paars"""
    
    def __init__(self, sync_pair: SyncPair = None, parent=None):
        super().__init__(parent)
        self.sync_pair = sync_pair or SyncPair(id="", name="", source="", target="")
        self.setWindowTitle("Sync-Paar bearbeiten" if sync_pair else "Neues Sync-Paar")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        # Source
        source_layout = QHBoxLayout()
        self.source_edit = QLineEdit()
        source_btn = QPushButton("...")
        source_btn.setFixedWidth(30)
        source_btn.clicked.connect(lambda: self._browse('source'))
        source_layout.addWidget(self.source_edit)
        source_layout.addWidget(source_btn)
        form.addRow("Quellordner:", source_layout)
        
        # Target
        target_layout = QHBoxLayout()
        self.target_edit = QLineEdit()
        target_btn = QPushButton("...")
        target_btn.setFixedWidth(30)
        target_btn.clicked.connect(lambda: self._browse('target'))
        target_layout.addWidget(self.target_edit)
        target_layout.addWidget(target_btn)
        form.addRow("Zielordner:", target_layout)
        
        # Richtung
        self.direction_combo = QComboBox()
        self.direction_combo.addItems([
            "Quelle → Ziel",
            "Ziel → Quelle",
            "Bidirektional ↔"
        ])
        form.addRow("Richtung:", self.direction_combo)
        
        # Konflikt-Lösung
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems([
            "Neuere Version gewinnt",
            "Größere Datei gewinnt",
            "Quelle gewinnt immer",
            "Ziel gewinnt immer"
        ])
        form.addRow("Bei Konflikten:", self.conflict_combo)
        
        # Hidden Files
        self.hidden_cb = QCheckBox("Versteckte Dateien einbeziehen")
        form.addRow("", self.hidden_cb)
        
        # Exclude Patterns
        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("*.tmp, *.bak, ~* (Komma-getrennt)")
        form.addRow("Ausschließen:", self.exclude_edit)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _browse(self, field: str):
        folder = QFileDialog.getExistingDirectory(self, "Ordner wählen")
        if folder:
            if field == 'source':
                self.source_edit.setText(folder)
            else:
                self.target_edit.setText(folder)
    
    def _load_data(self):
        self.name_edit.setText(self.sync_pair.name)
        self.source_edit.setText(self.sync_pair.source)
        self.target_edit.setText(self.sync_pair.target)
        
        direction_map = {
            'source_to_target': 0,
            'target_to_source': 1,
            'bidirectional': 2
        }
        self.direction_combo.setCurrentIndex(direction_map.get(self.sync_pair.direction, 0))
        
        conflict_map = {
            'newer_wins': 0,
            'larger_wins': 1,
            'source_wins': 2,
            'target_wins': 3
        }
        self.conflict_combo.setCurrentIndex(conflict_map.get(self.sync_pair.conflict_resolution, 0))
        
        self.hidden_cb.setChecked(self.sync_pair.include_hidden)
        self.exclude_edit.setText(", ".join(self.sync_pair.exclude_patterns))
    
    def _save_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Bitte Namen eingeben!")
            return
        if not self.source_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Bitte Quellordner angeben!")
            return
        if not self.target_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Bitte Zielordner angeben!")
            return
        
        self.sync_pair.name = self.name_edit.text().strip()
        self.sync_pair.source = self.source_edit.text().strip()
        self.sync_pair.target = self.target_edit.text().strip()
        
        directions = ['source_to_target', 'target_to_source', 'bidirectional']
        self.sync_pair.direction = directions[self.direction_combo.currentIndex()]
        
        conflicts = ['newer_wins', 'larger_wins', 'source_wins', 'target_wins']
        self.sync_pair.conflict_resolution = conflicts[self.conflict_combo.currentIndex()]
        
        self.sync_pair.include_hidden = self.hidden_cb.isChecked()
        
        exclude_text = self.exclude_edit.text().strip()
        self.sync_pair.exclude_patterns = [p.strip() for p in exclude_text.split(',') if p.strip()]
        
        self.accept()
    
    def get_sync_pair(self) -> SyncPair:
        return self.sync_pair


class SyncPanel(QWidget):
    """
    Sync-Panel für Ordner-Synchronisation
    Basiert auf ProSync
    """
    
    sync_started = pyqtSignal(str)   # Sync-Pair Name
    sync_finished = pyqtSignal(int)  # Anzahl synchronisierter Dateien
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sync_pairs: List[SyncPair] = []
        self.config_path = Path.home() / ".explorerpro" / "sync.json"
        self.sync_worker = None
        
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("🔄 Synchronisation"))
        header.addStretch()
        
        add_btn = QToolButton()
        add_btn.setText("➕")
        add_btn.setToolTip("Neues Sync-Paar")
        add_btn.clicked.connect(self._add_pair)
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Sync-Paare Liste
        self.pair_list = QListWidget()
        self.pair_list.itemDoubleClicked.connect(self._run_sync)
        self.pair_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pair_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.pair_list)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.sync_btn = QPushButton("🔄 Sync starten")
        self.sync_btn.clicked.connect(self._run_selected_sync)
        self.sync_btn.setEnabled(False)
        btn_layout.addWidget(self.sync_btn)
        
        self.preview_btn = QPushButton("👁️ Vorschau")
        self.preview_btn.clicked.connect(self._preview_sync)
        self.preview_btn.setEnabled(False)
        btn_layout.addWidget(self.preview_btn)
        
        layout.addLayout(btn_layout)
        
        # Selection changed
        self.pair_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sync_pairs = [SyncPair(**p) for p in data]
            except:
                self.sync_pairs = []
        
        self._refresh_list()
    
    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [{
            'id': p.id, 'name': p.name, 'source': p.source, 'target': p.target,
            'direction': p.direction, 'conflict_resolution': p.conflict_resolution,
            'exclude_patterns': p.exclude_patterns, 'include_hidden': p.include_hidden,
            'enabled': p.enabled, 'last_sync': p.last_sync
        } for p in self.sync_pairs]
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _refresh_list(self):
        self.pair_list.clear()
        
        for pair in self.sync_pairs:
            direction_icons = {
                'source_to_target': '→',
                'target_to_source': '←',
                'bidirectional': '↔'
            }
            icon = direction_icons.get(pair.direction, '→')
            
            item = QListWidgetItem(f"🔄 {pair.name} {icon}")
            item.setData(Qt.ItemDataRole.UserRole, pair)
            item.setToolTip(f"{pair.source}\n{icon}\n{pair.target}")
            
            if not pair.enabled:
                item.setForeground(Qt.GlobalColor.gray)
            
            self.pair_list.addItem(item)
    
    def _on_selection_changed(self):
        has_selection = self.pair_list.currentItem() is not None
        self.sync_btn.setEnabled(has_selection)
        self.preview_btn.setEnabled(has_selection)
    
    def _add_pair(self):
        dialog = SyncPairDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pair = dialog.get_sync_pair()
            self.sync_pairs.append(pair)
            self._save_config()
            self._refresh_list()
    
    def _edit_pair(self, pair: SyncPair):
        dialog = SyncPairDialog(pair, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_config()
            self._refresh_list()
    
    def _delete_pair(self, pair: SyncPair):
        if QMessageBox.question(
            self, "Löschen",
            f"'{pair.name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.sync_pairs.remove(pair)
            self._save_config()
            self._refresh_list()
    
    def _preview_sync(self):
        """Zeigt Vorschau der Sync-Aktionen"""
        item = self.pair_list.currentItem()
        if not item:
            return
        
        pair = item.data(Qt.ItemDataRole.UserRole)
        self._start_sync(pair, dry_run=True)
    
    def _run_selected_sync(self):
        """Führt Sync für ausgewähltes Paar aus"""
        item = self.pair_list.currentItem()
        if not item:
            return
        
        pair = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Synchronisation starten",
            f"'{pair.name}' synchronisieren?\n\n"
            f"Quelle: {pair.source}\n"
            f"Ziel: {pair.target}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_sync(pair, dry_run=False)
    
    def _run_sync(self, item: QListWidgetItem):
        """Doppelklick startet Vorschau"""
        self._preview_sync()
    
    def _start_sync(self, pair: SyncPair, dry_run: bool = True):
        """Startet Sync-Worker"""
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.cancel()
            self.sync_worker.wait()
        
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.sync_btn.setEnabled(False)
        
        mode = "Vorschau" if dry_run else "Sync"
        self.status_label.setText(f"{mode}: Analysiere...")
        self.sync_started.emit(pair.name)
        
        self.sync_worker = SyncWorker(pair, dry_run)
        self.sync_worker.progress.connect(self._on_progress)
        self.sync_worker.finished_scan.connect(
            lambda actions: self._on_scan_finished(actions, dry_run, pair)
        )
        self.sync_worker.finished_sync.connect(self._on_sync_finished)
        self.sync_worker.error.connect(self._on_error)
        self.sync_worker.start()
    
    @pyqtSlot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))
        self.status_label.setText(f"Prüfe: {Path(filename).name}")
    
    def _on_scan_finished(self, actions: list, dry_run: bool, pair: SyncPair):
        self.progress_bar.hide()
        self.sync_btn.setEnabled(True)
        
        if not actions:
            self.status_label.setText("✅ Alles synchron!")
            return
        
        if dry_run:
            # Vorschau anzeigen
            self._show_preview_dialog(actions, pair)
        else:
            pair.last_sync = datetime.now().isoformat()
            self._save_config()
    
    def _on_sync_finished(self, synced: int, errors: int):
        self.progress_bar.hide()
        self.sync_btn.setEnabled(True)
        
        if errors:
            self.status_label.setText(f"⚠️ {synced} synchronisiert, {errors} Fehler")
        else:
            self.status_label.setText(f"✅ {synced} Dateien synchronisiert")
        
        self.sync_finished.emit(synced)
    
    def _on_error(self, error: str):
        self.progress_bar.hide()
        self.sync_btn.setEnabled(True)
        self.status_label.setText(f"❌ Fehler: {error}")
    
    def _show_preview_dialog(self, actions: list, pair: SyncPair):
        """Zeigt Vorschau-Dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Sync-Vorschau: {pair.name}")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"📊 {len(actions)} Änderungen gefunden:"))
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Aktion", "Datei", "Richtung", "Grund"])
        table.setRowCount(len(actions))
        table.setAlternatingRowColors(True)
        
        for i, action in enumerate(actions):
            table.setItem(i, 0, QTableWidgetItem(action.action))
            table.setItem(i, 1, QTableWidgetItem(Path(action.source_path).name))
            table.setItem(i, 2, QTableWidgetItem(action.direction))
            table.setItem(i, 3, QTableWidgetItem(action.reason))
        
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        sync_btn = QPushButton("🔄 Jetzt synchronisieren")
        sync_btn.clicked.connect(lambda: self._execute_from_preview(pair, dialog))
        btn_layout.addWidget(sync_btn)
        
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()
    
    def _execute_from_preview(self, pair: SyncPair, dialog: QDialog):
        dialog.close()
        self._start_sync(pair, dry_run=False)
    
    def _show_context_menu(self, pos):
        item = self.pair_list.itemAt(pos)
        if not item:
            return
        
        pair = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        
        menu.addAction("🔄 Sync starten", lambda: self._start_sync(pair, False))
        menu.addAction("👁️ Vorschau", lambda: self._start_sync(pair, True))
        menu.addSeparator()
        menu.addAction("✏️ Bearbeiten", lambda: self._edit_pair(pair))
        menu.addSeparator()
        menu.addAction("🗑️ Löschen", lambda: self._delete_pair(pair))
        
        menu.exec(QCursor.pos())
