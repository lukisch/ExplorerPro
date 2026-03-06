#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AppsPanel - App-Launcher im Sidebar (SoftwareCenter-Integration)
Phase 5: Extras
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QPushButton, QLabel, QLineEdit, QTabWidget, QMenu, QDialog,
    QFormLayout, QComboBox, QDialogButtonBox, QFileDialog,
    QMessageBox, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QCursor
from pathlib import Path
from typing import List
from dataclasses import dataclass
import json
import os
import subprocess


@dataclass
class AppEntry:
    """Repräsentiert eine App"""
    name: str
    path: str
    icon: str = ""
    category: str = "Allgemein"
    description: str = ""
    arguments: str = ""
    working_dir: str = ""
    favorite: bool = False


class AppButton(QPushButton):
    """Button für eine App mit Icon und Name"""
    
    app_clicked = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    
    def __init__(self, app: AppEntry, parent=None):
        super().__init__(parent)
        self.app = app
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedSize(80, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{self.app.name}\n{self.app.path}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(40, 40)
        
        if self.app.icon and os.path.exists(self.app.icon):
            pixmap = QPixmap(self.app.icon).scaled(
                32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            icon_label.setPixmap(pixmap)
        else:
            ext = Path(self.app.path).suffix.lower()
            emoji = self._get_emoji_for_ext(ext)
            icon_label.setText(emoji)
            icon_label.setStyleSheet("font-size: 24px;")
        
        layout.addWidget(icon_label)
        
        # Name
        name_label = QLabel(self.app.name[:12])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 10px;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        self.clicked.connect(lambda: self.app_clicked.emit(self.app))
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _get_emoji_for_ext(self, ext: str) -> str:
        mapping = {
            '.exe': '🖥️', '.py': '🐍', '.js': '📜',
            '.bat': '⚙️', '.cmd': '⚙️', '.ps1': '💠',
            '.sh': '🐚', '.msi': '📦', '.lnk': '🔗',
        }
        return mapping.get(ext, '📁')
    
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("▶️ Starten", lambda: self.app_clicked.emit(self.app))
        menu.addSeparator()
        menu.addAction("✏️ Bearbeiten", lambda: self.edit_requested.emit(self.app))
        menu.addAction("📁 Ordner öffnen", self._open_folder)
        menu.addSeparator()
        menu.addAction("🗑️ Entfernen", lambda: self.delete_requested.emit(self.app))
        menu.exec(QCursor.pos())
    
    def _open_folder(self):
        folder = str(Path(self.app.path).parent)
        if os.name == 'nt':
            os.startfile(folder)
        else:
            subprocess.run(['xdg-open', folder])


class AppEditDialog(QDialog):
    """Dialog zum Bearbeiten/Erstellen einer App"""
    
    def __init__(self, app: AppEntry = None, parent=None):
        super().__init__(parent)
        self.app = app or AppEntry(name="", path="")
        self.setWindowTitle("App bearbeiten" if app else "Neue App")
        self.setMinimumWidth(450)
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        path_btn = QPushButton("...")
        path_btn.setFixedWidth(30)
        path_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)
        form.addRow("Pfad:", path_layout)
        
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            "Allgemein", "Entwicklung", "Office", "Grafik", 
            "Multimedia", "Internet", "System", "Spiele"
        ])
        form.addRow("Kategorie:", self.category_combo)
        
        self.desc_edit = QLineEdit()
        form.addRow("Beschreibung:", self.desc_edit)
        
        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("z.B. --verbose --config=config.ini")
        form.addRow("Argumente:", self.args_edit)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_data(self):
        self.name_edit.setText(self.app.name)
        self.path_edit.setText(self.app.path)
        self.category_combo.setCurrentText(self.app.category)
        self.desc_edit.setText(self.app.description)
        self.args_edit.setText(self.app.arguments)
    
    def _browse_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Programm wählen", "",
            "Ausführbare Dateien (*.exe *.bat *.cmd *.py);;Alle (*.*)"
        )
        if path:
            self.path_edit.setText(path)
            if not self.name_edit.text():
                self.name_edit.setText(Path(path).stem)
    
    def _save_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Bitte Namen eingeben!")
            return
        if not self.path_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Bitte Pfad angeben!")
            return
        
        self.app.name = self.name_edit.text().strip()
        self.app.path = self.path_edit.text().strip()
        self.app.category = self.category_combo.currentText()
        self.app.description = self.desc_edit.text().strip()
        self.app.arguments = self.args_edit.text().strip()
        self.accept()
    
    def get_app(self) -> AppEntry:
        return self.app


