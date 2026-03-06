#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileBrowser - Dateilisten-Ansicht mit QuickEditor-Integration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QHeaderView, 
    QMenu, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QDir, QModelIndex, QSortFilterProxyModel,
    QStandardPaths
)
from PyQt6.QtGui import (
    QFileSystemModel, QAction, QCursor
)
import os
from pathlib import Path

# Editor-Extensions
EDITOR_EXTENSIONS = {
    '.py', '.pyw', '.js', '.jsx', '.ts', '.tsx',
    '.html', '.htm', '.css', '.scss', '.less',
    '.json', '.xml', '.yaml', '.yml', '.toml',
    '.md', '.txt', '.rst', '.ini', '.cfg',
    '.sql', '.sh', '.bash', '.bat', '.ps1',
    '.c', '.cpp', '.h', '.hpp', '.java',
    '.rb', '.php', '.go', '.rs', '.swift'
}


class FileBrowser(QWidget):
    """
    Datei-Browser mit Tabellen-Ansicht
    Integriert QuickEditor für Code-Dateien
    """
    
    # Signale
    file_selected = pyqtSignal(str)
    folder_changed = pyqtSignal(str)
    path_changed = pyqtSignal(str)          # Für Toolbar & StatusBar
    selection_changed = pyqtSignal(int)     # Anzahl ausgewählter Dateien
    file_double_clicked = pyqtSignal(str)
    edit_requested = pyqtSignal(str)        # Datei im Editor öffnen
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = ""
        self._history = []
        self._history_index = -1
        self._file_count = 0
        self._setup_ui()
        
        # Startverzeichnis
        home = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.HomeLocation
        )
        self.navigate_to(home)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Datei-System-Model
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(
            QDir.Filter.AllEntries | 
            QDir.Filter.NoDotAndDotDot
        )
        self.model.directoryLoaded.connect(self._on_directory_loaded)
        
        # Sortier-Proxy
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Tabellen-View
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setRootIndex(self.proxy.mapFromSource(
            self.model.index(QDir.rootPath())
        ))
        
        # Spalten konfigurieren
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        
        # Header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Signale
        self.table.clicked.connect(self._on_item_clicked)
        self.table.doubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Selection-Signal
        self.table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        
        layout.addWidget(self.table)
    
    def _on_directory_loaded(self, path: str):
        """Handler wenn Verzeichnis geladen wurde"""
        if path == self._current_path:
            self._update_file_count()
    
    def _update_file_count(self):
        """Aktualisiert die Datei-Anzahl"""
        if self._current_path:
            try:
                entries = list(Path(self._current_path).iterdir())
                self._file_count = len(entries)
            except:
                self._file_count = 0
    
    def _on_selection_changed(self):
        """Handler für Auswahl-Änderungen"""
        selected = len(self.get_selected_files())
        self.selection_changed.emit(selected)
    
    def navigate_to(self, path: str):
        """Navigiert zu einem Pfad"""
        if not os.path.exists(path):
            return
        
        # History aktualisieren
        if self._current_path and self._current_path != path:
            # Vorwärts-History löschen
            self._history = self._history[:self._history_index + 1]
            self._history.append(path)
            self._history_index = len(self._history) - 1
        elif not self._history:
            self._history.append(path)
            self._history_index = 0
        
        self._current_path = path
        
        source_index = self.model.index(path)
        proxy_index = self.proxy.mapFromSource(source_index)
        self.table.setRootIndex(proxy_index)
        
        self._update_file_count()
        
        # Signale senden
        self.folder_changed.emit(path)
        self.path_changed.emit(path)
    
    def go_back(self):
        """Geht einen Schritt zurück"""
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._current_path = path
            source_index = self.model.index(path)
            proxy_index = self.proxy.mapFromSource(source_index)
            self.table.setRootIndex(proxy_index)
            self._update_file_count()
            self.folder_changed.emit(path)
            self.path_changed.emit(path)
    
    def go_forward(self):
        """Geht einen Schritt vorwärts"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            path = self._history[self._history_index]
            self._current_path = path
            source_index = self.model.index(path)
            proxy_index = self.proxy.mapFromSource(source_index)
            self.table.setRootIndex(proxy_index)
            self._update_file_count()
            self.folder_changed.emit(path)
            self.path_changed.emit(path)
    
    def go_up(self):
        """Geht zum übergeordneten Ordner"""
        if self._current_path:
            parent = os.path.dirname(self._current_path)
            if parent and parent != self._current_path:
                self.navigate_to(parent)
    
    def refresh(self):
        """Aktualisiert die Ansicht"""
        if self._current_path:
            self.model.setRootPath("")
            self.model.setRootPath(self._current_path)
            self._update_file_count()
    
    def _on_item_clicked(self, index: QModelIndex):
        source_index = self.proxy.mapToSource(index)
        file_path = self.model.filePath(source_index)
        
        if os.path.isfile(file_path):
            self.file_selected.emit(file_path)
    
    def _on_item_double_clicked(self, index: QModelIndex):
        source_index = self.proxy.mapToSource(index)
        file_path = self.model.filePath(source_index)
        
        if os.path.isdir(file_path):
            self.navigate_to(file_path)
        else:
            # Prüfe ob Editor-Datei
            ext = Path(file_path).suffix.lower()
            if ext in EDITOR_EXTENSIONS:
                self._edit_file(file_path)
            else:
                self._open_file(file_path)
    
    def _show_context_menu(self, pos):
        """Zeigt das Kontextmenü"""
        index = self.table.indexAt(pos)
        
        menu = QMenu(self)
        
        if index.isValid():
            source_index = self.proxy.mapToSource(index)
            file_path = self.model.filePath(source_index)
            is_file = os.path.isfile(file_path)
            ext = Path(file_path).suffix.lower() if is_file else ""
            
            # Öffnen
            open_action = QAction("📂 Öffnen", self)
            open_action.triggered.connect(lambda: self._open_file(file_path))
            menu.addAction(open_action)
            
            # In Editor öffnen (nur für Code-Dateien)
            if is_file and ext in EDITOR_EXTENSIONS:
                edit_action = QAction("✏️ In Editor öffnen", self)
                edit_action.setShortcut("F4")
                edit_action.triggered.connect(lambda: self._edit_file(file_path))
                menu.addAction(edit_action)
            
            menu.addSeparator()
            
            # Index-Aktionen
            index_action = QAction("🔍 In Index suchen", self)
            menu.addAction(index_action)
            
            meta_action = QAction("📊 Metadaten anzeigen", self)
            meta_action.triggered.connect(lambda: self.file_selected.emit(file_path))
            menu.addAction(meta_action)
            
            tags_action = QAction("🏷️ Tags bearbeiten", self)
            menu.addAction(tags_action)
            
            menu.addSeparator()
            
            # Sync
            sync_action = QAction("🔄 Synchronisieren", self)
            menu.addAction(sync_action)
            
            prompt_action = QAction("📋 Pfad als Prompt speichern", self)
            menu.addAction(prompt_action)
            
            menu.addSeparator()
            
            # Datenschutz
            privacy_action = QAction("🛡️ Datenschutz prüfen", self)
            privacy_action.triggered.connect(lambda: self._check_privacy(file_path))
            menu.addAction(privacy_action)
            
            blacklist_action = QAction("🔴 Zur Blacklist hinzufügen", self)
            menu.addAction(blacklist_action)
            
            menu.addSeparator()
            
            # Standard-Aktionen
            copy_action = QAction("Kopieren", self)
            copy_action.setShortcut("Ctrl+C")
            menu.addAction(copy_action)
            
            delete_action = QAction("Löschen", self)
            delete_action.setShortcut("Delete")
            menu.addAction(delete_action)
            
            rename_action = QAction("Umbenennen", self)
            rename_action.setShortcut("F2")
            menu.addAction(rename_action)
        
        else:
            # Leer-Bereich-Menü
            new_folder = QAction("📁 Neuer Ordner", self)
            menu.addAction(new_folder)
            
            paste_action = QAction("Einfügen", self)
            paste_action.setShortcut("Ctrl+V")
            menu.addAction(paste_action)
            
            menu.addSeparator()
            
            refresh_action = QAction("Aktualisieren", self)
            refresh_action.setShortcut("F5")
            refresh_action.triggered.connect(self.refresh)
            menu.addAction(refresh_action)
        
        menu.exec(QCursor.pos())
    
    def _open_file(self, path: str):
        """Öffnet eine Datei/Ordner mit System-Standard"""
        if os.path.isdir(path):
            self.navigate_to(path)
        else:
            import subprocess
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.run(['xdg-open', path])
    
    def _edit_file(self, path: str):
        """Öffnet Datei im QuickEditor"""
        from modules.editor.quick_editor import QuickEditorDialog
        
        editor = QuickEditorDialog(path, self.window())
        editor.exec()
    
    def _check_privacy(self, path: str):
        """Prüft Datei auf sensible Daten"""
        if not os.path.isfile(path):
            return
        
        try:
            # Nur Text-Dateien prüfen
            ext = Path(path).suffix.lower()
            if ext not in EDITOR_EXTENSIONS and ext not in {'.csv', '.log'}:
                QMessageBox.information(
                    self, "Datenschutz",
                    "Datenschutz-Prüfung nur für Text-Dateien verfügbar."
                )
                return
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # Max 50KB
            
            # PrivacyMonitor vom Hauptfenster holen
            main_window = self.window()
            if hasattr(main_window, 'privacy_monitor'):
                alert = main_window.privacy_monitor.check_text(content)
                
                if alert.detected_patterns:
                    QMessageBox.warning(
                        self, "Datenschutz-Prüfung",
                        f"Status: {alert.status.value.upper()}\n\n"
                        f"Erkannte Muster:\n• " + 
                        "\n• ".join(alert.detected_patterns)
                    )
                else:
                    QMessageBox.information(
                        self, "Datenschutz-Prüfung",
                        "✅ Keine sensiblen Daten erkannt."
                    )
        except Exception as e:
            QMessageBox.warning(
                self, "Fehler",
                f"Konnte Datei nicht prüfen: {e}"
            )
    
    @property
    def current_path(self) -> str:
        return self._current_path
    
    @property
    def file_count(self) -> int:
        return self._file_count
    
    def get_selected_files(self) -> list:
        """Gibt ausgewählte Dateien zurück"""
        selected = []
        for index in self.table.selectedIndexes():
            if index.column() == 0:
                source_index = self.proxy.mapToSource(index)
                path = self.model.filePath(source_index)
                selected.append(path)
        return selected
