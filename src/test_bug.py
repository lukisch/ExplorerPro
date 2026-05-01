from __future__ import annotations

import sys
import traceback
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def check_import(label: str, import_path: str, name: str) -> bool:
    print(f"Test: {label}...")
    try:
        module = __import__(import_path, fromlist=[name])
        getattr(module, name)
    except Exception as exc:
        print(f"  -> FEHLER: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return False
    print("  -> OK")
    return True


def main() -> int:
    checks = [
        check_import("Sidebar Import", "gui.sidebar", "Sidebar"),
        check_import("MainWindow Import", "gui.main_window", "MainWindow"),
        check_import("ExplorerProApp Import", "app", "ExplorerProApp"),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
