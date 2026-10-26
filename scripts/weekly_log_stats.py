"""Compute summary stats for the weekly keepalive log.

Reads the "ofertas" sheet with the same scripts.helpers.get_sheet_data
helper used by scripts/update_offers.py, and prints (or appends to
GITHUB_OUTPUT) the total row count and the most recent fecha_publicacion.

Usage:
    python -m scripts.weekly_log_stats
"""

import os
import re
from datetime import datetime

from scripts.helpers import get_sheet_data


def parse_fecha_publicacion(value):
    value = (value or "").strip()
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if not match:
        return None

    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def compute_stats(rows):
    if not rows or len(rows) < 2:
        return 0, None

    headers = [str(h).strip().lower() for h in rows[0]]
    try:
        idx = headers.index("fecha_publicacion")
    except ValueError:
        idx = None

    data_rows = rows[1:]
    total = len(data_rows)

    latest = None
    if idx is not None:
        for row in data_rows:
            value = row[idx] if idx < len(row) else ""
            parsed = parse_fecha_publicacion(value)
            if parsed and (latest is None or parsed > latest):
                latest = parsed

    return total, latest


def main():
    rows = get_sheet_data("ofertas")
    total, latest = compute_stats(rows)
    latest_str = latest.strftime("%d/%m/%Y") if latest else "sin datos"

    lines = [f"total={total}", f"latest_fecha_publicacion={latest_str}"]

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
