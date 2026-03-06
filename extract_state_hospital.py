#!/usr/bin/env python3
"""
Extract inmates awaiting transfer to Arkansas State Hospital.
Run from the pulaskijailjsons directory, or pass the directory as an argument.

Usage:
    python3 extract_state_hospital.py
    python3 extract_state_hospital.py /path/to/pulaskijailjsons
"""

import json
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

HOLD_KEYWORD = "Arkansas State Hospital"
TODAY = date.today()
OUTPUT_FILE = "state_hospital_waitlist.csv"


def parse_ash_date(hold_text):
    text = hold_text.replace("<br />", "\n").replace("<br>", "\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if HOLD_KEYWORD in line:
            date_match = re.search(r"Arrest Date\s+(\d{2}/\d{2}/\d{4})", line)
            if not date_match and i + 1 < len(lines):
                date_match = re.search(r"Arrest Date\s+(\d{2}/\d{2}/\d{4})", lines[i + 1])
            if date_match:
                return date_match.group(1)
            break
    return None


def days_waiting(ash_date_str):
    if not ash_date_str:
        return "unknown"
    try:
        hold_date = datetime.strptime(ash_date_str, "%m/%d/%Y").date()
        return (TODAY - hold_date).days
    except ValueError:
        return "unknown"


def process_files(directory):
    results = []
    seen = set()
    all_files = []
    for f in sorted(directory.iterdir()):
        if f.suffix in (".json", ".txt") and f not in seen:
            seen.add(f)
            all_files.append(f)

    for filepath in sorted(all_files):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠  Skipping {filepath.name}: {e}")
            continue

        for person in data.get("records", []):
            hold = person.get("hold_reasons", "")
            if HOLD_KEYWORD not in hold:
                continue

            ash_date_str = parse_ash_date(hold)
            wait = days_waiting(ash_date_str)
            clean_hold = hold.replace("<br />", " | ").replace("<br>", " | ").strip(" | ")

            results.append({
                "name": person.get("name", ""),
                "dob": person.get("dob", ""),
                "sex": person.get("sex", ""),
                "race": person.get("race", ""),
                "arrest_date": person.get("arrest_date", ""),
                "state_hospital_hold_date": ash_date_str or "",
                "days_waiting": wait,
                "hold_reasons": clean_hold,
                "held_for_agency": person.get("held_for_agency", ""),
                "source_file": filepath.name,
            })

    return results


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)

    print(f"Scanning {directory.resolve()} ...")
    results = process_files(directory)

    if not results:
        print("No inmates found awaiting transfer to Arkansas State Hospital.")
        return

    results.sort(key=lambda r: r["days_waiting"] if isinstance(r["days_waiting"], int) else -1, reverse=True)

    out_path = directory / OUTPUT_FILE
    fieldnames = ["name", "dob", "sex", "race", "arrest_date",
                  "state_hospital_hold_date", "days_waiting", "hold_reasons",
                  "held_for_agency", "source_file"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    known_waits = [r["days_waiting"] for r in results if isinstance(r["days_waiting"], int)]
    avg = round(sum(known_waits) / len(known_waits)) if known_waits else "N/A"

    print(f"\n✅  Found {len(results)} people awaiting state hospital transfer.")
    print(f"   Average wait: {avg} days")
    print(f"   Saved to: {out_path}")
    print(f"\nTop 10 longest waits:")
    for r in results[:10]:
        print(f"  {r['days_waiting']:>4} days  {r['name']}")


if __name__ == "__main__":
    main()
