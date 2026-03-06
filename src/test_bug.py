import sys
import os
sys.path.insert(0, r'C:\Users\User\OneDrive\Software Entwicklung\SUITEN\ExplorerPro\src')
os.chdir(r'C:\Users\User\OneDrive\Software Entwicklung\SUITEN\ExplorerPro\src')

print("Test 1: Sidebar Import...")
try:
    print("  -> OK")
except Exception as e:
    print(f"  -> FEHLER: {e}")

print("Test 2: MainWindow Import...")
try:
    print("  -> OK")
except Exception as e:
    print(f"  -> FEHLER: {e}")

print("Test 3: ExplorerProApp Import...")
try:
    print("  -> OK")
except Exception as e:
    print(f"  -> FEHLER: {e}")
