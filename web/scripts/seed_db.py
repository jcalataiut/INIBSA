"""
Carrega els fitxers master_*.csv a PostgreSQL.
Idempotent: només carrega si la DB està buida, o amb --force.

Ús:
    python scripts/seed_db.py
    python scripts/seed_db.py --force
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import init_db, is_db_empty, load_csv_to_db
from backend.config import CSV_COMMODITIES, CSV_TECHNICALS


def main():
    parser = argparse.ArgumentParser(description="Carrega CSV a PostgreSQL")
    parser.add_argument("--force", action="store_true", help="Forçar recàrrega")
    args = parser.parse_args()

    init_db()

    if not args.force and not is_db_empty():
        print("✅ DB ja conté dades. Ometent càrrega (usa --force per recarregar).")
        return

    total = 0
    for path in [CSV_COMMODITIES, CSV_TECHNICALS]:
        if not os.path.exists(path):
            print(f"⚠️  No trobat: {path}")
            continue
        print(f"📥 Carregant {path}...", end=" ", flush=True)
        n = load_csv_to_db(path)
        total += n
        print(f"{n:,} files")

    print(f"✅ Total: {total:,} files carregades a PostgreSQL")


if __name__ == "__main__":
    main()
