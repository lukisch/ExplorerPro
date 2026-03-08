# 📦 ExplorerPro Suite – Final Documentation

## 1. Überblick

**Kurzbeschreibung:**  
ExplorerPro ist ein intelligenter Datei-Explorer mit Datenbankindizierung, integrierter Vorschau, Code-Editor, Datenschutz-Ampel und Tool-Integration (Apps, Prompts, Sync).

| Feld | Wert |
|------|------|
| **Version** | 1.0.0 |
| **Stand** | 2026-01-09 |
| **Status** | Fertiggestellt (100%) |
| **Sprache** | Python 3.10+ |
| **Framework** | PyQt6 + QScintilla |
| **Codebase** | ~7.500 Zeilen / 25+ Dateien |

---

## 2. Herkunft & Fusion

### 2.1 Ursprungstools

| Tool | Version | Zeilen | Reifegrad | Kernfunktion |
|------|---------|--------|-----------|--------------|
| ProFiler | V14 | 7.575 | 85% | Datei-Index, SQLite+FTS5, Hash |
| PythonBox | V8 | 3.381 | 85% | Code-Editor, Syntax-Highlighting |
| AmpelTool | V5 | ~500 | 80% | Clipboard-Überwachung, Datenschutz |
| SoftwareCenter | - | ~400 | 80% | App-Launcher, Kategorien |
| ProfiPrompt | - | ~500 | 75% | Prompt-Bibliothek, Variablen |
| ProSync | V3.1 | 1.764 | 85% | Ordner-Sync, Konflikt-Lösung |

**Gesamt:** 6 Tools, ~13.000+ Zeilen Ursprungscode

### 2.2 Fusionsziel

> **"Ein intelligenter Explorer mit Datenbankindizierung und integrierten Entwicklertools"**

Die Suite vereint Datei-Navigation, Volltextsuche, Code-Bearbeitung, Datenschutz-Monitoring und Tool-Integration in einer Anwendung.

### 2.3 Synergien

| Synergie | Beschreibung |
|----------|--------------|
| 🔍 **Index + Search** | FTS5-Volltextsuche über alle Dateien |
| 📝 **Browser + Editor** | Direktes Bearbeiten ohne Tool-Wechsel |
| 🔒 **Privacy + Status** | Ampel in Statusbar zeigt Datenschutz-Status |
| 🚀 **Apps + Quick Launch** | Favoriten-Apps in Sidebar |
| 📋 **Prompts + Clipboard** | Schneller Zugriff auf Prompt-Bibliothek |
| 🔄 **Sync + Backup** | Integrierte Ordner-Synchronisation |

---

## 3. Features

### 3.1 Hauptfunktionen

| Bereich | Icon | Features |
|---------|------|----------|
| **File Browser** | 📁 | Navigation, Kontextmenü, Multi-Select |
| **File Index** | 🔍 | SQLite+FTS5, Hash-Index, OCR-Text |
| **Preview** | 👁️ | PDF, Bilder, Code, Metadaten |
| **Quick Editor** | 📝 | Multi-Tab, Syntax-Highlighting |
| **Privacy Monitor** | 🔒 | Clipboard-Überwachung, Ampel |
| **Apps Panel** | 🚀 | Kategorien, Favoriten, Quick-Launch |
| **Prompts Panel** | 📋 | Variablen, Tags, Quick-Copy |
| **Sync Panel** | 🔄 | Bidirektional, Konflikt-Lösung |

### 3.2 Feature-Matrix

| Feature | Einzeltools | ExplorerPro |
|---------|:-----------:|:-----------:|
| Datei-Navigation | Standard Explorer | ✅ Erweitert |
| Volltextsuche | ProFiler | ✅ Integriert |
| Code-Bearbeitung | PythonBox | ✅ Quick Editor |
| Datenschutz | AmpelTool | ✅ Status Bar |
| App-Launcher | SoftwareCenter | ✅ Sidebar |
| Prompt-Bibliothek | ProfiPrompt | ✅ Sidebar |
| Ordner-Sync | ProSync | ✅ Sidebar |

### 3.3 Sidebar-Tabs (6 Panels)

