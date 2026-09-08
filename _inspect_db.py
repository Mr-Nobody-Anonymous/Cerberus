"""Inspect memory DB schemas (dev utility)."""
import sqlite3
import glob

for db in sorted(set(glob.glob("memory/**/*.db", recursive=True) + glob.glob("*.db"))):
    print(f"=== {db} ===")
    try:
        conn = sqlite3.connect(db)
        tables = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table'"
        ).fetchall()
        for name, sql in tables:
            print(f"  [{name}]")
            if sql:
                print(f"    {sql}")
        conn.close()
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
