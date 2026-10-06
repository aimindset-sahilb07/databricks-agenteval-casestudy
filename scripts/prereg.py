"""Pre-register a hypothesis by committing its SHA-256 hash, not its text.

The hypothesis lives in a private (gitignored) journal entry. This script
extracts the entry's ``Hypothesis:`` field, normalizes it, hashes it and
appends a row to the public ledger. Commit and push the ledger before running
the experiment; the pushed commit time is the evidence of ordering.

Usage:
    python scripts/prereg.py register FILE --id EXP-20261006-01 --kind experiment
    python scripts/prereg.py verify   FILE --id EXP-20261006-01
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "prereg" / "ledger.csv"
FIELDS = ["id", "utc_time", "kind", "sha256"]

HEADING = re.compile(r"^#{1,6}\s")
FIELD = re.compile(r"^\**([A-Z][\w /()-]*):\**\s*(.*)$")


def extract_hypothesis(text: str, entry_id: str) -> str:
    """Return the Hypothesis field inside the section whose heading contains entry_id."""
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if HEADING.match(line) and entry_id in line),
        None,
    )
    if start is None:
        raise SystemExit(f"No heading containing {entry_id!r} found.")

    level = len(lines[start]) - len(lines[start].lstrip("#"))
    collected: list[str] | None = None
    for line in lines[start + 1 :]:
        if HEADING.match(line) and len(line) - len(line.lstrip("#")) <= level:
            break  # next entry at same or higher level
        match = FIELD.match(line)
        if collected is None:
            if match and match.group(1).strip().lower() == "hypothesis":
                collected = [match.group(2)]
        elif match or HEADING.match(line):
            break
        else:
            collected.append(line)

    if collected is None:
        raise SystemExit(f"No 'Hypothesis:' field in entry {entry_id!r}.")
    hypothesis = normalize("\n".join(collected))
    if not hypothesis.strip():
        raise SystemExit(f"Hypothesis for {entry_id!r} is empty; write it before registering.")
    return hypothesis


def normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip() + "\n"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_ledger() -> list[dict[str, str]]:
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def register(path: Path, entry_id: str, kind: str) -> None:
    digest = sha256(extract_hypothesis(path.read_text(encoding="utf-8"), entry_id))
    if any(row["id"] == entry_id for row in read_ledger()):
        raise SystemExit(f"{entry_id} is already registered; use a new id for a revised hypothesis.")

    new_file = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        writer.writerow({
            "id": entry_id,
            "utc_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kind": kind,
            "sha256": digest,
        })
    print(f"{entry_id} {digest}")
    print("Next: git add prereg/ledger.csv && git commit && git push, then run the experiment.")


def verify(path: Path, entry_id: str) -> None:
    digest = sha256(extract_hypothesis(path.read_text(encoding="utf-8"), entry_id))
    row = next((r for r in read_ledger() if r["id"] == entry_id), None)
    if row is None:
        raise SystemExit(f"{entry_id} is not in the ledger.")
    if row["sha256"] != digest:
        print(f"MISMATCH {entry_id}: ledger {row['sha256']} vs file {digest}")
        sys.exit(1)
    print(f"OK {entry_id} registered {row['utc_time']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("register", "verify"):
        p = sub.add_parser(name)
        p.add_argument("file", type=Path)
        p.add_argument("--id", required=True, dest="entry_id")
        if name == "register":
            p.add_argument("--kind", default="experiment", choices=["experiment", "decision"])
    args = parser.parse_args()

    if args.command == "register":
        register(args.file, args.entry_id, args.kind)
    else:
        verify(args.file, args.entry_id)


if __name__ == "__main__":
    main()
