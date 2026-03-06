#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileIndex - SQLite-basierte Dateiindizierung
Basiert auf ProFiler V14
"""

import os
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal

# Optionale Imports
try:
    from PyPDF2 import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


@dataclass
class IndexEntry:
    """Repräsentiert einen Eintrag im Datei-Index"""
    id: int
    path: str
    filename: str
    extension: str
    size: int
    modified: datetime
    created: datetime
    hash: Optional[str]
    category: str
    text_content: Optional[str]
    tags: List[str]
    notes: str
    indexed_at: datetime


class FileIndex:
    """
    SQLite-basierte Dateiindizierung.
    Ermöglicht Volltextsuche, Hash-Duplikatenerkennung und Metadaten-Speicherung.
    """
    
    # Dateikategorien
    CATEGORIES = {
        "Dokumente": ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf', '.odt'],
        "Bilder": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
        "Audio": ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
        "Video": ['.mp4', '.mkv', '.avi', '.mov', '.wmv'],
        "Archive": ['.zip', '.rar', '.7z', '.tar', '.gz'],
        "Code": ['.py', '.js', '.html', '.css', '.json', '.xml', '.sql', '.cpp', '.c', '.h'],
        "Tabellen": ['.xls', '.xlsx', '.csv'],
    }
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from .settings_manager import SettingsManager
            config_dir = SettingsManager.instance().config_dir
            db_path = str(config_dir / "explorer.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialisiert die Datenbankstruktur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Haupttabelle für Dateien
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT,
                size INTEGER,
                modified TIMESTAMP,
                created TIMESTAMP,
                hash TEXT,
                category TEXT,
                text_content TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tags-Tabelle (Many-to-Many)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (file_id, tag_id),
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')
        
        # Notizen-Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER UNIQUE,
                content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')
        
        # FTS5 für Volltextsuche
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                path, filename, text_content,
                content='files',
                content_rowid='id'
            )
        ''')
        
        # Trigger für FTS-Synchronisation
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, path, filename, text_content)
                VALUES (new.id, new.path, new.filename, new.text_content);
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, path, filename, text_content)
                VALUES ('delete', old.id, old.path, old.filename, old.text_content);
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, path, filename, text_content)
                VALUES ('delete', old.id, old.path, old.filename, old.text_content);
                INSERT INTO files_fts(rowid, path, filename, text_content)
                VALUES (new.id, new.path, new.filename, new.text_content);
            END
        ''')
        
        # Indizes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_category ON files(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)')
        
        conn.commit()
        conn.close()
    
    def get_category(self, filename: str) -> str:
        """Bestimmt die Kategorie einer Datei"""
        ext = os.path.splitext(filename)[1].lower()
        for category, extensions in self.CATEGORIES.items():
            if ext in extensions:
                return category
        return "Andere"
    
    @staticmethod
    def calculate_hash(filepath: str, chunk_size: int = 1024*1024) -> Optional[str]:
        """Berechnet SHA256 Hash einer Datei"""
        h = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except (PermissionError, OSError):
            return None
    
    def extract_text(self, filepath: str) -> Optional[str]:
        """Extrahiert Text aus Dateien (PDF, TXT, etc.)"""
        ext = os.path.splitext(filepath)[1].lower()
        
        try:
            if ext == '.txt' or ext == '.md':
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()[:50000]  # Max 50KB Text
            
            elif ext == '.pdf' and HAS_FITZ:
                doc = fitz.open(filepath)
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
                return '\n'.join(text_parts)[:50000]
            
            elif ext == '.pdf' and HAS_PDF:
                with open(filepath, 'rb') as f:
                    reader = PdfReader(f)
                    text_parts = []
                    for page in reader.pages[:20]:  # Max 20 Seiten
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                return '\n'.join(text_parts)[:50000]
                
        except Exception as e:
            print(f"Text-Extraktion fehlgeschlagen für {filepath}: {e}")
        
        return None
    
    def index_file(self, filepath: str, calculate_hash: bool = True) -> bool:
        """Indiziert eine einzelne Datei"""
        if not os.path.exists(filepath):
            return False
        
        try:
            stat = os.stat(filepath)
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1].lower()
            
            file_hash = None
            if calculate_hash and stat.st_size < 100 * 1024 * 1024:  # Max 100MB
                file_hash = self.calculate_hash(filepath)
            
            text_content = self.extract_text(filepath)
            category = self.get_category(filename)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO files 
                (path, filename, extension, size, modified, created, hash, category, text_content, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filepath,
                filename,
                ext,
                stat.st_size,
                datetime.fromtimestamp(stat.st_mtime),
                datetime.fromtimestamp(stat.st_ctime),
                file_hash,
                category,
                text_content,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Indizierung fehlgeschlagen für {filepath}: {e}")
            return False
    
    def search(self, query: str, extension: str = None, category: str = None,
               min_size: int = None, max_size: int = None, 
               content_only: bool = False, limit: int = 100) -> List[Dict]:
        """
        Volltextsuche im Index mit optionalen Filtern.
        
        Args:
            query: Suchbegriff
            extension: Dateierweiterung (z.B. '.pdf')
            category: Kategorie (z.B. 'Dokumente')
            min_size: Minimale Dateigröße in Bytes
            max_size: Maximale Dateigröße in Bytes
            content_only: Nur im Inhalt suchen (nicht im Dateinamen)
            limit: Maximale Anzahl Ergebnisse
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Basis-Query mit FTS5
        if content_only:
            fts_query = f'text_content:{query}'
        else:
            fts_query = query
        
        sql = '''
            SELECT f.*, bm25(files_fts) as score,
                   snippet(files_fts, 2, '>>>', '<<<', '...', 32) as snippet
            FROM files f
            JOIN files_fts fts ON f.id = fts.rowid
            WHERE files_fts MATCH ?
        '''
        params = [fts_query]
        
        # Filter hinzufügen
        if extension:
            if extension.startswith('.'):
                sql += ' AND f.extension = ?'
                params.append(extension)
            else:
                sql += ' AND f.extension = ?'
                params.append(f'.{extension}')
        
        if category:
            sql += ' AND f.category = ?'
            params.append(category)
        
        if min_size is not None:
            sql += ' AND f.size >= ?'
            params.append(min_size)
        
        if max_size is not None:
            sql += ' AND f.size <= ?'
            params.append(max_size)
        
        sql += ' ORDER BY score LIMIT ?'
        params.append(limit)
        
        try:
            cursor.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Datum parsen
                if result.get('modified'):
                    try:
                        result['modified'] = datetime.fromisoformat(str(result['modified']))
                    except:
                        result['modified'] = None
                results.append(result)
        except sqlite3.OperationalError:
            # Falls FTS-Query ungültig, Fallback auf LIKE
            results = self._search_fallback(query, extension, category, min_size, max_size, limit)
        
        conn.close()
        return results
    
    def _search_fallback(self, query: str, extension: str = None, category: str = None,
                         min_size: int = None, max_size: int = None, limit: int = 100) -> List[Dict]:
        """Fallback-Suche mit LIKE wenn FTS fehlschlägt"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = '''
            SELECT * FROM files
            WHERE (filename LIKE ? OR text_content LIKE ?)
        '''
        like_pattern = f'%{query}%'
        params = [like_pattern, like_pattern]
        
        if extension:
            sql += ' AND extension = ?'
            params.append(extension if extension.startswith('.') else f'.{extension}')
        
        if category:
            sql += ' AND category = ?'
            params.append(category)
        
        if min_size:
            sql += ' AND size >= ?'
            params.append(min_size)
        
        if max_size:
            sql += ' AND size <= ?'
            params.append(max_size)
        
        sql += ' ORDER BY modified DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def advanced_search(self, query: str = None, extensions: List[str] = None,
                       date_from = None, date_to = None,
                       min_size: int = None, max_size: int = None,
                       tags: List[str] = None, use_regex: bool = False,
                       case_sensitive: bool = False, search_name: bool = True,
                       search_content: bool = True, search_path: bool = False,
                       limit: int = 500, **kwargs) -> List[Dict]:
        """
        Erweiterte Suche mit umfangreichen Filtern.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = 'SELECT DISTINCT f.* FROM files f'
        params = []
        conditions = []
        
        # Tags-Join wenn nötig
        if tags:
            sql += '''
                JOIN file_tags ft ON f.id = ft.file_id
                JOIN tags t ON ft.tag_id = t.id
            '''
            placeholders = ','.join(['?' for _ in tags])
            conditions.append(f't.name IN ({placeholders})')
            params.extend(tags)
        
        # Query-Bedingung
        if query:
            query_conditions = []
            pattern = f'%{query}%'
            
            if search_name:
                query_conditions.append('LOWER(f.filename) LIKE LOWER(?)')
                params.append(pattern)
            
            if search_content:
                query_conditions.append('LOWER(f.text_content) LIKE LOWER(?)')
                params.append(pattern)
            
            if search_path:
                query_conditions.append('LOWER(f.path) LIKE LOWER(?)')
                params.append(pattern)
            
            if query_conditions:
                conditions.append(f'({" OR ".join(query_conditions)})')
        
        # Extensions
        if extensions:
            normalized_ext = [e if e.startswith('.') else f'.{e}' for e in extensions]
            placeholders = ','.join(['?' for _ in normalized_ext])
            conditions.append(f'f.extension IN ({placeholders})')
            params.extend(normalized_ext)
        
        # Datum
        if date_from:
            conditions.append('f.modified >= ?')
            params.append(str(date_from))
        
        if date_to:
            conditions.append('f.modified <= ?')
            params.append(str(date_to))
        
        # Größe
        if min_size is not None:
            conditions.append('f.size >= ?')
            params.append(min_size)
        
        if max_size is not None:
            conditions.append('f.size <= ?')
            params.append(max_size)
        
        # WHERE zusammenbauen
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
        
        sql += ' ORDER BY f.modified DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def find_duplicates(self) -> List[Tuple[str, List[str]]]:
        """Findet Duplikate basierend auf Hash"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT hash, GROUP_CONCAT(path, '|||') as paths
            FROM files
            WHERE hash IS NOT NULL
            GROUP BY hash
            HAVING COUNT(*) > 1
        ''')
        
        results = []
        for row in cursor.fetchall():
            hash_val, paths_str = row
            paths = paths_str.split('|||')
            results.append((hash_val, paths))
        
        conn.close()
        return results
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken zum Index zurück"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM files')
        stats['total_files'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(size) FROM files')
        stats['total_size'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT category, COUNT(*) FROM files GROUP BY category')
        stats['by_category'] = dict(cursor.fetchall())
        
        conn.close()
        return stats


class IndexWorker(QThread):
    """Worker-Thread für Hintergrund-Indizierung"""
    
    progress = pyqtSignal(int, int)  # current, total
    file_indexed = pyqtSignal(str)
    finished_indexing = pyqtSignal(int)  # total indexed
    error = pyqtSignal(str)
    
    def __init__(self, index: FileIndex, folder: str, recursive: bool = True):
        super().__init__()
        self.index = index
        self.folder = folder
        self.recursive = recursive
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        """Führt die Indizierung im Hintergrund aus"""
        indexed_count = 0
        
        try:
            files = []
            if self.recursive:
                for root, _, filenames in os.walk(self.folder):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
            else:
                files = [
                    os.path.join(self.folder, f) 
                    for f in os.listdir(self.folder) 
                    if os.path.isfile(os.path.join(self.folder, f))
                ]
            
            total = len(files)
            
            for i, filepath in enumerate(files):
                if self._cancelled:
                    break
                
                if self.index.index_file(filepath):
                    indexed_count += 1
                    self.file_indexed.emit(filepath)
                
                self.progress.emit(i + 1, total)
            
            self.finished_indexing.emit(indexed_count)
            
        except Exception as e:
            self.error.emit(str(e))
