#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreviewPanel - Vorschau-Panel für Dateien
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget,
    QLabel, QScrollArea, QGroupBox, QFormLayout, QLineEdit,
    QPlainTextEdit, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QFont, QSyntaxHighlighter, QTextCharFormat, QColor
import os
from datetime import datetime

# Optionale Imports
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class PythonHighlighter(QSyntaxHighlighter):
    """Einfacher Python Syntax-Highlighter"""
    
    KEYWORDS = [
        'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
        'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
        'global', 'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal',
        'not', 'or', 'pass', 'raise', 'return', 'True', 'False', 'try',
        'while', 'with', 'yield'
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569CD6"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))
        
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))
    
    def highlightBlock(self, text):
        import re
        
        # Keywords
        for word in self.KEYWORDS:
            pattern = r'\b' + word + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
        
        # Strings
        for pattern in [r'"[^"]*"', r"'[^']*'"]:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        
        # Comments
        if '#' in text:
            idx = text.index('#')
            self.setFormat(idx, len(text) - idx, self.comment_format)
        
        # Functions
        for match in re.finditer(r'\bdef\s+(\w+)', text):
            start = match.start(1)
            length = len(match.group(1))
            self.setFormat(start, length, self.function_format)


class ImagePreview(QLabel):
    """Bild-Vorschau"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self._original_pixmap = None
    
    def load_image(self, path: str):
        """Lädt und zeigt ein Bild"""
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.setText("Bild konnte nicht geladen werden")
                return
            
            self._original_pixmap = pixmap
            self._scale_to_fit()
        except Exception as e:
            self.setText(f"Fehler: {e}")
    
    def _scale_to_fit(self):
        if self._original_pixmap:
            scaled = self._original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)
    
    def resizeEvent(self, event):
        self._scale_to_fit()
        super().resizeEvent(event)


class TextPreview(QPlainTextEdit):
    """Text/Code-Vorschau"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        font = QFont("Consolas", 10)
        self.setFont(font)
        
        self._highlighter = None
    
    def load_file(self, path: str):
        """Lädt eine Textdatei"""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(100000)  # Max 100KB
            
            self.setPlainText(content)
            
            # Syntax-Highlighting für Python
            ext = os.path.splitext(path)[1].lower()
            if ext == '.py':
                self._highlighter = PythonHighlighter(self.document())
            else:
                self._highlighter = None
                
        except Exception as e:
            self.setPlainText(f"Fehler beim Laden: {e}")


