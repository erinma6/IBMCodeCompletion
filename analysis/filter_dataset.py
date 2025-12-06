#!/usr/bin/env python3
"""
Filter the combined dataset to the highest-signal examples for the
next-action prediction task.

Example:
    python analysis/filter_dataset.py \
        --input-file data/combined_dataset.json \
        --output-file data/filtered_dataset.jsonl \
        --summary-file data/filtered_dataset_summary.json \
        --max-total-changes 20 \
        --max-files-per-commit 1 \
        --min-chunks-per-file 2
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter combined dataset to keep only high-signal examples."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("data/combined_dataset.json"),
        help="Path to the raw combined_dataset.json file.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/filtered_dataset.jsonl"),
        help="Destination JSONL file for the filtered dataset.",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        default=Path("data/filtered_dataset_summary.json"),
        help="Where to store summary statistics for the filtering run.",
    )
    parser.add_argument(
        "--max-total-changes",
        type=int,
        default=20,
        help="Maximum number of line changes (added + deleted) allowed per record.",
    )
    parser.add_argument(
        "--max-files-per-commit",
        type=int,
        default=1,
        help="Maximum number of files touched in the commit. Use 1 to enforce single-file commits.",
    )
    parser.add_argument(
        "--min-chunks-per-file",
        type=int,
        default=2,
        help="Minimum number of diff chunks inside a file to indicate multiple edit regions.",
    )
    return parser.parse_args()


def load_records(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def compute_total_changes(record: Dict[str, Any]) -> int | None:
    total_changes = record.get("total_changes")
    if total_changes is not None:
        return total_changes
    added = record.get("lines_added")
    deleted = record.get("lines_deleted")
    if added is None or deleted is None:
        return None
    return added + deleted


def should_keep(
    record: Dict[str, Any],
    args: argparse.Namespace,
    drop_counter: Counter,
) -> bool:
    total_changes = compute_total_changes(record)
    if total_changes is None:
        drop_counter["missing_line_stats"] += 1
        return False
    if total_changes > args.max_total_changes:
        drop_counter["too_many_lines_changed"] += 1
        return False
    files_in_commit = record.get("total_files_in_commit")
    if files_in_commit is None:
        drop_counter["missing_file_count"] += 1
        return False
    if files_in_commit > args.max_files_per_commit:
        drop_counter["multi_file_commit"] += 1
        return False
    chunks = record.get("total_chunks_in_file")
    if chunks is None:
        drop_counter["missing_chunk_count"] += 1
        return False
    if chunks < args.min_chunks_per_file:
        drop_counter["single_chunk_file"] += 1
        return False
    return True


def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")


def main() -> None:
    args = parse_args()
    records = load_records(args.input_file)
    drop_reasons: Counter = Counter()
    kept: List[Dict[str, Any]] = []

    for record in records:
        if should_keep(record, args, drop_reasons):
            kept.append(record)

    write_jsonl(kept, args.output_file)
    summary = {
        "input_records": len(records),
        "kept_records": len(kept),
        "retention_rate": (len(kept) / len(records)) if records else 0.0,
        "parameters": {
            "max_total_changes": args.max_total_changes,
            "max_files_per_commit": args.max_files_per_commit,
            "min_chunks_per_file": args.min_chunks_per_file,
        },
        "drop_reasons": drop_reasons,
    }
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

