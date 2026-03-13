#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MainWindow - Hauptfenster für ExplorerPro
Mit vollständiger Menü-Integration
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QLabel, QToolBar, QLineEdit, QPushButton, QMessageBox,
    QToolButton, QDialog, QFormLayout, QCheckBox, QGroupBox,
    QVBoxLayout as QVBox, QDialogButtonBox, QFileDialog,
    QInputDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QAction, QKeySequence
import os

from .sidebar import Sidebar
from .browser.file_browser import FileBrowser
from .preview.preview_panel import PreviewPanel
from .status_bar import StatusBarWidget


class SearchToolBar(QToolBar):
    """Toolbar mit Such-Funktionalität"""
    
    search_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__("Toolbar", parent)
        self.setMovable(False)
        self.setIconSize(QSize(24, 24))
        self._setup_ui()
    
    def _setup_ui(self):
        # Navigation
        self.back_action = QAction("←", self)
        self.back_action.setToolTip("Zurück (Alt+Left)")
        self.back_action.setShortcut(QKeySequence("Alt+Left"))
        self.addAction(self.back_action)
        
        self.forward_action = QAction("→", self)
        self.forward_action.setToolTip("Vorwärts (Alt+Right)")
        self.forward_action.setShortcut(QKeySequence("Alt+Right"))
        self.addAction(self.forward_action)
        
        self.up_action = QAction("↑", self)
        self.up_action.setToolTip("Übergeordneter Ordner (Alt+Up)")
        self.up_action.setShortcut(QKeySequence("Alt+Up"))
        self.addAction(self.up_action)
        
        self.addSeparator()
        
        # Pfad-Anzeige
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Pfad eingeben...")
        self.path_edit.setMinimumWidth(300)
        self.addWidget(self.path_edit)
        
        self.addSeparator()
        
        # Suche
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Suchen...")
        self.search_edit.setMinimumWidth(200)
        self.search_edit.setMaximumWidth(300)
        self.search_edit.returnPressed.connect(self._on_search)
        self.addWidget(self.search_edit)
        
        # Suche-Button
        search_btn = QPushButton("Suchen")
        search_btn.clicked.connect(self._on_search)
        self.addWidget(search_btn)
        
        self.addSeparator()
        
        # Ansicht-Umschalter
        self.view_btn = QToolButton()
        self.view_btn.setText("Ansicht")
        self.view_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.addWidget(self.view_btn)
    
    def _on_search(self):
        query = self.search_edit.text()
        if query:
            self.search_requested.emit(query)
    
    def set_path(self, path: str):
        """Aktualisiert die Pfad-Anzeige"""
        self.path_edit.setText(path)


