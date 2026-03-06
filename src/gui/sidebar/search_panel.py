#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearchPanel - Erweiterte Suche im Sidebar
Phase 2: Index & Suche
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QComboBox, QMenu,
    QToolButton, QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QCursor
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """Suchergebnis"""
    path: str
    name: str
    extension: str
    size: int
    modified: datetime
    snippet: str = ""
    score: float = 0.0
    category: str = ""


class SearchResultItem(QListWidgetItem):
    """Ergebnis-Item mit erweiterten Infos"""
    
    CATEGORY_ICONS = {
        'Dokumente': '📄',
        'Bilder': '🖼️',
        'Code': '💻',
        'Audio': '🎵',
        'Video': '🎬',
        'Archive': '📦',
        'Tabellen': '📊',
        'Sonstige': '📁'
    }
    
    def __init__(self, result: SearchResult):
        super().__init__()
        self.result = result
        
        # Icon + Name
        icon = self.CATEGORY_ICONS.get(result.category, '📄')
        self.setText(f"{icon} {result.name}")
        
        # Tooltip mit Details
        tooltip = f"""<b>{result.name}</b><br>
        📁 {result.path}<br>
        📏 {self._format_size(result.size)}<br>
        📅 {result.modified.strftime('%d.%m.%Y %H:%M') if result.modified else 'Unbekannt'}"""
        
        if result.snippet:
            tooltip += f"<br><br><i>...{result.snippet[:200]}...</i>"
        
        self.setToolTip(tooltip)
        
        # Pfad für Doppelklick
        self.setData(Qt.ItemDataRole.UserRole, result.path)
    
    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024*1024):.1f} MB"
        else:
            return f"{size / (1024*1024*1024):.2f} GB"


class SearchWorker(QThread):
    """Background-Thread für Suche"""
    
    results_ready = pyqtSignal(list)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, index, query: str, filters: dict):
        super().__init__()
        self.index = index
        self.query = query
        self.filters = filters
        self._cancelled = False
    
    def run(self):
        try:
            results = self.index.search(
                query=self.query,
                extension=self.filters.get('extension'),
                category=self.filters.get('category'),
                min_size=self.filters.get('min_size'),
                max_size=self.filters.get('max_size'),
                limit=self.filters.get('limit', 100)
            )
            
            if not self._cancelled:
                self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self._cancelled = True


