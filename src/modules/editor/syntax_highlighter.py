#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Syntax Highlighter für verschiedene Programmiersprachen
Basiert auf PythonBox
"""

import re
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)


class BaseHighlighter(QSyntaxHighlighter):
    """Basis-Klasse für Syntax-Highlighting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []
        self._setup_formats()
        self._setup_rules()
    
    def _setup_formats(self):
        """Erstellt die Text-Formate"""
        # Keyword Format (blau, fett)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569CD6"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        # Builtin Format (cyan)
        self.builtin_format = QTextCharFormat()
        self.builtin_format.setForeground(QColor("#4EC9B0"))
        
        # String Format (orange)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))
        
        # Comment Format (grün)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))
        self.comment_format.setFontItalic(True)
        
        # Function Format (gelb)
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))
        
        # Class Format (grün)
        self.class_format = QTextCharFormat()
        self.class_format.setForeground(QColor("#4EC9B0"))
        self.class_format.setFontWeight(QFont.Weight.Bold)
        
        # Number Format (hellgrün)
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#B5CEA8"))
        
        # Decorator Format (gelb)
        self.decorator_format = QTextCharFormat()
        self.decorator_format.setForeground(QColor("#DCDCAA"))
        
        # Operator Format
        self.operator_format = QTextCharFormat()
        self.operator_format.setForeground(QColor("#D4D4D4"))
    
    def _setup_rules(self):
        """Überschreiben für sprachspezifische Regeln"""
    
    def highlightBlock(self, text):
        """Wendet Highlighting auf einen Textblock an"""
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


class PythonHighlighter(BaseHighlighter):
    """Syntax-Highlighting für Python"""
    
    KEYWORDS = [
        'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
        'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
        'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not',
        'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
        'True', 'False', 'None'
    ]
    
    BUILTINS = [
        'print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict',
        'set', 'tuple', 'bool', 'type', 'isinstance', 'hasattr', 'getattr',
        'setattr', 'open', 'input', 'sorted', 'enumerate', 'zip', 'map',
        'filter', 'any', 'all', 'sum', 'min', 'max', 'abs', 'round'
    ]
    
    def _setup_rules(self):
        # Keywords
        keyword_pattern = r'\b(' + '|'.join(self.KEYWORDS) + r')\b'
        self.rules.append((keyword_pattern, self.keyword_format))
        
        # Builtins
        builtin_pattern = r'\b(' + '|'.join(self.BUILTINS) + r')\b'
        self.rules.append((builtin_pattern, self.builtin_format))
        
        # Strings (einfache und doppelte Anführungszeichen)
        self.rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format))
        self.rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format))
        
        # Triple-quoted strings
        self.rules.append((r'""".*?"""', self.string_format))
        self.rules.append((r"'''.*?'''", self.string_format))
        
        # f-strings
        self.rules.append((r'f"[^"]*"', self.string_format))
        self.rules.append((r"f'[^']*'", self.string_format))
        
        # Numbers
        self.rules.append((r'\b\d+\.?\d*\b', self.number_format))
        
        # Function definitions
        self.rules.append((r'\bdef\s+(\w+)', self.function_format))
        
        # Class definitions
        self.rules.append((r'\bclass\s+(\w+)', self.class_format))
        
        # Decorators
        self.rules.append((r'@\w+', self.decorator_format))
        
        # Comments (muss zuletzt kommen)
        self.rules.append((r'#.*$', self.comment_format))


class JavaScriptHighlighter(BaseHighlighter):
    """Syntax-Highlighting für JavaScript"""
    
    KEYWORDS = [
        'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
        'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
        'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new',
        'return', 'static', 'super', 'switch', 'this', 'throw', 'try',
        'typeof', 'var', 'void', 'while', 'with', 'yield', 'async', 'await',
        'true', 'false', 'null', 'undefined'
    ]
    
    def _setup_rules(self):
        # Keywords
        keyword_pattern = r'\b(' + '|'.join(self.KEYWORDS) + r')\b'
        self.rules.append((keyword_pattern, self.keyword_format))
        
        # Strings
        self.rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format))
        self.rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format))
        self.rules.append((r'`[^`]*`', self.string_format))  # Template literals
        
        # Numbers
        self.rules.append((r'\b\d+\.?\d*\b', self.number_format))
        
        # Function definitions
        self.rules.append((r'\bfunction\s+(\w+)', self.function_format))
        self.rules.append((r'(\w+)\s*[=:]\s*(?:async\s+)?function', self.function_format))
        self.rules.append((r'(\w+)\s*[=:]\s*\([^)]*\)\s*=>', self.function_format))
        
        # Comments
        self.rules.append((r'//.*$', self.comment_format))
        self.rules.append((r'/\*.*?\*/', self.comment_format))


