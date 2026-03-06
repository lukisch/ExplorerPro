#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuplicateFinder - Findet Datei-Duplikate basierend auf Hash
Phase 2: Index & Suche
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QProgressBar, QGroupBox, QSpinBox,
    QComboBox, QFileDialog, QMessageBox, QHeaderView, QDialogButtonBox,
    QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QCursor
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import os
import hashlib


class DuplicateScanWorker(QThread):
    """Background-Thread für Duplikate-Scan"""
    
    progress = pyqtSignal(int, int, str)   # current, total, current_file
    duplicates_found = pyqtSignal(dict)     # {hash: [paths]}
    error = pyqtSignal(str)
    finished_scan = pyqtSignal(int, int)    # total_files, duplicate_groups
    
    def __init__(self, index=None, scan_path: str = None, min_size: int = 0):
        super().__init__()
        self.index = index
        self.scan_path = scan_path
        self.min_size = min_size
        self._cancelled = False
    
    def run(self):
        try:
            if self.index:
                # Aus Index laden
                duplicates = self._find_from_index()
            elif self.scan_path:
                # Live-Scan durchführen
                duplicates = self._scan_directory()
            else:
                self.error.emit("Kein Index oder Pfad angegeben")
                return
            
            if not self._cancelled:
                # Nur Gruppen mit > 1 Datei
                filtered = {h: paths for h, paths in duplicates.items() if len(paths) > 1}
                self.duplicates_found.emit(filtered)
                self.finished_scan.emit(
                    sum(len(p) for p in duplicates.values()),
                    len(filtered)
                )
        except Exception as e:
            self.error.emit(str(e))
    
    def _find_from_index(self) -> Dict[str, List[str]]:
        """Findet Duplikate aus dem Index"""
        duplicates = defaultdict(list)
        
        cursor = self.index.conn.execute('''
            SELECT hash, path, size
            FROM files
            WHERE hash IS NOT NULL
            AND hash != ''
            AND size >= ?
            ORDER BY hash
        ''', (self.min_size,))
        
        rows = cursor.fetchall()
        total = len(rows)
        
        for i, (file_hash, path, size) in enumerate(rows):
            if self._cancelled:
                break
            
            duplicates[file_hash].append({
                'path': path,
                'size': size
            })
            
            if i % 100 == 0:
                self.progress.emit(i, total, path)
        
        return {
            h: [d['path'] for d in paths] 
            for h, paths in duplicates.items()
        }
    
    def _scan_directory(self) -> Dict[str, List[str]]:
        """Scannt Verzeichnis live nach Duplikaten"""
        duplicates = defaultdict(list)
        
        # Erst alle Dateien sammeln
        all_files = []
        for root, dirs, files in os.walk(self.scan_path):
            for f in files:
                path = os.path.join(root, f)
                try:
                    size = os.path.getsize(path)
                    if size >= self.min_size:
                        all_files.append((path, size))
                except:
                    pass
            
            if self._cancelled:
                break
        
        # Nach Größe gruppieren (Vorfilter)
        size_groups = defaultdict(list)
        for path, size in all_files:
            size_groups[size].append(path)
        
        # Nur Gruppen mit > 1 Datei hashen
        files_to_hash = []
        for size, paths in size_groups.items():
            if len(paths) > 1:
                files_to_hash.extend(paths)
        
        total = len(files_to_hash)
        
        for i, path in enumerate(files_to_hash):
            if self._cancelled:
                break
            
            self.progress.emit(i, total, os.path.basename(path))
            
            try:
                file_hash = self._compute_hash(path)
                duplicates[file_hash].append(path)
            except:
                pass
        
        return dict(duplicates)
    
    def _compute_hash(self, path: str, block_size: int = 65536) -> str:
        """Berechnet SHA-256 Hash einer Datei"""
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                hasher.update(block)
        return hasher.hexdigest()
    
    def cancel(self):
        self._cancelled = True