class AppsPanel(QWidget):
    """App-Launcher Panel mit Kategorien-Tabs"""
    
    app_launched = pyqtSignal(str)
    
    DEFAULT_CATEGORIES = ["Favoriten", "Entwicklung", "Office", "System", "Allgemein"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.apps: List[AppEntry] = []
        self.config_path = Path.home() / ".explorerpro" / "apps.json"
        self._setup_ui()
        self._load_apps()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Header mit Suche
        header = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 App suchen...")
        self.search_edit.textChanged.connect(self._filter_apps)
        header.addWidget(self.search_edit)
        
        add_btn = QToolButton()
        add_btn.setText("➕")
        add_btn.setToolTip("App hinzufügen")
        add_btn.clicked.connect(self._add_app)
        header.addWidget(add_btn)
        layout.addLayout(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)
        
        self.category_widgets = {}
        for cat in self.DEFAULT_CATEGORIES:
            self._create_category_tab(cat)
    
    def _create_category_tab(self, category: str):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(container)
        
        self.category_widgets[category] = {
            'scroll': scroll, 'container': container,
            'grid': grid, 'buttons': []
        }
        
        icons = {
            "Favoriten": "⭐", "Entwicklung": "💻", "Office": "📄",
            "System": "⚙️", "Allgemein": "📁", "Grafik": "🎨",
            "Multimedia": "🎬", "Internet": "🌐", "Spiele": "🎮"
        }
        self.tabs.addTab(scroll, f"{icons.get(category, '📁')} {category}")
    
    def _load_apps(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.apps = [AppEntry(**a) for a in json.load(f)]
            except:
                self.apps = []
        
        if not self.apps:
            self._add_default_apps()
        self._refresh_display()
    
    def _add_default_apps(self):
        self.apps = [
            AppEntry("Notepad", "notepad.exe", category="System"),
            AppEntry("Explorer", "explorer.exe", category="System"),
            AppEntry("CMD", "cmd.exe", category="System"),
            AppEntry("PowerShell", "powershell.exe", category="System"),
            AppEntry("Rechner", "calc.exe", category="System"),
        ]
        
        dev_paths = [
            (r"C:\Program Files\Microsoft VS Code\Code.exe", "VS Code", "Entwicklung"),
            (r"C:\Program Files\Git\git-bash.exe", "Git Bash", "Entwicklung"),
        ]
        for path, name, cat in dev_paths:
            if os.path.exists(path):
                self.apps.append(AppEntry(name, path, category=cat))
        
        self._save_apps()
    
    def _save_apps(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = [{
            'name': a.name, 'path': a.path, 'icon': a.icon,
            'category': a.category, 'description': a.description,
            'arguments': a.arguments, 'working_dir': a.working_dir,
            'favorite': a.favorite
        } for a in self.apps]
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _refresh_display(self):
        for cat_data in self.category_widgets.values():
            for btn in cat_data['buttons']:
                btn.deleteLater()
            cat_data['buttons'] = []
        
        apps_by_cat = {}
        for app in self.apps:
            if app.category not in apps_by_cat:
                apps_by_cat[app.category] = []
            apps_by_cat[app.category].append(app)
            if app.favorite:
                apps_by_cat.setdefault("Favoriten", []).append(app)
        
        for category, cat_data in self.category_widgets.items():
            apps = apps_by_cat.get(category, [])
            grid = cat_data['grid']
            
            for i, app in enumerate(apps):
                btn = AppButton(app)
                btn.app_clicked.connect(self._launch_app)
                btn.edit_requested.connect(self._edit_app)
                btn.delete_requested.connect(self._delete_app)
                grid.addWidget(btn, i // 4, i % 4)
                cat_data['buttons'].append(btn)
    
    def _filter_apps(self, text: str):
        text = text.lower()
        for cat_data in self.category_widgets.values():
            for btn in cat_data['buttons']:
                btn.setVisible(
                    text in btn.app.name.lower() or
                    text in btn.app.path.lower()
                )
    
    def _add_app(self):
        dialog = AppEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app = dialog.get_app()
            if app.category not in self.category_widgets:
                self._create_category_tab(app.category)
            self.apps.append(app)
            self._save_apps()
            self._refresh_display()
    
    def _edit_app(self, app: AppEntry):
        dialog = AppEditDialog(app, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_apps()
            self._refresh_display()
    
    def _delete_app(self, app: AppEntry):
        if QMessageBox.question(
            self, "Entfernen", f"'{app.name}' entfernen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.apps.remove(app)
            self._save_apps()
            self._refresh_display()
    
    def _launch_app(self, app: AppEntry):
        try:
            if os.name == 'nt':
                if app.arguments:
                    subprocess.Popen([app.path] + app.arguments.split(), shell=True)
                else:
                    os.startfile(app.path)
            else:
                subprocess.Popen([app.path] + (app.arguments.split() if app.arguments else []))
            self.app_launched.emit(app.path)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Konnte nicht starten:\n{e}")