class HTMLHighlighter(BaseHighlighter):
    """Syntax-Highlighting für HTML"""
    
    def _setup_rules(self):
        # Tags
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor("#569CD6"))
        self.rules.append((r'</?[\w]+', tag_format))
        self.rules.append((r'/?>', tag_format))
        
        # Attribute names
        attr_format = QTextCharFormat()
        attr_format.setForeground(QColor("#9CDCFE"))
        self.rules.append((r'\s(\w+)=', attr_format))
        
        # Attribute values
        self.rules.append((r'"[^"]*"', self.string_format))
        self.rules.append((r"'[^']*'", self.string_format))
        
        # Comments
        self.rules.append((r'<!--.*?-->', self.comment_format))


class CSSHighlighter(BaseHighlighter):
    """Syntax-Highlighting für CSS"""
    
    def _setup_rules(self):
        # Selectors
        selector_format = QTextCharFormat()
        selector_format.setForeground(QColor("#D7BA7D"))
        self.rules.append((r'[\w.#\[\]=~^$*|-]+\s*(?={)', selector_format))
        
        # Properties
        property_format = QTextCharFormat()
        property_format.setForeground(QColor("#9CDCFE"))
        self.rules.append((r'[\w-]+(?=\s*:)', property_format))
        
        # Values
        self.rules.append((r':\s*([^;{}]+)', self.string_format))
        
        # Numbers with units
        self.rules.append((r'\b\d+\.?\d*(px|em|rem|%|vh|vw|s|ms)?\b', self.number_format))
        
        # Comments
        self.rules.append((r'/\*.*?\*/', self.comment_format))


class JSONHighlighter(BaseHighlighter):
    """Syntax-Highlighting für JSON"""
    
    def _setup_rules(self):
        # Keys
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#9CDCFE"))
        self.rules.append((r'"[^"]*"\s*(?=:)', key_format))
        
        # String values
        self.rules.append((r':\s*"[^"]*"', self.string_format))
        
        # Numbers
        self.rules.append((r'\b-?\d+\.?\d*\b', self.number_format))
        
        # Booleans and null
        self.rules.append((r'\b(true|false|null)\b', self.keyword_format))


class SQLHighlighter(BaseHighlighter):
    """Syntax-Highlighting für SQL"""
    
    KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE',
        'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE',
        'CREATE', 'TABLE', 'DROP', 'ALTER', 'INDEX', 'VIEW',
        'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON',
        'ORDER', 'BY', 'ASC', 'DESC', 'GROUP', 'HAVING',
        'LIMIT', 'OFFSET', 'UNION', 'ALL', 'DISTINCT',
        'AS', 'NULL', 'IS', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'
    ]
    
    def _setup_rules(self):
        # Keywords (case-insensitive)
        keyword_pattern = r'\b(' + '|'.join(self.KEYWORDS) + r')\b'
        self.rules.append((keyword_pattern, self.keyword_format))
        
        # Strings
        self.rules.append((r"'[^']*'", self.string_format))
        
        # Numbers
        self.rules.append((r'\b\d+\.?\d*\b', self.number_format))
        
        # Comments
        self.rules.append((r'--.*$', self.comment_format))
        self.rules.append((r'/\*.*?\*/', self.comment_format))


# ===== Highlighter-Factory =====

HIGHLIGHTERS = {
    '.py': PythonHighlighter,
    '.pyw': PythonHighlighter,
    '.js': JavaScriptHighlighter,
    '.jsx': JavaScriptHighlighter,
    '.ts': JavaScriptHighlighter,
    '.tsx': JavaScriptHighlighter,
    '.html': HTMLHighlighter,
    '.htm': HTMLHighlighter,
    '.xml': HTMLHighlighter,
    '.css': CSSHighlighter,
    '.scss': CSSHighlighter,
    '.less': CSSHighlighter,
    '.json': JSONHighlighter,
    '.sql': SQLHighlighter,
}


def get_lexer_for_extension(extension: str) -> type:
    """
    Gibt die passende Highlighter-Klasse für eine Dateiendung zurück.
    
    Args:
        extension: Dateiendung (z.B. '.py')
    
    Returns:
        Highlighter-Klasse oder None
    """
    return HIGHLIGHTERS.get(extension.lower())