class DuplicateFinderDialog(QDialog):
    """
    Dialog zum Finden und Verwalten von Datei-Duplikaten
    
    Features:
    - Scan aus Index oder live
    - Gruppierung nach Hash
    - Größen-Filter
    - Auswahl zum Löschen
    - Speicherplatz-Anzeige
    """
    
    def __init__(self, file_index=None, parent=None):
        super().__init__(parent)
        self.file_index = file_index
        self.scan_worker = None
        self.duplicate_groups = {}
        
        self.setWindowTitle("Duplikate finden")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # ===== Optionen =====
        options_group = QGroupBox("Scan-Optionen")
        options_layout = QHBoxLayout(options_group)
        
        # Quelle
        options_layout.addWidget(QLabel("Quelle:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Index (schnell)", "Ordner scannen..."])
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        options_layout.addWidget(self.source_combo)
        
        self.folder_btn = QPushButton("📁 Ordner wählen...")
        self.folder_btn.clicked.connect(self._select_folder)
        self.folder_btn.hide()
        options_layout.addWidget(self.folder_btn)
        
        self.folder_label = QLabel("")
        self.folder_label.hide()
        options_layout.addWidget(self.folder_label)
        
        options_layout.addStretch()
        
        # Min-Größe
        options_layout.addWidget(QLabel("Min. Größe:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 10000)
        self.min_size_spin.setValue(1)
        self.min_size_spin.setSuffix(" KB")
        options_layout.addWidget(self.min_size_spin)
        
        # Scan-Button
        self.scan_btn = QPushButton("🔍 Scan starten")
        self.scan_btn.clicked.connect(self._start_scan)
        options_layout.addWidget(self.scan_btn)
        
        layout.addWidget(options_group)
        
        # ===== Progress =====
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        progress_layout.addWidget(self.progress_label)
        
        self.cancel_btn = QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self._cancel_scan)
        self.cancel_btn.hide()
        progress_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(progress_layout)
        
        # ===== Ergebnisse =====
        results_group = QGroupBox("Gefundene Duplikate")
        results_layout = QVBoxLayout(results_group)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Datei", "Größe", "Pfad"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        # Spaltenbreiten
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(0, 250)
        
        results_layout.addWidget(self.tree)
        
        # Aktionen
        action_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Alle auswählen")
        self.select_all_btn.clicked.connect(self._select_all_duplicates)
        self.select_all_btn.setEnabled(False)
        action_layout.addWidget(self.select_all_btn)
        
        self.select_newest_btn = QPushButton("Neueste behalten")
        self.select_newest_btn.clicked.connect(self._select_keep_newest)
        self.select_newest_btn.setEnabled(False)
        action_layout.addWidget(self.select_newest_btn)
        
        self.select_oldest_btn = QPushButton("Älteste behalten")
        self.select_oldest_btn.clicked.connect(self._select_keep_oldest)
        self.select_oldest_btn.setEnabled(False)
        action_layout.addWidget(self.select_oldest_btn)
        
        action_layout.addStretch()
        
        self.delete_btn = QPushButton("🗑️ Ausgewählte löschen")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("color: red;")
        action_layout.addWidget(self.delete_btn)
        
        results_layout.addLayout(action_layout)
        
        layout.addWidget(results_group, 1)
        
        # ===== Statistik =====
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel("Bereit zum Scan")
        stats_layout.addWidget(self.stats_label)
        
        stats_layout.addStretch()
        
        self.space_label = QLabel("")
        self.space_label.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.space_label)
        
        layout.addLayout(stats_layout)
        
        # ===== Dialog-Buttons =====
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        
        # Verbindungen
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_index(self, file_index):
        """Setzt den Datei-Index"""
        self.file_index = file_index
    
    def _on_source_changed(self, index: int):
        """Quelle geändert"""
        is_folder = index == 1
        self.folder_btn.setVisible(is_folder)
        self.folder_label.setVisible(is_folder)
    
    def _select_folder(self):
        """Ordner auswählen"""
        folder = QFileDialog.getExistingDirectory(self, "Ordner auswählen")
        if folder:
            self.folder_label.setText(folder)
            self.folder_label.setToolTip(folder)
    
    def _start_scan(self):
        """Startet den Duplikate-Scan"""
        # Validierung
        use_index = self.source_combo.currentIndex() == 0
        
        if use_index and not self.file_index:
            QMessageBox.warning(self, "Fehler", "Kein Index verfügbar!")
            return
        
        if not use_index and not self.folder_label.text():
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Ordner!")
            return
        
        # Alte Scan abbrechen
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait()
        
        # UI vorbereiten
        self.tree.clear()
        self.duplicate_groups = {}
        self.scan_btn.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.cancel_btn.show()
        self.stats_label.setText("Scan läuft...")
        self._update_buttons(False)
        
        # Worker starten
        min_size = self.min_size_spin.value() * 1024
        
        if use_index:
            self.scan_worker = DuplicateScanWorker(
                index=self.file_index,
                min_size=min_size
            )
        else:
            self.scan_worker = DuplicateScanWorker(
                scan_path=self.folder_label.text(),
                min_size=min_size
            )
        
        self.scan_worker.progress.connect(self._on_progress)
        self.scan_worker.duplicates_found.connect(self._on_duplicates_found)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.finished_scan.connect(self._on_scan_finished)
        self.scan_worker.start()
    
    def _cancel_scan(self):
        """Bricht den Scan ab"""
        if self.scan_worker:
            self.scan_worker.cancel()
            self.stats_label.setText("Scan abgebrochen")
        
        self._reset_ui()
    
    @pyqtSlot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        """Progress-Update"""
        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
        self.progress_label.setText(f"Prüfe: {filename[:50]}...")
    
    @pyqtSlot(dict)
    def _on_duplicates_found(self, duplicates: dict):
        """Duplikate gefunden"""
        self.duplicate_groups = duplicates
        self._populate_tree(duplicates)
    
    @pyqtSlot(int, int)
    def _on_scan_finished(self, total_files: int, groups: int):
        """Scan abgeschlossen"""
        self._reset_ui()
        
        if groups == 0:
            self.stats_label.setText(f"✅ Keine Duplikate gefunden ({total_files} Dateien geprüft)")
        else:
            total_duplicates = sum(len(p) - 1 for p in self.duplicate_groups.values())
            self.stats_label.setText(
                f"✅ {groups} Duplikat-Gruppen gefunden ({total_duplicates} doppelte Dateien)"
            )
            self._update_space_info()
            self._update_buttons(True)
    
    @pyqtSlot(str)
    def _on_scan_error(self, error: str):
        """Fehler beim Scan"""
        self._reset_ui()
        self.stats_label.setText(f"❌ Fehler: {error}")
    
    def _reset_ui(self):
        """Setzt UI zurück"""
        self.scan_btn.setEnabled(True)
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.progress_label.setText("")
    
    def _populate_tree(self, duplicates: dict):
        """Füllt den Baum mit Duplikaten"""
        self.tree.clear()
        
        for file_hash, paths in sorted(duplicates.items(), key=lambda x: -len(x[1])):
            if len(paths) < 2:
                continue
            
            # Gruppe
            size = self._get_file_size(paths[0])
            group_item = QTreeWidgetItem([
                f"📁 {len(paths)} Dateien",
                self._format_size(size),
                f"Hash: {file_hash[:16]}..."
            ])
            group_item.setData(0, Qt.ItemDataRole.UserRole, file_hash)
            group_item.setExpanded(True)
            
            # Dateien in der Gruppe
            for path in paths:
                name = Path(path).name
                folder = str(Path(path).parent)
                
                file_item = QTreeWidgetItem([
                    f"  📄 {name}",
                    self._format_size(self._get_file_size(path)),
                    folder
                ])
                file_item.setData(0, Qt.ItemDataRole.UserRole, path)
                file_item.setFlags(
                    file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                file_item.setCheckState(0, Qt.CheckState.Unchecked)
                
                group_item.addChild(file_item)
            
            self.tree.addTopLevelItem(group_item)
    
    def _get_file_size(self, path: str) -> int:
        """Gibt Dateigröße zurück"""
        try:
            return os.path.getsize(path)
        except:
            return 0
    
    def _format_size(self, size: int) -> str:
        """Formatiert Größe"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024*1024):.1f} MB"
        else:
            return f"{size / (1024*1024*1024):.2f} GB"
    
    def _update_space_info(self):
        """Aktualisiert Speicherplatz-Info"""
        total_waste = 0
        for paths in self.duplicate_groups.values():
            if len(paths) > 1:
                size = self._get_file_size(paths[0])
                total_waste += size * (len(paths) - 1)
        
        self.space_label.setText(
            f"💾 Verschwendeter Speicher: {self._format_size(total_waste)}"
        )
    
    def _update_buttons(self, enabled: bool):
        """Aktualisiert Button-Status"""
        self.select_all_btn.setEnabled(enabled)
        self.select_newest_btn.setEnabled(enabled)
        self.select_oldest_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled and self._has_checked_items())
    
    def _has_checked_items(self) -> bool:
        """Prüft ob Items ausgewählt sind"""
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                if group.child(j).checkState(0) == Qt.CheckState.Checked:
                    return True
        return False
    
    def _on_selection_changed(self):
        """Auswahl geändert"""
        self.delete_btn.setEnabled(self._has_checked_items())
    
    def _select_all_duplicates(self):
        """Wählt alle Duplikate (außer erste pro Gruppe)"""
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                child = group.child(j)
                # Erstes behalten
                state = Qt.CheckState.Unchecked if j == 0 else Qt.CheckState.Checked
                child.setCheckState(0, state)
        
        self.delete_btn.setEnabled(True)
    
    def _select_keep_newest(self):
        """Behält nur die neueste Datei pro Gruppe"""
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            
            # Dateien nach Änderungsdatum sortieren
            files_with_dates = []
            for j in range(group.childCount()):
                child = group.child(j)
                path = child.data(0, Qt.ItemDataRole.UserRole)
                try:
                    mtime = os.path.getmtime(path)
                except:
                    mtime = 0
                files_with_dates.append((j, mtime))
            
            # Neueste finden
            files_with_dates.sort(key=lambda x: -x[1])
            newest_idx = files_with_dates[0][0] if files_with_dates else 0
            
            # Checkboxen setzen
            for j in range(group.childCount()):
                state = Qt.CheckState.Unchecked if j == newest_idx else Qt.CheckState.Checked
                group.child(j).setCheckState(0, state)
        
        self.delete_btn.setEnabled(True)
    
    def _select_keep_oldest(self):
        """Behält nur die älteste Datei pro Gruppe"""
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            
            files_with_dates = []
            for j in range(group.childCount()):
                child = group.child(j)
                path = child.data(0, Qt.ItemDataRole.UserRole)
                try:
                    mtime = os.path.getmtime(path)
                except:
                    mtime = float('inf')
                files_with_dates.append((j, mtime))
            
            files_with_dates.sort(key=lambda x: x[1])
            oldest_idx = files_with_dates[0][0] if files_with_dates else 0
            
            for j in range(group.childCount()):
                state = Qt.CheckState.Unchecked if j == oldest_idx else Qt.CheckState.Checked
                group.child(j).setCheckState(0, state)
        
        self.delete_btn.setEnabled(True)
    
    def _delete_selected(self):
        """Löscht ausgewählte Dateien"""
        files_to_delete = []
        
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    files_to_delete.append(path)
        
        if not files_to_delete:
            return
        
        # Bestätigung
        total_size = sum(self._get_file_size(f) for f in files_to_delete)
        reply = QMessageBox.question(
            self,
            "Duplikate löschen",
            f"Möchten Sie {len(files_to_delete)} Dateien löschen?\n\n"
            f"Gesamtgröße: {self._format_size(total_size)}\n\n"
            f"Diese Aktion kann nicht rückgängig gemacht werden!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Löschen
        deleted = 0
        errors = []
        
        for path in files_to_delete:
            try:
                os.remove(path)
                deleted += 1
            except Exception as e:
                errors.append(f"{path}: {e}")
        
        # Ergebnis
        if errors:
            QMessageBox.warning(
                self, "Teilweise gelöscht",
                f"{deleted} von {len(files_to_delete)} Dateien gelöscht.\n\n"
                f"Fehler:\n" + "\n".join(errors[:5])
            )
        else:
            QMessageBox.information(
                self, "Erfolgreich",
                f"{deleted} Dateien wurden gelöscht.\n"
                f"Freigegeben: {self._format_size(total_size)}"
            )
        
        # Neu scannen
        self._start_scan()
    
    def _show_context_menu(self, pos):
        """Zeigt Kontextmenü"""
        item = self.tree.itemAt(pos)
        if not item or item.parent() is None:
            return
        
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        open_action = QAction("📂 Öffnen", self)
        open_action.triggered.connect(lambda: self._open_file(path))
        menu.addAction(open_action)
        
        folder_action = QAction("📁 Ordner öffnen", self)
        folder_action.triggered.connect(lambda: self._open_folder(path))
        menu.addAction(folder_action)
        
        menu.addSeparator()
        
        copy_action = QAction("📋 Pfad kopieren", self)
        copy_action.triggered.connect(lambda: self._copy_path(path))
        menu.addAction(copy_action)
        
        menu.exec(QCursor.pos())
    
    def _open_file(self, path: str):
        """Öffnet Datei"""
        import subprocess
        if os.name == 'nt':
            os.startfile(path)
        else:
            subprocess.run(['xdg-open', path])
    
    def _open_folder(self, path: str):
        """Öffnet Ordner"""
        folder = str(Path(path).parent)
        import subprocess
        if os.name == 'nt':
            os.startfile(folder)
        else:
            subprocess.run(['xdg-open', folder])
    
    def _copy_path(self, path: str):
        """Kopiert Pfad"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(path)