1. **📁 Tree Panel** - Verzeichnisbaum, Laufwerke
2. **⭐ Favorites** - Schnellzugriff auf Ordner
3. **🔍 Search Panel** - Erweiterte Suche mit Filtern
4. **🚀 Apps Panel** - App-Launcher (SoftwareCenter)
5. **📋 Prompts Panel** - Prompt-Bibliothek (ProfiPrompt)
6. **🔄 Sync Panel** - Ordner-Synchronisation (ProSync)

### 3.4 Erweiterte Suche

- Volltext-Suche (FTS5)
- Dateiname-Filter
- Dateigrößen-Filter
- Datums-Filter
- Erweiterungen-Filter
- Hash-Suche (Duplikate)
- Regex-Unterstützung

---

## 4. Architektur

### 4.1 Layer-Modell

```
┌─────────────────────────────────────────────────────────────────┐
│                         GUI Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ MainWindow  │  │   Sidebar   │  │     PreviewPanel        │  │
│  │             │  │  6 Tabs     │  │  PDF/Image/Code/Meta    │  │
│  │             │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ FileBrowser │  │  StatusBar  │  │      Dialogs            │  │
│  │ QTableView  │  │ + Ampel     │  │  Search, Settings       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                       Core Layer                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │FileIndex │  │ MetaStore│  │ Privacy  │  │  EventBus     │   │
│  │(ProFiler)│  │ (Tags,   │  │ Monitor  │  │               │   │
│  │SQLite+   │  │  Notes)  │  │(AmpelTool│  │  Signals      │   │
│  │FTS5      │  │          │  │          │  │               │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                      Module Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │  Editor  │  │  Apps    │  │ Prompts  │  │    Sync       │   │
│  │(PythonBox│  │(Software │  │(ProfiPro │  │  (ProSync)    │   │
│  │QuickEdit)│  │ Center)  │  │   mpt)   │  │               │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                       Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │fileindex.db  │  │  apps.json   │  │   File System        │  │
│  │  (Index)     │  │prompts.json  │  │   (watched dirs)     │  │
│  │              │  │  sync.json   │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Module

| Modul | Pfad | Zeilen | Beschreibung |
|-------|------|--------|--------------|
| **main.py** | `src/main.py` | 58 | Entry Point |
| **app.py** | `src/app.py` | 239 | Haupt-App-Klasse |
| **FileIndex** | `core/file_index.py` | 580 | SQLite + FTS5 |
| **MainWindow** | `gui/main_window.py` | 530 | Hauptfenster + Menüs |
| **Sidebar** | `gui/sidebar.py` | 301 | 6-Tab Sidebar |
| **StatusBar** | `gui/status_bar.py` | 167 | Statusleiste + Ampel |
| **SearchPanel** | `gui/sidebar/search_panel.py` | 387 | Erweiterte Suche |
| **AdvancedSearch** | `gui/sidebar/advanced_search_dialog.py` | 489 | Such-Dialog |
| **FileBrowser** | `gui/browser/file_browser.py` | 395 | Dateiliste |
| **PreviewPanel** | `gui/preview/preview_panel.py` | 367 | Vorschau |
| **PrivacyMonitor** | `modules/privacy/privacy_monitor.py` | 437 | Clipboard-Überwachung |
| **BlacklistManager** | `modules/privacy/blacklist_manager.py` | 244 | Blacklist-Verwaltung |
| **QuickEditor** | `modules/editor/quick_editor.py` | 545 | Code-Editor |
| **SyntaxHighlighter** | `modules/editor/syntax_highlighter.py` | 294 | Syntax-Highlighting |
| **DuplicateFinder** | `modules/indexer/duplicate_finder.py` | 676 | Duplikate-Finder |
| **AppsPanel** | `modules/launcher/apps_panel.py` | 382 | App-Launcher |
| **PromptsPanel** | `modules/prompts/prompts_panel.py` | 500 | Prompt-Bibliothek |
| **SyncManager** | `modules/sync/sync_manager.py` | 709 | Ordner-Sync |

### 4.3 Datenfluss

```
User Navigation → FileBrowser → FileIndex Query → Results Display
       ↓                              ↓
   Preview ← File Selection ← EventBus Signals
       ↓
   QuickEditor (bei Code-Dateien)
