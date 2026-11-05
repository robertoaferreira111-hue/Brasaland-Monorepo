"""Load dev inventory events into telemetry_events.

Run from services/api so the API package and the locked driver are available:

    uv run python ../../data/dev/seed_inventory_events.py
    uv run python ../../data/dev/seed_inventory_events.py late

The second command inserts one purchase dated inside the earliest seeded
week. It does not rewrite the main batch. Requires DATABASE_URL for a
database you have confirmed is not production.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "services" / "api"))
sys.path.insert(0, str(_REPO / "data"))
sys.path.insert(0, str(_REPO / "data" / "dev"))

from inventory_seed import counts_by_type_and_week, insert_rows, late_events, main_events
from pipelines.db import connect


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "main"
    if command == "main":
        events = main_events()
    elif command == "late":
        events = late_events()
    else:
        print("usage: seed_inventory_events.py [main|late]", file=sys.stderr)
        return 2
    with connect() as connection:
        inserted = insert_rows(connection, events)
    print(f"command={command} received={len(events)} inserted={inserted}")
    for event_type, weeks in sorted(counts_by_type_and_week(events).items()):
        for week, count in sorted(weeks.items()):
            print(f"{event_type} {week} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
