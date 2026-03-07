# ExplorerPro Suite

Erweiterter Datei-Explorer mit Datenschutz-Monitor, Vorschau-Panel, Sync-Manager und integriertem Code-Editor.

## Features

- **Datei-Browser** mit Multi-Tab-Support und Breadcrumb-Navigation
- **Vorschau-Panel** fuer PDF, Bilder, Code und Text
- **Datenschutz-Monitor** - Erkennung und Verwaltung sensibler Dateien
- **Erweiterte Suche** mit Filtern (Typ, Groesse, Datum)
- **Duplikat-Finder** ueber Datei-Hashes
- **Quick-Editor** mit Syntax-Highlighting (QScintilla + Pygments)
- **Prompt-Launcher** fuer KI-Prompts
- **Sync-Manager** fuer Ordner-Synchronisation
- **App-Launcher** fuer Schnellzugriff
- **Statusleiste** mit Datei-Statistiken und Datenschutz-Status

## Architektur

```
ExplorerPro Suite v1.0
├── src/
│   ├── core/           Event-Bus, Datei-Index, Settings
│   ├── gui/
│   │   ├── browser/    Datei-Browser mit Tabellen-Ansicht
│   │   ├── preview/    Vorschau-Panel (PDF, Bilder, Code)
│   │   └── sidebar/    Seitenleiste mit Suche und Navigation
│   └── modules/
│       ├── editor/     Quick-Editor mit Syntax-Highlighting
│       ├── indexer/    Duplikat-Finder
│       ├── launcher/   App-Launcher
│       ├── privacy/    Datenschutz-Monitor und Blacklist
│       ├── prompts/    Prompt-Verwaltung
│       └── sync/       Sync-Manager
```

Vollstaendige Architektur: [ARCHITEKTUR.md](ARCHITEKTUR.md)

## Installation

### Voraussetzungen

- Python >= 3.8
- PyQt6

### Setup

```bash
pip install -r requirements.txt
```

## Verwendung

```bash
python src/main.py
```

Oder ueber die Batch-Datei:

```bash
START_ExplorerPro.bat
```

## Abhaengigkeiten

| Paket | Zweck |
|-------|-------|
| PyQt6 | GUI-Framework |
| PyQt6-QScintilla | Code-Editor |
| PyMuPDF | PDF-Vorschau |
| watchdog | Datei-Ueberwachung |
| Pygments | Syntax-Highlighting |
| pandas | Tabellen-Import |

## Lizenz

AGPL v3 - Siehe [LICENSE](LICENSE)

Dieses Projekt verwendet PyQt6 (GPL) und PyMuPDF (AGPL).

---

**Version:** 1.0.0
**Autor:** Lukas Geiger
**Letzte Aktualisierung:** Maerz 2026

---

English version: [README.md](README.md)
