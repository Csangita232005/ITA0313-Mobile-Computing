from pathlib import Path
import csv
import json
from datetime import datetime, timezone

OUTPUT_DIR = Path("outputs")

def ensure_output_dir(*parts):
    path = OUTPUT_DIR.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path

def write_text(relative_path, content):
    path = OUTPUT_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path

def write_csv(relative_path, rows, fieldnames=None):
    path = OUTPUT_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)
    return path

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
