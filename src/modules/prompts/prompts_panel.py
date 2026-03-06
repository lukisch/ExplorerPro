#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PromptsPanel - Prompt-Bibliothek im Sidebar (ProfiPrompt-Integration)
Phase 5: Extras
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit, QDialog, QFormLayout,
    QComboBox, QDialogButtonBox, QMenu, QToolButton, QSplitter,
    QMessageBox, QInputDialog, QApplication, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from pathlib import Path
from typing import List
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Prompt:
    """Repräsentiert einen Prompt"""
    id: str
    title: str
    content: str
    category: str = "Allgemein"
    tags: List[str] = field(default_factory=list)
    created: str = ""
    modified: str = ""
    favorite: bool = False
    use_count: int = 0
    
    def __post_init__(self):
        if not self.id:
            self.id = f"prompt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.modified:
            self.modified = self.created


class PromptEditDialog(QDialog):
    """Dialog zum Bearbeiten/Erstellen eines Prompts"""
    
    def __init__(self, prompt: Prompt = None, categories: List[str] = None, parent=None):
        super().__init__(parent)
        self.prompt = prompt or Prompt(id="", title="", content="")
        self.categories = categories or ["Allgemein", "Code", "Text", "Analyse", "Kreativ"]
        
        self.setWindowTitle("Prompt bearbeiten" if prompt else "Neuer Prompt")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Titel
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Aussagekräftiger Titel...")
        form.addRow("Titel:", self.title_edit)
        
        # Kategorie
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(self.categories)
        form.addRow("Kategorie:", self.category_combo)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("tag1, tag2, tag3 (mit Komma trennen)")
        form.addRow("Tags:", self.tags_edit)
        
        layout.addLayout(form)
        
        # Prompt-Inhalt
        layout.addWidget(QLabel("Prompt:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Prompt-Text hier eingeben...\n\nVariablen: {{variable}} werden beim Kopieren abgefragt")
        self.content_edit.setMinimumHeight(200)
        layout.addWidget(self.content_edit)
        
        # Variablen-Hinweis
        hint = QLabel("💡 Tipp: Verwende {{name}} für Variablen, die beim Einfügen abgefragt werden")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_data(self):
        self.title_edit.setText(self.prompt.title)
        self.category_combo.setCurrentText(self.prompt.category)
        self.tags_edit.setText(", ".join(self.prompt.tags))
        self.content_edit.setPlainText(self.prompt.content)
    
    def _save_and_accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Fehler", "Bitte einen Titel eingeben!")
            return
        
        if not self.content_edit.toPlainText().strip():
            QMessageBox.warning(self, "Fehler", "Bitte Prompt-Inhalt eingeben!")
            return
        
        self.prompt.title = self.title_edit.text().strip()
        self.prompt.category = self.category_combo.currentText()
        self.prompt.content = self.content_edit.toPlainText()
        self.prompt.modified = datetime.now().isoformat()
        
        tags_text = self.tags_edit.text().strip()
        self.prompt.tags = [t.strip() for t in tags_text.split(',') if t.strip()]
        
        self.accept()
    
    def get_prompt(self) -> Prompt:
        return self.prompt


class PromptItem(QListWidgetItem):
    """List-Item für einen Prompt"""
    
    def __init__(self, prompt: Prompt):
        super().__init__()
        self.prompt = prompt
        self._update_display()
    
    def _update_display(self):
        # Icon für Kategorie
        icons = {
            "Code": "💻", "Text": "📝", "Analyse": "📊",
            "Kreativ": "🎨", "Allgemein": "📋", "Chat": "💬",
            "System": "⚙️", "Favoriten": "⭐"
        }
        icon = icons.get(self.prompt.category, "📋")
        star = "⭐ " if self.prompt.favorite else ""
        
        self.setText(f"{star}{icon} {self.prompt.title}")
        
        # Tooltip
        tooltip = f"<b>{self.prompt.title}</b><br>"
        tooltip += f"📁 {self.prompt.category}<br>"
        if self.prompt.tags:
            tooltip += f"🏷️ {', '.join(self.prompt.tags)}<br>"
        tooltip += f"📅 {self.prompt.modified[:10]}<br>"
        tooltip += f"📊 {self.prompt.use_count}x verwendet<br><br>"
        tooltip += f"<i>{self.prompt.content[:200]}...</i>"
        
        self.setToolTip(tooltip)


class PromptsPanel(QWidget):
    """
    Prompt-Bibliothek Panel
    Basiert auf ProfiPrompt
    
    Features:
    - Kategorien & Tags
    - Variablen-Ersetzung {{var}}
    - Quick-Copy mit Strg+C
    - Favoriten
    - Nutzungsstatistik
    """
    
    prompt_copied = pyqtSignal(str)  # Kopierter Prompt-Text
    
    DEFAULT_CATEGORIES = ["Allgemein", "Code", "Text", "Analyse", "Kreativ", "System"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.prompts: List[Prompt] = []
        self.config_path = Path.home() / ".explorerpro" / "prompts.json"
        
        self._setup_ui()
        self._load_prompts()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header
        header = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Prompt suchen...")
        self.search_edit.textChanged.connect(self._filter_prompts)
        header.addWidget(self.search_edit)
        
        add_btn = QToolButton()
        add_btn.setText("➕")
        add_btn.setToolTip("Neuen Prompt erstellen")
        add_btn.clicked.connect(self._add_prompt)
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Filter-Tabs (Kategorien)
        self.category_tabs = QTabWidget()
        self.category_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.category_tabs.setDocumentMode(True)
        self.category_tabs.currentChanged.connect(self._on_category_changed)
        
        # "Alle" Tab
        self.category_tabs.addTab(QWidget(), "📋 Alle")
        
        # Kategorie-Tabs
        for cat in self.DEFAULT_CATEGORIES:
            icons = {
                "Allgemein": "📋", "Code": "💻", "Text": "📝",
                "Analyse": "📊", "Kreativ": "🎨", "System": "⚙️"
            }
            self.category_tabs.addTab(QWidget(), f"{icons.get(cat, '📁')} {cat}")
        
        layout.addWidget(self.category_tabs)
        
        # Splitter für Liste und Preview
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Prompt-Liste
        self.prompt_list = QListWidget()
        self.prompt_list.setAlternatingRowColors(True)
        self.prompt_list.itemClicked.connect(self._on_item_clicked)
        self.prompt_list.itemDoubleClicked.connect(self._copy_prompt)
        self.prompt_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.prompt_list.customContextMenuRequested.connect(self._show_context_menu)
        splitter.addWidget(self.prompt_list)
        
        # Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_label = QLabel("Prompt auswählen...")
        self.preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(self.preview_label)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        preview_layout.addWidget(self.preview_text)
        
        # Aktions-Buttons
        btn_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 Kopieren")
        self.copy_btn.clicked.connect(self._copy_selected)
        self.copy_btn.setEnabled(False)
        btn_layout.addWidget(self.copy_btn)
        
        self.edit_btn = QPushButton("✏️ Bearbeiten")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.edit_btn.setEnabled(False)
        btn_layout.addWidget(self.edit_btn)
        
        btn_layout.addStretch()
        preview_layout.addLayout(btn_layout)
        
        splitter.addWidget(preview_widget)
        splitter.setSizes([200, 100])
        
        layout.addWidget(splitter)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.status_label)
    
    def _load_prompts(self):
        """Lädt Prompts aus JSON"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.prompts = [Prompt(**p) for p in data]
            except Exception as e:
                print(f"Fehler beim Laden der Prompts: {e}")
                self.prompts = []
        
        if not self.prompts:
            self._add_default_prompts()
        
        self._refresh_list()
        self._update_status()
    
    def _add_default_prompts(self):
        """Fügt Beispiel-Prompts hinzu"""
        self.prompts = [
            Prompt(
                id="", title="Code Review",
                content="Bitte überprüfe den folgenden Code auf:\n- Bugs und Fehler\n- Performance-Probleme\n- Best Practices\n- Sicherheitslücken\n\nCode:\n{{code}}",
                category="Code", tags=["review", "analyse"]
            ),
            Prompt(
                id="", title="Text verbessern",
                content="Verbessere den folgenden Text hinsichtlich Grammatik, Stil und Klarheit:\n\n{{text}}",
                category="Text", tags=["korrektur", "verbesserung"]
            ),
            Prompt(
                id="", title="Zusammenfassung erstellen",
                content="Erstelle eine prägnante Zusammenfassung des folgenden Textes in maximal {{länge}} Sätzen:\n\n{{text}}",
                category="Analyse", tags=["zusammenfassung"]
            ),
            Prompt(
                id="", title="Python Funktion",
                content="Schreibe eine Python-Funktion die {{beschreibung}}.\n\nAnforderungen:\n- Type Hints verwenden\n- Docstring hinzufügen\n- Fehlerbehandlung implementieren",
                category="Code", tags=["python", "funktion"]
            ),
            Prompt(
                id="", title="Erkläre wie ein Experte",
                content="Erkläre {{thema}} so, dass es ein {{zielgruppe}} verstehen kann. Verwende Analogien und praktische Beispiele.",
                category="Allgemein", tags=["erklärung", "lernen"]
            ),
        ]
        self._save_prompts()
    
    def _save_prompts(self):
        """Speichert Prompts nach JSON"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for p in self.prompts:
            data.append({
                'id': p.id, 'title': p.title, 'content': p.content,
                'category': p.category, 'tags': p.tags,
                'created': p.created, 'modified': p.modified,
                'favorite': p.favorite, 'use_count': p.use_count
            })
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _refresh_list(self, filter_text: str = "", category: str = None):
        """Aktualisiert die Prompt-Liste"""
        self.prompt_list.clear()
        
        filter_text = filter_text.lower()
        
        for prompt in self.prompts:
            # Kategorie-Filter
            if category and category != "Alle":
                if prompt.category != category:
                    continue
            
            # Text-Filter
            if filter_text:
                if not (filter_text in prompt.title.lower() or
                        filter_text in prompt.content.lower() or
                        any(filter_text in tag.lower() for tag in prompt.tags)):
                    continue
            
            item = PromptItem(prompt)
            self.prompt_list.addItem(item)
        
        self._update_status()
    
    def _filter_prompts(self, text: str):
        """Filtert Prompts nach Suchtext"""
        current_tab = self.category_tabs.currentIndex()
        category = None
        if current_tab > 0:
            category = self.DEFAULT_CATEGORIES[current_tab - 1]
        
        self._refresh_list(text, category)
    
    def _on_category_changed(self, index: int):
        """Kategorie-Tab gewechselt"""
        # Guard: UI noch nicht vollständig initialisiert
        if not hasattr(self, 'prompt_list'):
            return
            
        category = None
        if index > 0:
            category = self.DEFAULT_CATEGORIES[index - 1]
        
        self._refresh_list(self.search_edit.text(), category)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Item angeklickt - Preview zeigen"""
        if isinstance(item, PromptItem):
            self.preview_label.setText(item.prompt.title)
            self.preview_text.setPlainText(item.prompt.content)
            self.copy_btn.setEnabled(True)
            self.edit_btn.setEnabled(True)
    
    def _copy_prompt(self, item: QListWidgetItem):
        """Prompt in Zwischenablage kopieren (mit Variablen-Ersetzung)"""
        if not isinstance(item, PromptItem):
            return
        
        prompt = item.prompt
        content = prompt.content
        
        # Variablen finden: {{var}}
        import re
        variables = re.findall(r'\{\{(\w+)\}\}', content)
        
        if variables:
            # Variablen abfragen
            for var in set(variables):
                value, ok = QInputDialog.getText(
                    self, f"Variable: {var}",
                    f"Wert für '{var}' eingeben:"
                )
                if ok:
                    content = content.replace(f"{{{{{var}}}}}", value)
                else:
                    return  # Abgebrochen
        
        # In Zwischenablage kopieren
        clipboard = QApplication.clipboard()
        clipboard.setText(content)
        
        # Statistik aktualisieren
        prompt.use_count += 1
        self._save_prompts()
        
        self.status_label.setText(f"✅ '{prompt.title}' kopiert!")
        self.prompt_copied.emit(content)
    
    def _copy_selected(self):
        """Ausgewählten Prompt kopieren"""
        item = self.prompt_list.currentItem()
        if item:
            self._copy_prompt(item)
    
    def _edit_selected(self):
        """Ausgewählten Prompt bearbeiten"""
        item = self.prompt_list.currentItem()
        if isinstance(item, PromptItem):
            self._edit_prompt(item.prompt)
    
    def _add_prompt(self):
        """Neuen Prompt erstellen"""
        dialog = PromptEditDialog(categories=self.DEFAULT_CATEGORIES, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            prompt = dialog.get_prompt()
            self.prompts.append(prompt)
            self._save_prompts()
            self._refresh_list()
    
    def _edit_prompt(self, prompt: Prompt):
        """Prompt bearbeiten"""
        dialog = PromptEditDialog(prompt, self.DEFAULT_CATEGORIES, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_prompts()
            self._refresh_list()
    
    def _delete_prompt(self, prompt: Prompt):
        """Prompt löschen"""
        if QMessageBox.question(
            self, "Löschen",
            f"'{prompt.title}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.prompts.remove(prompt)
            self._save_prompts()
            self._refresh_list()
    
    def _toggle_favorite(self, prompt: Prompt):
        """Favorit umschalten"""
        prompt.favorite = not prompt.favorite
        self._save_prompts()
        self._refresh_list()
    
    def _show_context_menu(self, pos):
        """Kontextmenü"""
        item = self.prompt_list.itemAt(pos)
        if not isinstance(item, PromptItem):
            return
        
        prompt = item.prompt
        menu = QMenu(self)
        
        menu.addAction("📋 Kopieren", lambda: self._copy_prompt(item))
        menu.addAction("✏️ Bearbeiten", lambda: self._edit_prompt(prompt))
        menu.addSeparator()
        
        fav_text = "⭐ Aus Favoriten entfernen" if prompt.favorite else "⭐ Zu Favoriten"
        menu.addAction(fav_text, lambda: self._toggle_favorite(prompt))
        
        menu.addSeparator()
        menu.addAction("🗑️ Löschen", lambda: self._delete_prompt(prompt))
        
        menu.exec(QCursor.pos())
    
    def _update_status(self):
        """Aktualisiert Status-Anzeige"""
        total = len(self.prompts)
        shown = self.prompt_list.count()
        self.status_label.setText(f"{shown} von {total} Prompts")