```

---

## 5. Projektstruktur

```
ExplorerPro/
├── src/
│   ├── main.py                      # Entry Point
│   ├── app.py                       # Haupt-App-Klasse
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── file_index.py            # SQLite Index + FTS5
│   │   ├── settings_manager.py      # Einstellungen (JSON)
│   │   └── event_bus.py             # Signal-Bus
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # Hauptfenster + Menüs
│   │   ├── sidebar.py               # 6-Tab Sidebar
│   │   ├── status_bar.py            # Statusleiste mit Ampel
│   │   │
│   │   ├── sidebar/
│   │   │   ├── search_panel.py      # Erweiterte Suche
│   │   │   └── advanced_search_dialog.py
│   │   │
│   │   ├── browser/
│   │   │   └── file_browser.py      # Dateiliste
│   │   │
│   │   └── preview/
│   │       └── preview_panel.py     # Vorschau-Panel
│   │
│   └── modules/
│       ├── privacy/                  # AmpelTool-Integration
│       │   ├── privacy_monitor.py
│       │   └── blacklist_manager.py
│       │
│       ├── editor/                   # PythonBox-Integration
│       │   ├── quick_editor.py
│       │   └── syntax_highlighter.py
│       │
│       ├── indexer/
│       │   └── duplicate_finder.py
│       │
│       ├── launcher/                 # SoftwareCenter
│       │   └── apps_panel.py
│       │
│       ├── prompts/                  # ProfiPrompt
│       │   └── prompts_panel.py
│       │
│       └── sync/                     # ProSync
│           └── sync_manager.py
│
├── requirements.txt
├── README.md
├── START_ExplorerPro.bat
└── resources/
```

---

## 6. Datenformate & Datenbanken

### 6.1 Formate

| Format | Verwendung |
|--------|------------|
| **SQLite + FTS5** | Datei-Index (fileindex.db) |
| **JSON** | Apps, Prompts, Sync-Config, Settings |
| **QSettings** | Window-State, Preferences |

### 6.2 Datei-Index Schema

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    name TEXT,
    extension TEXT,
    size INTEGER,
    modified REAL,
    hash TEXT,
    content TEXT  -- FTS5 indexed
);

CREATE VIRTUAL TABLE files_fts USING fts5(
    name, content, content='files'
);
```

### 6.3 Speicherort

```
~/.explorerpro/
├── fileindex.db        # Datei-Index
├── apps.json           # App-Definitionen
├── prompts.json        # Prompt-Bibliothek
├── sync.json           # Sync-Verbindungen
├── blacklist.txt       # Datenschutz-Blacklist
└── settings.json       # Einstellungen
```

---

## 7. Workflows

### 7.1 Hauptworkflow

```
Ordner öffnen → Dateien indizieren → Suchen/Filtern → Vorschau/Bearbeiten
       ↓
Sidebar nutzen (Apps, Prompts, Sync)
       ↓
Statusbar zeigt: Anzahl, Größe, Datenschutz-Status
```

### 7.2 Such-Workflow

```
Suchbegriff eingeben → FTS5 Query → Ergebnisse in Liste
       ↓
Erweiterte Filter (Größe, Datum, Extension)
       ↓
Duplikate finden (Hash-Vergleich)
```

### 7.3 Datenschutz-Workflow

```
Clipboard-Änderung → Pattern-Check (Blacklist) → Ampel-Update
       ↓
🟢 Grün: Keine sensiblen Daten
🟡 Gelb: Möglicherweise sensibel
🔴 Rot: Sensible Daten erkannt
```

---

## 8. Installation & Setup

### 8.1 Voraussetzungen

| Anforderung | Version |
|-------------|---------|
| Python | 3.10+ |
| OS | Windows 10/11 (primär) |
| RAM | 4 GB+ |

### 8.2 Installation

```bash
# Ordner öffnen
cd "C:\Users\User\OneDrive\.SOFTWARE\SUITEN\ExplorerPro"

# Abhängigkeiten installieren
pip install -r requirements.txt

# Starten
python src/main.py
# oder
START_ExplorerPro.bat
```

### 8.3 Abhängigkeiten

```
PyQt6>=6.4.0
QScintilla>=2.13.0
PyMuPDF>=1.23.0
Pillow>=10.0.0
watchdog>=3.0.0
pygments>=2.15.0
```

---

## 9. Build & Deployment

### 9.1 PyInstaller

```bash
pyinstaller --onefile --windowed --icon=resources/icons/explorer.ico src/main.py
```

---

## 10. Tests

```bash
# Import-Test
python test_imports.py

# Vollständiger Test
python -m pytest tests/ -v
```