class PrivacySettingsDialog(QDialog):
    """Dialog für Datenschutz-Einstellungen"""
    
    def __init__(self, privacy_monitor, parent=None):
        super().__init__(parent)
        self.privacy_monitor = privacy_monitor
        self.setWindowTitle("Datenschutz-Einstellungen")
        self.setMinimumWidth(450)
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBox(self)
        
        # Pattern-Gruppe
        pattern_group = QGroupBox("Erkennungsmuster")
        pattern_layout = QVBox(pattern_group)
        
        self.pattern_checks = {}
        from modules.privacy.privacy_monitor import BUILTIN_PATTERNS
        
        for key, info in BUILTIN_PATTERNS.items():
            cb = QCheckBox(f"{info['name']} - {info['description']}")
            cb.setToolTip(f"Severity: {info['severity']}")
            self.pattern_checks[key] = cb
            pattern_layout.addWidget(cb)
        
        layout.addWidget(pattern_group)
        
        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QVBox(options_group)
        
        self.case_sensitive_cb = QCheckBox("Groß-/Kleinschreibung beachten")
        options_layout.addWidget(self.case_sensitive_cb)
        
        self.whole_words_cb = QCheckBox("Nur ganze Wörter")
        options_layout.addWidget(self.whole_words_cb)
        
        self.auto_clear_cb = QCheckBox("Clipboard bei ROT automatisch leeren")
        options_layout.addWidget(self.auto_clear_cb)
        
        layout.addWidget(options_group)
        
        # Statistik
        stats_group = QGroupBox("Statistik")
        stats_layout = QFormLayout(stats_group)
        
        stats = self.privacy_monitor.get_stats()
        stats_layout.addRow("Blacklist-Einträge:", QLabel(str(stats['blacklist_count'])))
        stats_layout.addRow("Whitelist-Einträge:", QLabel(str(stats['whitelist_count'])))
        stats_layout.addRow("Aktive Patterns:", QLabel(str(stats['active_patterns'])))
        
        layout.addWidget(stats_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_settings(self):
        """Lädt aktuelle Einstellungen"""
        for key, cb in self.pattern_checks.items():
            cb.setChecked(self.privacy_monitor.pattern_enabled.get(key, False))
        
        self.case_sensitive_cb.setChecked(self.privacy_monitor.case_sensitive)
        self.whole_words_cb.setChecked(self.privacy_monitor.whole_words)
        self.auto_clear_cb.setChecked(self.privacy_monitor._auto_clear)
    
    def _save_and_close(self):
        """Speichert und schließt"""
        for key, cb in self.pattern_checks.items():
            self.privacy_monitor.pattern_enabled[key] = cb.isChecked()
        
        self.privacy_monitor.case_sensitive = self.case_sensitive_cb.isChecked()
        self.privacy_monitor.whole_words = self.whole_words_cb.isChecked()
        self.privacy_monitor._auto_clear = self.auto_clear_cb.isChecked()
        
        self.privacy_monitor._compile_patterns()
        self.privacy_monitor.save_config()
        
        self.accept()


class MainWindow(QMainWindow):
    """
    Hauptfenster mit 3-Panel Layout:
    - Sidebar (links): Ordnerbaum, Favoriten, Suche, Apps, Prompts
    - FileBrowser (mitte): Dateiliste
    - PreviewPanel (rechts): Vorschau, Metadaten
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExplorerPro")
        self.setMinimumSize(1200, 800)
        
        self._setup_menu()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_statusbar()
    
    def _setup_menu(self):
        """Erstellt die Menüleiste"""
        menubar = self.menuBar()
        
        # ===== Datei-Menü =====
        file_menu = menubar.addMenu("&Datei")
        
        new_window_action = QAction("Neues Fenster", self)
        new_window_action.setShortcut(QKeySequence("Ctrl+N"))
        file_menu.addAction(new_window_action)
        
        file_menu.addSeparator()
        
        open_folder_action = QAction("Ordner öffnen...", self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+O"))
        open_folder_action.triggered.connect(self._open_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Beenden", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ===== Bearbeiten-Menü =====
        edit_menu = menubar.addMenu("&Bearbeiten")
        
        copy_action = QAction("Kopieren", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Einfügen", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        new_folder_action = QAction("Neuer Ordner", self)
        new_folder_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_folder_action.triggered.connect(self._create_new_folder)
        edit_menu.addAction(new_folder_action)
        
        # ===== Ansicht-Menü =====
        view_menu = menubar.addMenu("&Ansicht")
        
        self.toggle_sidebar = QAction("Sidebar anzeigen", self)
        self.toggle_sidebar.setCheckable(True)
        self.toggle_sidebar.setChecked(True)
        self.toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        self.toggle_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(self.toggle_sidebar)
        
        self.toggle_preview = QAction("Vorschau anzeigen", self)
        self.toggle_preview.setCheckable(True)
        self.toggle_preview.setChecked(True)
        self.toggle_preview.setShortcut(QKeySequence("Ctrl+P"))
        self.toggle_preview.triggered.connect(self._toggle_preview)
        view_menu.addAction(self.toggle_preview)
        
        view_menu.addSeparator()
        
        refresh_action = QAction("Aktualisieren", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(lambda: self.file_browser.refresh())
        view_menu.addAction(refresh_action)
        
        # ===== Gehe zu-Menü =====
        go_menu = menubar.addMenu("&Gehe zu")
        
        home_action = QAction("Home", self)
        home_action.setShortcut(QKeySequence("Alt+Home"))
        home_action.triggered.connect(self._go_home)
        go_menu.addAction(home_action)
        
        documents_action = QAction("Dokumente", self)
        documents_action.triggered.connect(self._go_documents)
        go_menu.addAction(documents_action)
        
        downloads_action = QAction("Downloads", self)
        downloads_action.triggered.connect(self._go_downloads)
        go_menu.addAction(downloads_action)
        
        desktop_action = QAction("Desktop", self)
        desktop_action.triggered.connect(self._go_desktop)
        go_menu.addAction(desktop_action)
        
        # ===== Tools-Menü =====
        tools_menu = menubar.addMenu("&Tools")
        
        index_action = QAction("🔍 Ordner indizieren...", self)
        index_action.triggered.connect(self._index_folder)
        tools_menu.addAction(index_action)
        
        duplicates_action = QAction("🔄 Duplikate finden...", self)
        duplicates_action.triggered.connect(self._find_duplicates)
        tools_menu.addAction(duplicates_action)
        
        tools_menu.addSeparator()
        
        editor_action = QAction("✏️ Editor öffnen", self)
        editor_action.setShortcut(QKeySequence("F4"))
        editor_action.triggered.connect(self._open_editor)
        tools_menu.addAction(editor_action)
        
        tools_menu.addSeparator()
        
        # Sidebar-Panels
        apps_action = QAction("🚀 Apps öffnen", self)
        apps_action.setShortcut(QKeySequence("Ctrl+1"))
        apps_action.triggered.connect(self.show_apps_panel)
        tools_menu.addAction(apps_action)
        
        prompts_action = QAction("📋 Prompts öffnen", self)
        prompts_action.setShortcut(QKeySequence("Ctrl+2"))
        prompts_action.triggered.connect(self.show_prompts_panel)
        tools_menu.addAction(prompts_action)
        
        sync_action = QAction("🔄 Sync öffnen", self)
        sync_action.setShortcut(QKeySequence("Ctrl+3"))
        sync_action.triggered.connect(self.show_sync_panel)
        tools_menu.addAction(sync_action)
        
        tools_menu.addSeparator()
        
        privacy_action = QAction("🛡️ Datenschutz-Einstellungen...", self)
        privacy_action.triggered.connect(self._show_privacy_settings)
        tools_menu.addAction(privacy_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction("Einstellungen...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        tools_menu.addAction(settings_action)
        
        # ===== Hilfe-Menü =====
        help_menu = menubar.addMenu("&Hilfe")
        
        about_action = QAction("Über ExplorerPro...", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Erstellt die Toolbar"""
        self.toolbar = SearchToolBar(self)
        self.addToolBar(self.toolbar)
    
    def _setup_ui(self):
        """Erstellt das 3-Panel Layout"""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Haupt-Splitter (horizontal)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar (links)
        self.sidebar = Sidebar()
        self.main_splitter.addWidget(self.sidebar)
        
        # Rechter Bereich mit Browser und Preview
        self.right_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File Browser (mitte)
        self.file_browser = FileBrowser()
        self.right_splitter.addWidget(self.file_browser)
        
        # Preview Panel (rechts)
        self.preview_panel = PreviewPanel()
        self.right_splitter.addWidget(self.preview_panel)
        
        self.right_splitter.setSizes([600, 400])
        self.main_splitter.addWidget(self.right_splitter)
        
        self.main_splitter.setSizes([250, 1000])
        
        layout.addWidget(self.main_splitter)
    
    def _setup_statusbar(self):
        """Erstellt die Statusleiste mit Ampel"""
        self.status_widget = StatusBarWidget()
        self.setStatusBar(self.status_widget)
    
    # ===== Menü-Aktionen =====
    
    def _open_folder(self):
        """Öffnet einen Ordner-Dialog"""
        folder = QFileDialog.getExistingDirectory(
            self, "Ordner öffnen",
            self.file_browser.current_path
        )
        if folder:
            self.file_browser.navigate_to(folder)
    
    def _create_new_folder(self):
        """Erstellt einen neuen Ordner"""
        name, ok = QInputDialog.getText(
            self, "Neuer Ordner", "Ordnername:"
        )
        if ok and name:
            path = os.path.join(self.file_browser.current_path, name)
            try:
                os.makedirs(path, exist_ok=True)
                self.file_browser.refresh()
                self.statusBar().showMessage(f"Ordner erstellt: {name}", 3000)
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Konnte Ordner nicht erstellen: {e}")
    
    def _toggle_sidebar(self):
        """Sidebar ein-/ausblenden"""
        self.sidebar.setVisible(self.toggle_sidebar.isChecked())
    
    def _toggle_preview(self):
        """Preview ein-/ausblenden"""
        self.preview_panel.setVisible(self.toggle_preview.isChecked())
    
    def _go_home(self):
        """Zum Home-Verzeichnis"""
        home = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.HomeLocation
        )
        self.file_browser.navigate_to(home)
    
    def _go_documents(self):
        """Zum Dokumente-Verzeichnis"""
        docs = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        self.file_browser.navigate_to(docs)
    
    def _go_downloads(self):
        """Zum Downloads-Verzeichnis"""
        dl = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        self.file_browser.navigate_to(dl)
    
    def _go_desktop(self):
        """Zum Desktop-Verzeichnis"""
        desk = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )
        self.file_browser.navigate_to(desk)
    
    def _index_folder(self):
        """Aktuellen Ordner indizieren"""
        if hasattr(self, 'index_current_folder'):
            self.index_current_folder()
        elif hasattr(self, 'file_index'):
            from core.file_index import IndexWorker
            current_path = self.file_browser.current_path
            if current_path:
                self.index_worker = IndexWorker(self.file_index, current_path)
                self.index_worker.progress.connect(
                    lambda c, t: self.statusBar().showMessage(f"Indiziere: {c}/{t}")
                )
                self.index_worker.finished_indexing.connect(
                    lambda n: self.statusBar().showMessage(f"✅ {n} Dateien indiziert", 5000)
                )
                self.index_worker.start()
        else:
            self.statusBar().showMessage("Indizierung: Funktion in app.py", 3000)
    
    def _find_duplicates(self):
        """Duplikate finden - öffnet DuplicateFinderDialog"""
        if hasattr(self, 'file_index'):
            from modules.indexer.duplicate_finder import DuplicateFinderDialog
            dialog = DuplicateFinderDialog(self.file_index, self)
            dialog.exec()
        elif hasattr(self, 'show_duplicate_finder'):
            self.show_duplicate_finder()
        else:
            self.statusBar().showMessage("Duplikate-Finder: In app.py verfügbar", 3000)
    
    def _open_editor(self):
        """Öffnet Editor für ausgewählte Datei"""
        selected = self.file_browser.get_selected_files()
        if selected:
            for path in selected:
                if os.path.isfile(path):
                    self.file_browser._edit_file(path)
                    break
        else:
            self.statusBar().showMessage("Keine Datei ausgewählt", 3000)
    
    def show_apps_panel(self):
        pass  # TODO: implement - switch sidebar to apps panel

    def show_prompts_panel(self):
        pass  # TODO: implement - switch sidebar to prompts panel

    def show_sync_panel(self):
        pass  # TODO: implement - switch sidebar to sync panel

    def _show_privacy_settings(self):
        """Zeigt Datenschutz-Einstellungen"""
        if hasattr(self, 'privacy_monitor'):
            dialog = PrivacySettingsDialog(self.privacy_monitor, self)
            dialog.exec()
        else:
            QMessageBox.information(
                self, "Hinweis",
                "Datenschutz-Monitor nicht initialisiert."
            )
    
    def _show_about(self):
        """Zeigt den Über-Dialog"""
        QMessageBox.about(
            self,
            "Über ExplorerPro",
            """<h2>ExplorerPro</h2>
            <p>Version 0.1.0</p>
            <p>Ein intelligenter Datei-Explorer mit:</p>
            <ul>
                <li>Datenbank-gestützter Volltextsuche</li>
                <li>Integrierter Code-Bearbeitung</li>
                <li>Datenschutz-Ampel</li>
                <li>App-Launcher</li>
                <li>Prompt-Bibliothek</li>
            </ul>
            <p>Fusion aus: ProFiler, PythonBox, ProSync, AmpelTool, SoftwareCenter, ProfiPrompt</p>
            """
        )
