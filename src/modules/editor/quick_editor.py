#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuickEditorDialog - Schneller Code-Editor
Basiert auf PythonBox
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QSplitter, QTextEdit, QFileDialog,
    QMessageBox, QShortcut
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal
from PyQt6.QtGui import (
    QFont, QTextCursor, QKeySequence, QTextOption,
    QPainter, QColor
)

from .syntax_highlighter import get_lexer_for_extension


class LineNumberArea(QPlainTextEdit):
    """Text-Editor mit Zeilennummern"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        
        # Tab-Breite
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(' ') * 4
        )
        
        # Word Wrap aus
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        
        # Zeilennummern-Bereich
        self.line_number_area = QWidget(self)
        
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        
        self._update_line_number_width(0)
        self._highlight_current_line()
    
    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def _update_line_number_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), 
                self.line_number_area.width(), rect.height()
            )
        
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width(0)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()
        )
    
    def _highlight_current_line(self):
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2D2D30")
            selection.format.setBackground(line_color)
            selection.format.setProperty(
                QTextFormat.Property.FullWidthSelection, True
            )
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#1E1E1E"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0, top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number
                )
            
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1


# Importiere QTextFormat für FullWidthSelection
from PyQt6.QtGui import QTextFormat


class LineNumberWidget(QWidget):
    """Widget für Zeilennummern"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QSize


class CodeEditor(QPlainTextEdit):
    """Erweiterter Code-Editor mit Zeilennummern"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        
        # Tab-Breite (4 Leerzeichen)
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(' ') * 4
        )
        
        # Word Wrap aus
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        
        # Dark Theme
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                selection-background-color: #264F78;
            }
        """)
        
        # Highlighter
        self._highlighter = None
    
    def set_highlighter(self, extension: str):
        """Setzt den Syntax-Highlighter basierend auf der Dateiendung"""
        highlighter_class = get_lexer_for_extension(extension)
        if highlighter_class:
            self._highlighter = highlighter_class(self.document())
        else:
            self._highlighter = None
    
    def keyPressEvent(self, event):
        """Erweiterte Tastatureingabe"""
        # Tab -> 4 Leerzeichen
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return
        
        # Auto-Einrückung bei Enter
        if event.key() == Qt.Key.Key_Return:
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = len(line) - len(line.lstrip())
            
            # Extra Einrückung nach ':'
            if line.rstrip().endswith(':'):
                indent += 4
            
            super().keyPressEvent(event)
            self.insertPlainText(' ' * indent)
            return
        
        super().keyPressEvent(event)


