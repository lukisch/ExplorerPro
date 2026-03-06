#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AdvancedSearchDialog - Erweiterte Suche mit Filtern
Phase 2: Index & Suche
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QDateEdit, QSpinBox, QCheckBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar, QDialogButtonBox, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QThread, pyqtSlot
from pathlib import Path


class AdvancedSearchWorker(QThread):
    """Background-Thread für erweiterte Suche"""
    
    results_ready = pyqtSignal(list)
    progress = pyqtSignal(int, int)  # current, total
    error = pyqtSignal(str)
    
    def __init__(self, index, criteria: dict):
        super().__init__()
        self.index = index
        self.criteria = criteria
        self._cancelled = False
    
    def run(self):
        try:
            results = self.index.advanced_search(**self.criteria)
            
            if not self._cancelled:
                self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self._cancelled = True


class AdvancedSearchDialog(QDialog):
    """
    Erweiterte Suche mit umfangreichen Filteroptionen:
    - Volltext-Suche
    - Dateityp-Filter
    - Datum-Bereich
    - Größen-Bereich
    - Tag-Filter
    - Regex-Unterstützung
    """
    
    result_selected = pyqtSignal(str)
    
    # Dateityp-Presets
    FILE_TYPES = [
        ("Alle Dateien", None),
        ("Dokumente", ['.txt', '.md', '.doc', '.docx', '.pdf', '.odt', '.rtf']),
        ("Bilder", ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg']),
        ("Code", ['.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.json', '.xml']),
        ("Tabellen", ['.xlsx', '.xls', '.csv', '.ods']),
        ("Audio", ['.mp3', '.wav', '.flac', '.ogg', '.m4a']),
        ("Video", ['.mp4', '.mkv', '.avi', '.mov', '.webm']),
        ("Archive", ['.zip', '.rar', '.7z', '.tar', '.gz']),
        ("PDFs", ['.pdf']),
        ("Python", ['.py', '.pyw', '.pyi']),
        ("JavaScript", ['.js', '.jsx', '.ts', '.tsx']),
        ("Benutzerdefiniert...", "custom"),
    ]
    
    # Datum-Presets
    DATE_PRESETS = [
        ("Beliebig", None, None),
        ("Heute", 0, 0),
        ("Letzte 7 Tage", 7, 0),
        ("Letzte 30 Tage", 30, 0),
        ("Letztes Jahr", 365, 0),
        ("Benutzerdefiniert...", "custom", "custom"),
    ]
    
    def __init__(self, file_index=None, parent=None):
        super().__init__(parent)
        self.file_index = file_index
        self.search_worker = None
        
        self.setWindowTitle("Erweiterte Suche")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # ===== Suchkriterien =====
        criteria_group = QGroupBox("Suchkriterien")
        criteria_layout = QFormLayout(criteria_group)
        
        # Suchbegriff
        search_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Suchbegriff eingeben...")
        self.query_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self.query_input)
        
        self.regex_cb = QCheckBox("Regex")
        self.regex_cb.setToolTip("Als regulären Ausdruck interpretieren")
        search_layout.addWidget(self.regex_cb)
        
        self.case_cb = QCheckBox("Groß/Klein")
        self.case_cb.setToolTip("Groß-/Kleinschreibung beachten")
        search_layout.addWidget(self.case_cb)
        
        criteria_layout.addRow("Suchbegriff:", search_layout)
        
        # Suchbereich
        scope_layout = QHBoxLayout()
        self.search_name_cb = QCheckBox("Dateiname")
        self.search_name_cb.setChecked(True)
        self.search_content_cb = QCheckBox("Inhalt")
        self.search_content_cb.setChecked(True)
        self.search_path_cb = QCheckBox("Pfad")
        scope_layout.addWidget(self.search_name_cb)
        scope_layout.addWidget(self.search_content_cb)
        scope_layout.addWidget(self.search_path_cb)
        scope_layout.addStretch()
        criteria_layout.addRow("Suche in:", scope_layout)
        
        # Dateityp
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        for name, _ in self.FILE_TYPES:
            self.type_combo.addItem(name)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)
        
        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText(".py, .txt, ...")
        self.custom_ext_input.hide()
        type_layout.addWidget(self.custom_ext_input)
        
        criteria_layout.addRow("Dateityp:", type_layout)
        
        # Datum
        date_layout = QHBoxLayout()
        self.date_preset_combo = QComboBox()
        for name, _, _ in self.DATE_PRESETS:
            self.date_preset_combo.addItem(name)
        self.date_preset_combo.currentIndexChanged.connect(self._on_date_preset_changed)
        date_layout.addWidget(self.date_preset_combo)
        
        date_layout.addWidget(QLabel("Von:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_from.setEnabled(False)
        date_layout.addWidget(self.date_from)
        
        date_layout.addWidget(QLabel("Bis:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)
        date_layout.addWidget(self.date_to)
        
        criteria_layout.addRow("Geändert:", date_layout)
        
        # Größe
        size_layout = QHBoxLayout()
        self.size_min = QSpinBox()
        self.size_min.setRange(0, 100000)
        self.size_min.setSuffix(" KB")
        self.size_min.setSpecialValueText("Keine Grenze")
        size_layout.addWidget(QLabel("Min:"))
        size_layout.addWidget(self.size_min)
        
        self.size_max = QSpinBox()
        self.size_max.setRange(0, 100000)
        self.size_max.setSuffix(" KB")
        self.size_max.setSpecialValueText("Keine Grenze")
        size_layout.addWidget(QLabel("Max:"))
        size_layout.addWidget(self.size_max)
        size_layout.addStretch()
        
        criteria_layout.addRow("Größe:", size_layout)
        
        # Tags
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("tag1, tag2, ... (mit Komma trennen)")
        criteria_layout.addRow("Tags:", self.tags_input)
        
        layout.addWidget(criteria_group)
        
        # ===== Buttons =====
        button_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("🔍 Suchen")
        self.search_btn.setDefault(True)
        self.search_btn.clicked.connect(self._do_search)
        button_layout.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("Zurücksetzen")
        self.clear_btn.clicked.connect(self._reset_form)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        button_layout.addWidget(self.progress_bar)
        
        layout.addLayout(button_layout)
        
        # ===== Ergebnisse =====
        results_group = QGroupBox("Ergebnisse")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Name", "Pfad", "Typ", "Größe", "Geändert"
        ])
        self.results_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        self.results_table.doubleClicked.connect(self._on_result_double_clicked)
        
        # Spaltenbreiten
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setColumnWidth(0, 200)
        
        results_layout.addWidget(self.results_table)
        
        # Status
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Bereit")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.open_btn = QPushButton("Öffnen")
        self.open_btn.clicked.connect(self._open_selected)
        self.open_btn.setEnabled(False)
        status_layout.addWidget(self.open_btn)
        
        self.open_folder_btn = QPushButton("Ordner öffnen")
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.setEnabled(False)
        status_layout.addWidget(self.open_folder_btn)
        
        results_layout.addLayout(status_layout)
        
        layout.addWidget(results_group, 1)
        
        # ===== Dialog-Buttons =====
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        
        # Verbindungen
        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_index(self, file_index):
        """Setzt den Datei-Index"""
        self.file_index = file_index
    
    def _on_type_changed(self, index: int):
        """Dateityp geändert"""
        _, extensions = self.FILE_TYPES[index]
        self.custom_ext_input.setVisible(extensions == "custom")
    
    def _on_date_preset_changed(self, index: int):
        """Datum-Preset geändert"""
        _, days_from, days_to = self.DATE_PRESETS[index]
        
        if days_from == "custom":
            self.date_from.setEnabled(True)
            self.date_to.setEnabled(True)
        elif days_from is None:
            self.date_from.setEnabled(False)
            self.date_to.setEnabled(False)
        else:
            self.date_from.setEnabled(False)
            self.date_to.setEnabled(False)
            self.date_from.setDate(QDate.currentDate().addDays(-days_from))
            self.date_to.setDate(QDate.currentDate())
    
    def _get_criteria(self) -> dict:
        """Sammelt Suchkriterien"""
        criteria = {}
        
        # Query
        query = self.query_input.text().strip()
        if query:
            criteria['query'] = query
            criteria['use_regex'] = self.regex_cb.isChecked()
            criteria['case_sensitive'] = self.case_cb.isChecked()
        
        # Suchbereich
        criteria['search_name'] = self.search_name_cb.isChecked()
        criteria['search_content'] = self.search_content_cb.isChecked()
        criteria['search_path'] = self.search_path_cb.isChecked()
        
        # Dateityp
        type_idx = self.type_combo.currentIndex()
        _, extensions = self.FILE_TYPES[type_idx]
        if extensions == "custom":
            custom = self.custom_ext_input.text()
            extensions = [e.strip() for e in custom.split(',') if e.strip()]
        if extensions:
            criteria['extensions'] = extensions
        
        # Datum
        date_idx = self.date_preset_combo.currentIndex()
        _, days_from, days_to = self.DATE_PRESETS[date_idx]
        if days_from is not None or self.date_from.isEnabled():
            criteria['date_from'] = self.date_from.date().toPyDate()
            criteria['date_to'] = self.date_to.date().toPyDate()
        
        # Größe
        if self.size_min.value() > 0:
            criteria['min_size'] = self.size_min.value() * 1024
        if self.size_max.value() > 0:
            criteria['max_size'] = self.size_max.value() * 1024
        
        # Tags
        tags = self.tags_input.text().strip()
        if tags:
            criteria['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
        
        criteria['limit'] = 500
        
        return criteria
    
    def _do_search(self):
        """Führt die Suche aus"""
        if not self.file_index:
            QMessageBox.warning(self, "Fehler", "Kein Index verfügbar!")
            return
        
        criteria = self._get_criteria()
        
        if not criteria.get('query') and not criteria.get('extensions') and not criteria.get('tags'):
            QMessageBox.information(
                self, "Hinweis",
                "Bitte geben Sie mindestens einen Suchbegriff, Dateityp oder Tag an."
            )
            return
        
        # Alte Suche abbrechen
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.search_worker.wait()
        
        # UI aktualisieren
        self.search_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.status_label.setText("Suche läuft...")
        self.results_table.setRowCount(0)
        
        # Suche starten
        self.search_worker = AdvancedSearchWorker(self.file_index, criteria)
        self.search_worker.results_ready.connect(self._on_results_ready)
        self.search_worker.error.connect(self._on_search_error)
        self.search_worker.start()
    
    @pyqtSlot(list)
    def _on_results_ready(self, results: list):
        """Verarbeitet Suchergebnisse"""
        self.search_btn.setEnabled(True)
        self.progress_bar.hide()
        
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # Name
            name_item = QTableWidgetItem(result.get('name', ''))
            name_item.setData(Qt.ItemDataRole.UserRole, result.get('path', ''))
            self.results_table.setItem(row, 0, name_item)
            
            # Pfad
            path = result.get('path', '')
            folder = str(Path(path).parent) if path else ''
            self.results_table.setItem(row, 1, QTableWidgetItem(folder))
            
            # Typ
            ext = result.get('extension', '')
            self.results_table.setItem(row, 2, QTableWidgetItem(ext))
            
            # Größe
            size = result.get('size', 0)
            size_str = self._format_size(size)
            size_item = QTableWidgetItem(size_str)
            size_item.setData(Qt.ItemDataRole.UserRole, size)  # Für Sortierung
            self.results_table.setItem(row, 3, size_item)
            
            # Datum
            modified = result.get('modified')
            if modified:
                if isinstance(modified, str):
                    date_str = modified[:10]
                else:
                    date_str = modified.strftime('%d.%m.%Y')
            else:
                date_str = ''
            self.results_table.setItem(row, 4, QTableWidgetItem(date_str))
        
        count = len(results)
        self.status_label.setText(f"✅ {count} Ergebnis{'se' if count != 1 else ''} gefunden")
    
    @pyqtSlot(str)
    def _on_search_error(self, error: str):
        """Fehler bei Suche"""
        self.search_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"❌ Fehler: {error}")
    
    def _format_size(self, size: int) -> str:
        """Formatiert Dateigröße"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024*1024):.1f} MB"
        else:
            return f"{size / (1024*1024*1024):.2f} GB"
    
    def _on_selection_changed(self):
        """Auswahl geändert"""
        has_selection = len(self.results_table.selectedItems()) > 0
        self.open_btn.setEnabled(has_selection)
        self.open_folder_btn.setEnabled(has_selection)
    
    def _on_result_double_clicked(self, index):
        """Ergebnis doppelt angeklickt"""
        self._open_selected()
    
    def _open_selected(self):
        """Öffnet ausgewählte Datei"""
        row = self.results_table.currentRow()
        if row >= 0:
            item = self.results_table.item(row, 0)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                self.result_selected.emit(path)
                self.accept()
    
    def _open_folder(self):
        """Öffnet Ordner der ausgewählten Datei"""
        row = self.results_table.currentRow()
        if row >= 0:
            item = self.results_table.item(row, 0)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                folder = str(Path(path).parent)
                self.result_selected.emit(folder)
    
    def _reset_form(self):
        """Setzt Formular zurück"""
        self.query_input.clear()
        self.regex_cb.setChecked(False)
        self.case_cb.setChecked(False)
        self.search_name_cb.setChecked(True)
        self.search_content_cb.setChecked(True)
        self.search_path_cb.setChecked(False)
        self.type_combo.setCurrentIndex(0)
        self.custom_ext_input.clear()
        self.date_preset_combo.setCurrentIndex(0)
        self.size_min.setValue(0)
        self.size_max.setValue(0)
        self.tags_input.clear()
        self.results_table.setRowCount(0)
        self.status_label.setText("Bereit")
