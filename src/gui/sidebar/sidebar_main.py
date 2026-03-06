#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sidebar - Seitenleiste mit Ordnerbaum, Favoriten, Suche, Apps, Prompts, Sync
Phase 5: Vollständige Integration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFrame, QToolButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir, QStandardPaths, QFileInfo
from PyQt6.QtWidgets import QFileIconProvider
import os

# Module importieren - absolute Imports
from gui.sidebar.search_panel import SearchPanel as AdvancedSearchPanel
from modules.launcher import AppsPanel
from modules.prompts import PromptsPanel
from modules.sync import SyncPanel


class TreePanel(QWidget):
    """Ordnerbaum-Panel"""
    
    folder_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_provider = QFileIconProvider()
        self._setup_ui()
        self._populate()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setAnimated(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        
        layout.addWidget(self.tree)
    
    def _populate(self):
        """Füllt den Baum mit Laufwerken und Schnellzugriff"""
        # Schnellzugriff
        quick_access = QTreeWidgetItem(["⭐ Schnellzugriff"])
        quick_access.setFlags(quick_access.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        
        locations = [
            ("Desktop", QStandardPaths.StandardLocation.DesktopLocation),
            ("Dokumente", QStandardPaths.StandardLocation.DocumentsLocation),
            ("Downloads", QStandardPaths.StandardLocation.DownloadLocation),
            ("Bilder", QStandardPaths.StandardLocation.PicturesLocation),
            ("Musik", QStandardPaths.StandardLocation.MusicLocation),
        ]
        
        for name, location in locations:
            path = QStandardPaths.writableLocation(location)
            if path and os.path.exists(path):
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.ItemDataRole.UserRole, path)
                child.setIcon(0, self._icon_provider.icon(QFileInfo(path)))
                quick_access.addChild(child)
        
        self.tree.addTopLevelItem(quick_access)
        quick_access.setExpanded(True)
        
        # Laufwerke
        drives_item = QTreeWidgetItem(["💾 Laufwerke"])
        drives_item.setFlags(drives_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        
        for drive in QDir.drives():
            path = drive.absolutePath()
            item = QTreeWidgetItem([path])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setIcon(0, self._icon_provider.icon(QFileInfo(path)))
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            drives_item.addChild(item)
        
        self.tree.addTopLevelItem(drives_item)
        drives_item.setExpanded(True)
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.folder_selected.emit(path)
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Lazy Loading für Unterordner"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        
        if item.childCount() > 0 and item.child(0).data(0, Qt.ItemDataRole.UserRole):
            return
        
        item.takeChildren()
        
        try:
            for name in os.listdir(path):
                full_path = os.path.join(path, name)
                if os.path.isdir(full_path) and not name.startswith('.'):
                    child = QTreeWidgetItem([name])
                    child.setData(0, Qt.ItemDataRole.UserRole, full_path)
                    child.setIcon(0, self._icon_provider.icon(QFileInfo(full_path)))
                    child.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                    item.addChild(child)
        except PermissionError:
            pass


class FavoritesPanel(QWidget):
    """Favoriten-Panel"""
    
    favorite_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("Favoriten"))
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setToolTip("Aktuellen Ordner zu Favoriten hinzufügen")
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list)
    
    def add_favorite(self, path: str, name: str = None):
        if name is None:
            name = os.path.basename(path) or path
        
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self.list.addItem(item)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.favorite_selected.emit(path)


class Sidebar(QWidget):
    """
    Haupt-Sidebar mit Tab-Navigation:
    - 📁 Ordnerbaum
    - ⭐ Favoriten
    - 🔍 Suche
    - 🚀 Apps
    - 📋 Prompts
    - 🔄 Sync
    """
    
    folder_selected = pyqtSignal(str)
    favorite_selected = pyqtSignal(str)
    app_launched = pyqtSignal(str)
    prompt_copied = pyqtSignal(str)
    sync_finished = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab-Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 4, 4, 4)
        btn_layout.setSpacing(2)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.buttonClicked.connect(self._on_tab_clicked)
        
        tabs = [
            ("📁", "Ordner", 0),
            ("⭐", "Favoriten", 1),
            ("🔍", "Suche", 2),
            ("🚀", "Apps", 3),
            ("📋", "Prompts", 4),
            ("🔄", "Sync", 5),
        ]
        
        for icon, tooltip, idx in tabs:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(36, 36)
            self.btn_group.addButton(btn, idx)
            btn_layout.addWidget(btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Stacked Widget für Panels
        self.stack = QStackedWidget()
        
        # 0: Ordner-Panel
        self.tree_panel = TreePanel()
        self.tree_panel.folder_selected.connect(self.folder_selected)
        self.stack.addWidget(self.tree_panel)
        
        # 1: Favoriten-Panel
        self.favorites_panel = FavoritesPanel()
        self.favorites_panel.favorite_selected.connect(self.favorite_selected)
        self.stack.addWidget(self.favorites_panel)
        
        # 2: Such-Panel
        self.search_panel = AdvancedSearchPanel()
        self.search_panel.result_selected.connect(self.folder_selected)
        self.search_panel.result_activated.connect(self._on_search_result_activated)
        self.stack.addWidget(self.search_panel)
        
        # 3: Apps-Panel (SoftwareCenter-Integration)
        self.apps_panel = AppsPanel()
        self.apps_panel.app_launched.connect(self.app_launched)
        self.stack.addWidget(self.apps_panel)
        
        # 4: Prompts-Panel (ProfiPrompt-Integration)
        self.prompts_panel = PromptsPanel()
        self.prompts_panel.prompt_copied.connect(self.prompt_copied)
        self.stack.addWidget(self.prompts_panel)
        
        # 5: Sync-Panel (ProSync-Integration)
        self.sync_panel = SyncPanel()
        self.sync_panel.sync_finished.connect(self.sync_finished)
        self.stack.addWidget(self.sync_panel)
        
        layout.addWidget(self.stack)
        
        # Ersten Tab aktivieren
        self.btn_group.button(0).setChecked(True)
    
    def _on_tab_clicked(self, button):
        idx = self.btn_group.id(button)
        self.stack.setCurrentIndex(idx)
    
    def _on_search_result_activated(self, path: str):
        """Öffnet Suchergebnis"""
        if os.path.isfile(path):
            folder = os.path.dirname(path)
            self.folder_selected.emit(folder)
        else:
            self.folder_selected.emit(path)
    
    def set_file_index(self, file_index):
        """Setzt den Datei-Index für die Suche"""
        self.search_panel.set_index(file_index)
    
    def switch_to_tab(self, index: int):
        """Wechselt zum angegebenen Tab"""
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            btn = self.btn_group.button(index)
            if btn:
                btn.setChecked(True)
    
    def switch_to_search(self):
        """Wechselt zum Such-Tab"""
        self.switch_to_tab(2)
    
    def switch_to_apps(self):
        """Wechselt zum Apps-Tab"""
        self.switch_to_tab(3)
    
    def switch_to_prompts(self):
        """Wechselt zum Prompts-Tab"""
        self.switch_to_tab(4)
    
    def switch_to_sync(self):
        """Wechselt zum Sync-Tab"""
        self.switch_to_tab(5)