class QuickEditorDialog(QDialog):
    """
    Schneller Code-Editor Dialog.
    Basiert auf PythonBox-Funktionalität.
    """
    
    file_saved = pyqtSignal(str)
    
    def __init__(self, filepath: Optional[str] = None, parent=None):
        super().__init__(parent)
        
        self.filepath = filepath
        self._modified = False
        self._process = None
        
        self._setup_ui()
        
        if filepath:
            self._load_file(filepath)
    
    def _setup_ui(self):
        self.setWindowTitle("Quick Editor")
        self.resize(900, 700)
        
        # Dark Theme für Dialog
        self.setStyleSheet("""
            QDialog { background-color: #252526; }
            QLabel { color: #D4D4D4; }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 2px;
            }
            QPushButton:hover { background-color: #1177BB; }
            QPushButton:pressed { background-color: #0D5A8A; }
            QPushButton#danger {
                background-color: #F14C4C;
            }
            QPushButton#danger:hover { background-color: #F55; }
            QSplitter::handle { background: #3C3C3C; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 8, 8, 8)
        
        self.file_label = QLabel("Neue Datei")
        self.file_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        toolbar.addWidget(self.file_label)
        
        toolbar.addStretch()
        
        # Buttons
        self.btn_save = QPushButton("💾 Speichern")
        self.btn_save.setShortcut(QKeySequence.StandardKey.Save)
        self.btn_save.clicked.connect(self._save_file)
        toolbar.addWidget(self.btn_save)
        
        self.btn_run = QPushButton("▶ Ausführen")
        self.btn_run.setShortcut(QKeySequence("F5"))
        self.btn_run.clicked.connect(self._run_code)
        toolbar.addWidget(self.btn_run)
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.clicked.connect(self._stop_process)
        self.btn_stop.setEnabled(False)
        toolbar.addWidget(self.btn_stop)
        
        layout.addLayout(toolbar)
        
        # Splitter für Editor und Output
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Editor
        self.editor = CodeEditor()
        self.editor.textChanged.connect(self._on_text_changed)
        splitter.addWidget(self.editor)
        
        # Output Panel
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: none;
                border-top: 1px solid #3C3C3C;
            }
        """)
        self.output.setPlaceholderText("Ausgabe wird hier angezeigt...")
        splitter.addWidget(self.output)
        
        splitter.setSizes([500, 200])
        layout.addWidget(splitter)
        
        # Statusbar
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(8, 4, 8, 4)
        
        self.line_label = QLabel("Zeile: 1, Spalte: 1")
        self.line_label.setStyleSheet("color: #858585;")
        status_layout.addWidget(self.line_label)
        
        status_layout.addStretch()
        
        self.encoding_label = QLabel("UTF-8")
        self.encoding_label.setStyleSheet("color: #858585;")
        status_layout.addWidget(self.encoding_label)
        
        self.modified_label = QLabel("")
        self.modified_label.setStyleSheet("color: #F14C4C;")
        status_layout.addWidget(self.modified_label)
        
        layout.addLayout(status_layout)
        
        # Cursor-Position tracken
        self.editor.cursorPositionChanged.connect(self._update_cursor_position)
        
        # Shortcuts
        QShortcut(QKeySequence("Ctrl+G"), self, self._goto_line)
        QShortcut(QKeySequence("Ctrl+F"), self, self._find_text)
    
    def _load_file(self, filepath: str):
        """Lädt eine Datei"""
        self.filepath = filepath
        path = Path(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            self.editor.setPlainText(content)
            self.editor.set_highlighter(path.suffix)
            
            self.file_label.setText(path.name)
            self.setWindowTitle(f"Quick Editor - {path.name}")
            
            self._modified = False
            self.modified_label.setText("")
            
            # Cursor an den Anfang
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden:\n{e}")
    
    def _save_file(self):
        """Speichert die Datei"""
        if not self.filepath:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Speichern unter",
                "", "Python (*.py);;Alle (*.*)"
            )
            if not filepath:
                return
            self.filepath = filepath
        
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            
            self._modified = False
            self.modified_label.setText("")
            self.file_label.setText(Path(self.filepath).name)
            self.setWindowTitle(f"Quick Editor - {Path(self.filepath).name}")
            
            self.file_saved.emit(self.filepath)
            self._add_output(f"✓ Gespeichert: {self.filepath}\n", "#4EC9B0")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern:\n{e}")
    
    def _on_text_changed(self):
        """Handler für Textänderungen"""
        if not self._modified:
            self._modified = True
            self.modified_label.setText("●")
    
    def _update_cursor_position(self):
        """Aktualisiert die Cursor-Position in der Statusbar"""
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.line_label.setText(f"Zeile: {line}, Spalte: {col}")
    
    def _run_code(self):
        """Führt den Code aus"""
        # Erst speichern
        if self._modified and self.filepath:
            self._save_file()
        
        if not self.filepath:
            QMessageBox.warning(self, "Warnung", "Bitte zuerst speichern!")
            return
        
        ext = Path(self.filepath).suffix.lower()
        
        self.output.clear()
        self._add_output(f"▶ Starte: {self.filepath}\n", "#569CD6")
        self._add_output("-" * 50 + "\n", "#3C3C3C")
        
        # Process starten
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.finished.connect(self._process_finished)
        
        if ext == '.py':
            self._process.start(sys.executable, [self.filepath])
        elif ext == '.js':
            self._process.start('node', [self.filepath])
        else:
            self._add_output(f"Keine Ausführung für {ext} unterstützt\n", "#F14C4C")
            return
        
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
    
    def _stop_process(self):
        """Stoppt den laufenden Prozess"""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._add_output("\n⏹ Prozess abgebrochen\n", "#F14C4C")
    
    def _read_stdout(self):
        """Liest stdout vom Prozess"""
        data = self._process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self._add_output(data)
    
    def _read_stderr(self):
        """Liest stderr vom Prozess"""
        data = self._process.readAllStandardError().data().decode('utf-8', errors='replace')
        self._add_output(data, "#F14C4C")
    
    def _process_finished(self, exit_code, exit_status):
        """Handler für Prozess-Ende"""
        self._add_output("-" * 50 + "\n", "#3C3C3C")
        if exit_code == 0:
            self._add_output(f"✓ Beendet (Exit-Code: {exit_code})\n", "#4EC9B0")
        else:
            self._add_output(f"✗ Beendet mit Fehler (Exit-Code: {exit_code})\n", "#F14C4C")
        
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._process = None
    
    def _add_output(self, text: str, color: str = "#CCCCCC"):
        """Fügt Text zum Output hinzu"""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = cursor.charFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()
    
    def _goto_line(self):
        """Springt zu einer bestimmten Zeile"""
        from PyQt6.QtWidgets import QInputDialog
        
        line, ok = QInputDialog.getInt(
            self, "Gehe zu Zeile",
            "Zeilennummer:", 1, 1, 
            self.editor.blockCount()
        )
        
        if ok:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.NextBlock,
                QTextCursor.MoveMode.MoveAnchor,
                line - 1
            )
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()
    
    def _find_text(self):
        """Öffnet Such-Dialog"""
        from PyQt6.QtWidgets import QInputDialog
        
        text, ok = QInputDialog.getText(
            self, "Suchen", "Suchbegriff:"
        )
        
        if ok and text:
            found = self.editor.find(text)
            if not found:
                # Von Anfang suchen
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.editor.setTextCursor(cursor)
                self.editor.find(text)
    
    def closeEvent(self, event):
        """Handler für Schließen"""
        if self._modified:
            reply = QMessageBox.question(
                self, "Ungespeicherte Änderungen",
                "Es gibt ungespeicherte Änderungen.\nTrotzdem schließen?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
        
        # Prozess beenden
        if self._process:
            self._process.kill()
