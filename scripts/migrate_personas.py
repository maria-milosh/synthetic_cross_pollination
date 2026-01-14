#!/usr/bin/env python3
"""Migrate personas from existing pilot outputs to persistent storage."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.persona_storage import migrate_from_outputs, load_storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    print("Migrating personas from existing pilots to storage...")
    added = migrate_from_outputs()

    storage = load_storage()
    print(f"\nMigration complete:")
    print(f"  - Added {added} new personas")
    print(f"  - Total personas in storage: {len(storage)}")


if __name__ == "__main__":
    main()
