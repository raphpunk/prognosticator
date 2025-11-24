#!/usr/bin/env python3
"""Quick script to optimize and secure the live database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forecasting.optimize import create_db_indexes, optimize_db


def main():
    db_path = "data/live.db"
    print(f"Optimizing {db_path}...")
    create_db_indexes(db_path)
    optimize_db(db_path)
    print("✓ Database optimized and secured (indexes created, VACUUM+ANALYZE run)")


if __name__ == "__main__":
    main()