---

## 11. Changelog

### 11.1 Phasen-Übersicht

| Phase | Beschreibung | Zeilen | Status |
|-------|--------------|--------|--------|
| Phase 1 | Explorer-Grundgerüst | ~2.000 | ✅ |
| Phase 2 | Index & Suche | ~1.500 | ✅ |
| Phase 3 | Editor & Preview | ~1.200 | ✅ |
| Phase 4 | Datenschutz (AmpelTool) | ~700 | ✅ |
| Phase 5 | Apps, Prompts, Sync | ~1.600 | ✅ |
| **Gesamt** | | **~7.500** | **100%** |

---

## 12. Roadmap

### ✅ Erledigt

- [x] Explorer-Grundgerüst mit 3-Panel-Layout
- [x] SQLite + FTS5 Datei-Index
- [x] Erweiterte Suche mit Filtern
- [x] PDF/Bild/Code Vorschau
- [x] Quick Editor (PythonBox)
- [x] Datenschutz-Monitor (AmpelTool)
- [x] Apps Panel (SoftwareCenter)
- [x] Prompts Panel (ProfiPrompt)
- [x] Sync Panel (ProSync)
- [x] Duplikate-Finder

### 🔮 Zukunft

- [ ] Cloud-Integration
- [ ] Tabs für mehrere Ordner
- [ ] Erweiterte OCR-Integration

---

## 13. Lizenz

**MIT License**

---

## 14. Tastenkürzel

| Kürzel | Funktion |
|--------|----------|
| `Alt+Left` | Zurück |
| `Alt+Right` | Vorwärts |
| `Alt+Up` | Übergeordneter Ordner |
| `Alt+Home` | Home-Verzeichnis |
| `Ctrl+B` | Sidebar ein/aus |
| `Ctrl+P` | Vorschau ein/aus |
| `F5` | Aktualisieren |
| `Ctrl+1` | Apps-Panel öffnen |
| `Ctrl+2` | Prompts-Panel öffnen |
| `Ctrl+3` | Sync-Panel öffnen |
| `F4` | Editor öffnen |
| `Ctrl+N` | Neues Fenster |
| `Ctrl+O` | Ordner öffnen |
| `Ctrl+Shift+N` | Neuer Ordner |

---

## 15. UI-Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ExplOrer Pro v1.0                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  [◀][▶][↑] [📁 C:\Users\...           ] [🔍 Suchen...  ] [⚙️]              │
├─────────┬──────────────────────────────┬────────────────────────────────────┤
│ SIDEBAR │        FILE BROWSER          │         PREVIEW PANEL              │
│         │                              │                                    │
│ [📁][⭐]│  ┌────────────────────────┐  │  ┌────────────────────────────┐   │
│ [🔍][🚀]│  │ Name    │ Size │ Date │  │  │      PDF/Image/Code        │   │
│ [📋][🔄]│  ├─────────┼──────┼──────┤  │  │         Preview            │   │
│         │  │ doc.pdf │ 2MB  │ 01/03│  │  │                            │   │
│ ┌─────┐ │  │ code.py │ 12KB │ 01/02│  │  └────────────────────────────┘   │
│ │📁Tree│ │  │ img.png │ 500KB│ 12/28│  │                                    │
│ │ ├─C:│ │  └────────────────────────┘  │  ┌────────────────────────────┐   │
│ │ ├─D:│ │                              │  │        METADATA            │   │
│ │ └─..│ │                              │  │  Hash, Tags, Notes         │   │
│ └─────┘ │                              │  └────────────────────────────┘   │
│         │                              │                                    │
│ ┌─────┐ │                              │  ┌────────────────────────────┐   │
│ │⭐Favs│ │                              │  │      QUICK EDIT            │   │
│ │🔍Srch│ │                              │  │     (PythonBox)            │   │
│ │🚀Apps│ │                              │  └────────────────────────────┘   │
│ │📋Prmt│ │                              │                                    │
│ │🔄Sync│ │                              │                                    │
│ └─────┘ │                              │                                    │
├─────────┴──────────────────────────────┴────────────────────────────────────┤
│  📁 1.234 Dateien │ 💾 2.3 GB │ 🟢 Datenschutz OK │ Sync: ✓                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Generiert: 2026-01-09 | ExplorerPro Suite | ~7.500 Zeilen / 25+ Dateien*
