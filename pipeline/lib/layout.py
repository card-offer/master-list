"""Stable JSON writers. Each record in a collection is one line, sorted by id."""
import json
import os


def record_line(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_collection(path, header, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    items = sorted(items, key=lambda row: row["id"])
    header = dict(header)
    header["count"] = len(items)
    keys = sorted(key for key in header if key != "items")
    lines = ["{"]
    for key in keys:
        lines.append(f"  {json.dumps(key)}: {json.dumps(header[key], ensure_ascii=False)},")
    lines.append('  "items": [')
    for index, item in enumerate(items):
        suffix = "," if index < len(items) - 1 else ""
        lines.append("    " + record_line(item) + suffix)
    lines.append("  ]")
    lines.append("}")
    text = "\n".join(lines) + "\n"
    if "\u2014" in text:
        raise SystemExit(f"em dash in {path}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if "\u2014" in text:
        raise SystemExit(f"em dash in {path}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