class SearchPanel(QWidget):
    """
    Erweiterte Suche im Sidebar
    Features:
    - Volltext-Suche mit FTS5
    - Typ-Filter
    - Echtzeit-Ergebnisse (Debounce)
    - Snippet-Vorschau
    """
    
    # Signale
    result_selected = pyqtSignal(str)       # Pfad der ausgewählten Datei
    result_activated = pyqtSignal(str)      # Doppelklick auf Ergebnis
    search_started = pyqtSignal()
    search_finished = pyqtSignal(int)       # Anzahl Ergebnisse
    
    # Kategorien
    CATEGORIES = [
        ("Alle", None),
        ("Dokumente", "Dokumente"),
        ("Bilder", "Bilder"),
        ("Code", "Code"),
        ("PDFs", ".pdf"),
        ("Audio", "Audio"),
        ("Video", "Video"),
        ("Archive", "Archive"),
    ]
    
    def __init__(self, file_index=None, parent=None):
        super().__init__(parent)
        self.file_index = file_index
        self.search_worker = None
        
        # Debounce Timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)  # 300ms Verzögerung
        self.search_timer.timeout.connect(self._execute_search)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # ===== Suchfeld =====
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Volltextsuche...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._execute_search)
        search_layout.addWidget(self.search_input)
        
        # Erweiterte Suche Button
        self.advanced_btn = QToolButton()
        self.advanced_btn.setText("⚙️")
        self.advanced_btn.setToolTip("Erweiterte Suche")
        self.advanced_btn.clicked.connect(self._show_advanced_search)
        search_layout.addWidget(self.advanced_btn)
        
        layout.addLayout(search_layout)
        
        # ===== Filter-Leiste =====
        filter_layout = QHBoxLayout()
        
        self.type_combo = QComboBox()
        for name, _ in self.CATEGORIES:
            self.type_combo.addItem(name)
        self.type_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(QLabel("Typ:"))
        filter_layout.addWidget(self.type_combo, 1)
        
        # Content-Only Checkbox
        self.content_only_cb = QCheckBox("Im Inhalt")
        self.content_only_cb.setToolTip("Nur im Dateiinhalt suchen (nicht im Namen)")
        self.content_only_cb.stateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.content_only_cb)
        
        layout.addLayout(filter_layout)
        
        # ===== Progress =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # ===== Ergebnis-Liste =====
        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.results_list, 1)
        
        # ===== Status =====
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Bereit")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        status_layout.addWidget(self.status_label)
        
        self.clear_btn = QPushButton("Löschen")
        self.clear_btn.setMaximumWidth(60)
        self.clear_btn.clicked.connect(self._clear_results)
        self.clear_btn.hide()
        status_layout.addWidget(self.clear_btn)
        
        layout.addLayout(status_layout)
    
    def set_index(self, file_index):
        """Setzt den Datei-Index"""
        self.file_index = file_index
    
    def _on_text_changed(self, text: str):
        """Startet Debounce-Timer bei Texteingabe"""
        if len(text) >= 2:
            self.search_timer.start()
        elif len(text) == 0:
            self._clear_results()
    
    def _on_filter_changed(self):
        """Filter geändert - neu suchen"""
        if self.search_input.text():
            self._execute_search()
    
    def _execute_search(self):
        """Führt die Suche aus"""
        query = self.search_input.text().strip()
        if not query or len(query) < 2:
            return
        
        if not self.file_index:
            self.status_label.setText("⚠️ Kein Index verfügbar")
            return
        
        # Alte Suche abbrechen
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.search_worker.wait()
        
        # Filter zusammenstellen
        category_idx = self.type_combo.currentIndex()
        _, category = self.CATEGORIES[category_idx]
        
        filters = {
            'category': category,
            'content_only': self.content_only_cb.isChecked(),
            'limit': 100
        }
        
        # UI aktualisieren
        self.search_started.emit()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.show()
        self.status_label.setText(f"Suche nach '{query}'...")
        self.results_list.clear()
        
        # Suche starten
        self.search_worker = SearchWorker(self.file_index, query, filters)
        self.search_worker.results_ready.connect(self._on_results_ready)
        self.search_worker.error.connect(self._on_search_error)
        self.search_worker.start()
    
    @pyqtSlot(list)
    def _on_results_ready(self, results: list):
        """Verarbeitet Suchergebnisse"""
        self.progress_bar.hide()
        self.results_list.clear()
        
        for result_dict in results:
            # Dict zu SearchResult konvertieren
            result = SearchResult(
                path=result_dict.get('path', ''),
                name=result_dict.get('name', ''),
                extension=result_dict.get('extension', ''),
                size=result_dict.get('size', 0),
                modified=result_dict.get('modified'),
                snippet=result_dict.get('snippet', ''),
                score=result_dict.get('score', 0),
                category=result_dict.get('category', 'Sonstige')
            )
            
            item = SearchResultItem(result)
            self.results_list.addItem(item)
        
        count = len(results)
        self.status_label.setText(f"✅ {count} Ergebnis{'se' if count != 1 else ''}")
        self.clear_btn.setVisible(count > 0)
        self.search_finished.emit(count)
    
    @pyqtSlot(str)
    def _on_search_error(self, error: str):
        """Fehler bei Suche"""
        self.progress_bar.hide()
        self.status_label.setText(f"❌ Fehler: {error}")
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Item angeklickt"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.result_selected.emit(path)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Item doppelt angeklickt"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.result_activated.emit(path)
    
    def _show_context_menu(self, pos):
        """Kontextmenü für Ergebnisse"""
        item = self.results_list.itemAt(pos)
        if not item:
            return
        
        path = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        open_action = QAction("📂 Öffnen", self)
        open_action.triggered.connect(lambda: self.result_activated.emit(path))
        menu.addAction(open_action)
        
        folder_action = QAction("📁 Ordner öffnen", self)
        folder_action.triggered.connect(lambda: self._open_folder(path))
        menu.addAction(folder_action)
        
        menu.addSeparator()
        
        copy_path_action = QAction("📋 Pfad kopieren", self)
        copy_path_action.triggered.connect(lambda: self._copy_path(path))
        menu.addAction(copy_path_action)
        
        menu.exec(QCursor.pos())
    
    def _open_folder(self, path: str):
        """Öffnet den Ordner der Datei"""
        folder = str(Path(path).parent)
        self.result_selected.emit(folder)
    
    def _copy_path(self, path: str):
        """Kopiert Pfad in Zwischenablage"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
    
    def _clear_results(self):
        """Löscht Suchergebnisse"""
        self.search_input.clear()
        self.results_list.clear()
        self.status_label.setText("Bereit")
        self.clear_btn.hide()
    
    def _show_advanced_search(self):
        """Öffnet erweiterte Suche"""
        from .advanced_search_dialog import AdvancedSearchDialog
        
        dialog = AdvancedSearchDialog(self.file_index, self.window())
        dialog.result_selected.connect(self.result_selected.emit)
        dialog.exec()
    
    def show_results(self, results: list):
        """Zeigt Suchergebnisse an (Kompatibilität mit altem Interface)"""
        self._on_results_ready(results)
