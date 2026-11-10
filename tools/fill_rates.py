#!/usr/bin/env python3
"""Print fill rates for the published tree. Used as a pull request comment."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.build_indexes import load_tree


def present(value):
    if value is None:
        return False
    if value == "":
        return False
    if value == [] or value == {}:
        return False
    return True


def rate(rows, getter):
    if not rows:
        return 0, 0, 0.0
    filled = sum(1 for row in rows if present(getter(row)))
    return filled, len(rows), (100.0 * filled / len(rows))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    cards, offers, issuers, merchants = load_tree(root)
    fields = [
        ("offer end_date", offers, lambda row: row.get("end_date")),
        ("offer start_date", offers, lambda row: row.get("start_date")),
        ("offer min_spend.amount", offers, lambda row: (row.get("min_spend") or {}).get("amount")),
        ("offer cap.amount", offers, lambda row: (row.get("cap") or {}).get("amount")),
        ("offer terms_url", offers, lambda row: row.get("terms_url")),
        ("offer terms_hash", offers, lambda row: row.get("terms_hash")),
        ("offer merchant_id", offers, lambda row: row.get("merchant_id")),
        ("offer evidence_text", offers, lambda row: (row.get("eligibility") or {}).get("evidence_text")),
        ("offer checked_at", offers, lambda row: row.get("checked_at")),
        ("offer benefit.value", offers, lambda row: (row.get("benefit") or {}).get("value")),
        ("offer benefit.unit", offers, lambda row: (row.get("benefit") or {}).get("unit")),
        ("offer valid_days", offers, lambda row: row.get("valid_days")),
        ("card networks", cards, lambda row: row.get("networks")),
        ("card annual_fee.amount", cards, lambda row: (row.get("annual_fee") or {}).get("amount") if row.get("annual_fee") else None),
        ("card min_income.amount", cards, lambda row: (row.get("min_income") or {}).get("amount") if row.get("min_income") else None),
        ("card checked_at", cards, lambda row: row.get("checked_at")),
        ("merchant official_domain", merchants, lambda row: row.get("official_domain")),
    ]
    print("<!-- fill-rates -->")
    print("## Fill rates")
    print()
    print("| Field | Filled | Total | Rate |")
    print("| --- | ---: | ---: | ---: |")
    for label, rows, getter in fields:
        filled, total, pct = rate(rows, getter)
        print(f"| {label} | {filled} | {total} | {pct:.1f}% |")
    print()
    print(f"Offers {len(offers)}, cards {len(cards)}, merchants {len(merchants)}, issuers {len(issuers)}.")


if __name__ == "__main__":
    main()