class PdfPreview(QScrollArea):
    """PDF-Vorschau (erste Seite)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        
        self.content = QLabel()
        self.content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.setWidget(self.content)
    
    def load_pdf(self, path: str):
        """Lädt ein PDF und zeigt die erste Seite"""
        if not HAS_FITZ:
            self.content.setText("PyMuPDF nicht installiert.\nPDF-Vorschau nicht verfügbar.")
            return
        
        try:
            doc = fitz.open(path)
            if len(doc) > 0:
                page = doc[0]
                mat = fitz.Matrix(1.5, 1.5)  # Zoom
                pix = page.get_pixmap(matrix=mat)
                
                img = QImage(
                    pix.samples,
                    pix.width,
                    pix.height,
                    pix.stride,
                    QImage.Format.Format_RGB888
                )
                
                pixmap = QPixmap.fromImage(img)
                self.content.setPixmap(pixmap)
            else:
                self.content.setText("Leeres PDF")
            
            doc.close()
        except Exception as e:
            self.content.setText(f"Fehler beim Laden: {e}")


class MetadataPanel(QWidget):
    """Metadaten-Anzeige"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Datei-Info
        info_group = QGroupBox("📊 Datei-Information")
        info_layout = QFormLayout(info_group)
        
        self.name_label = QLabel("-")
        info_layout.addRow("Name:", self.name_label)
        
        self.type_label = QLabel("-")
        info_layout.addRow("Typ:", self.type_label)
        
        self.size_label = QLabel("-")
        info_layout.addRow("Größe:", self.size_label)
        
        self.modified_label = QLabel("-")
        info_layout.addRow("Geändert:", self.modified_label)
        
        self.created_label = QLabel("-")
        info_layout.addRow("Erstellt:", self.created_label)
        
        layout.addWidget(info_group)
        
        # Tags
        tags_group = QGroupBox("🏷️ Tags")
        tags_layout = QVBoxLayout(tags_group)
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Tags hinzufügen (kommagetrennt)")
        tags_layout.addWidget(self.tags_edit)
        
        layout.addWidget(tags_group)
        
        # Notizen
        notes_group = QGroupBox("📝 Notizen")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setPlaceholderText("Notizen zur Datei...")
        notes_layout.addWidget(self.notes_edit)
        
        layout.addWidget(notes_group)
        
        layout.addStretch()
    
    def show_metadata(self, path: str):
        """Zeigt Metadaten einer Datei"""
        if not os.path.exists(path):
            return
        
        stat = os.stat(path)
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        
        self.name_label.setText(name)
        self.type_label.setText(ext or "Ordner" if os.path.isdir(path) else "Unbekannt")
        
        # Größe formatieren
        size = stat.st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024*1024):.2f} MB"
        else:
            size_str = f"{size / (1024*1024*1024):.2f} GB"
        self.size_label.setText(size_str)
        
        # Zeitstempel
        modified = datetime.fromtimestamp(stat.st_mtime)
        created = datetime.fromtimestamp(stat.st_ctime)
        
        self.modified_label.setText(modified.strftime("%d.%m.%Y %H:%M"))
        self.created_label.setText(created.strftime("%d.%m.%Y %H:%M"))


class PreviewPanel(QWidget):
    """
    Haupt-Vorschau-Panel mit:
    - Datei-Vorschau (Bild, Text, PDF)
    - Metadaten
    - Tags & Notizen
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self._current_path = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Vorschau-Stack
        self.preview_stack = QStackedWidget()
        
        # Platzhalter
        placeholder = QLabel("Keine Datei ausgewählt")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack.addWidget(placeholder)
        
        # Bild-Vorschau
        self.image_preview = ImagePreview()
        self.preview_stack.addWidget(self.image_preview)
        
        # Text-Vorschau
        self.text_preview = TextPreview()
        self.preview_stack.addWidget(self.text_preview)
        
        # PDF-Vorschau
        self.pdf_preview = PdfPreview()
        self.preview_stack.addWidget(self.pdf_preview)
        
        # Nicht unterstützt
        unsupported = QLabel("Vorschau nicht verfügbar\nfür diesen Dateityp")
        unsupported.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack.addWidget(unsupported)
        
        layout.addWidget(self.preview_stack, 2)
        
        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Metadaten
        self.metadata_panel = MetadataPanel()
        layout.addWidget(self.metadata_panel, 1)
    
    def show_preview(self, path: str):
        """Zeigt Vorschau für eine Datei"""
        if not os.path.exists(path):
            self.preview_stack.setCurrentIndex(0)
            return
        
        self._current_path = path
        ext = os.path.splitext(path)[1].lower()
        
        # Bild-Vorschau
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            self.image_preview.load_image(path)
            self.preview_stack.setCurrentIndex(1)
        
        # Text/Code-Vorschau
        elif ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', 
                     '.xml', '.sql', '.c', '.cpp', '.h', '.java', '.ini', '.cfg']:
            self.text_preview.load_file(path)
            self.preview_stack.setCurrentIndex(2)
        
        # PDF-Vorschau
        elif ext == '.pdf':
            self.pdf_preview.load_pdf(path)
            self.preview_stack.setCurrentIndex(3)
        
        # Nicht unterstützt
        else:
            self.preview_stack.setCurrentIndex(4)
        
        # Metadaten aktualisieren
        self.metadata_panel.show_metadata(path)
