#!/usr/bin/env python3


from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_records(path: Path) -> List[Dict[str, Any]]:
    """Load records from JSONL."""
    records = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip():
                record = json.loads(line)
                record["_index"] = i
                records.append(record)
    return records


def load_labels(path: Path) -> Dict[int, str]:
    """Load existing labels."""
    labels = {}
    if not path.exists():
        return labels
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                labels[data["record_index"]] = data["pattern_type"]
    return labels


def detect_import_statement(record: Dict[str, Any]) -> bool:
    """Detect if this is an import statement pattern."""
    before = record.get("before_content", "")
    after = record.get("after_content", "")
    patch = record.get("patch", "")
    
    # Check if new imports were added
    import_patterns = [
        r'\+import\s+',
        r'\+from\s+\w+\s+import',
        r'\+using\s+',
    ]
    
    for pattern in import_patterns:
        if re.search(pattern, patch, re.MULTILINE):
            return True
    
    # Count imports in before vs after
    before_imports = len(re.findall(r'^import\s+', before, re.MULTILINE))
    after_imports = len(re.findall(r'^import\s+', after, re.MULTILINE))
    
    if after_imports > before_imports:
        return True
    
    return False


def detect_variable_rename(record: Dict[str, Any]) -> bool:
    """Detect variable renaming."""
    patch = record.get("patch", "")
    
    # Look for variable renames in diff
    # Pattern: -oldName +newName in same context
    rename_patterns = [
        r'-\s*\w+\s*\+\s*\w+',  # Simple rename
        r'-\w+\(\)\s*\+\w+\(\)',  # Method rename
    ]
    
    for pattern in rename_patterns:
        if re.search(pattern, patch):
            return True
    
    return False


def detect_function_rename(record: Dict[str, Any]) -> bool:
    """Detect function/method renaming."""
    patch = record.get("patch", "")
    before = record.get("before_content", "")
    after = record.get("after_content", "")
    
    # Look for function definition changes
    func_patterns = [
        r'-\s*(public|private|protected)?\s*\w+\s+\w+\(',  # Function definition removed
        r'\+\s*(public|private|protected)?\s*\w+\s+\w+\(',  # Function definition added
    ]
    
    # Check if function names changed
    before_funcs = set(re.findall(r'(?:public|private|protected)?\s+\w+\s+(\w+)\s*\(', before))
    after_funcs = set(re.findall(r'(?:public|private|protected)?\s+\w+\s+(\w+)\s*\(', after))
    
    # If function count same but names different
    if len(before_funcs) == len(after_funcs) and before_funcs != after_funcs:
        return True
    
    return False


def detect_getter_setter(record: Dict[str, Any]) -> bool:
    """Detect getter/setter additions."""
    patch = record.get("patch", "")
    after = record.get("after_content", "")
    
    # Look for get/set methods
    getter_setter_patterns = [
        r'\+.*\bget\w+\(\)',
        r'\+.*\bset\w+\(\)',
        r'\+.*@Getter',
        r'\+.*@Setter',
    ]
    
    for pattern in getter_setter_patterns:
        if re.search(pattern, patch, re.IGNORECASE):
            return True
    
    return False


def detect_function_signature_change(record: Dict[str, Any]) -> bool:
    """Detect function signature changes (parameters added/removed)."""
    patch = record.get("patch", "")
    before = record.get("before_content", "")
    after = record.get("after_content", "")
    
    # Extract function signatures
    before_sigs = re.findall(r'(\w+)\s*\(([^)]*)\)', before)
    after_sigs = re.findall(r'(\w+)\s*\(([^)]*)\)', after)
    
    # Check if same function has different parameters
    before_dict = {name: params for name, params in before_sigs}
    after_dict = {name: params for name, params in after_sigs}
    
    for func_name in before_dict:
        if func_name in after_dict:
            if before_dict[func_name] != after_dict[func_name]:
                return True
    
    return False


def detect_refactoring(record: Dict[str, Any]) -> bool:
    """Detect general refactoring patterns."""
    patch = record.get("patch", "")
    before = record.get("before_content", "")
    after = record.get("after_content", "")
    
    # Code structure changes without new functionality
    # Multiple lines changed, but not clearly import/rename/etc
    
    # Check for import consolidation (multiple imports -> wildcard)
    if re.search(r'-\s*import\s+.*\n.*-\s*import\s+', patch):
        if re.search(r'\+\s*import\s+.*\*', patch):
            return True
    
    # Significant code restructuring
    lines_changed = record.get("total_changes", 0)
    if lines_changed > 5:
        # If it's not clearly another pattern, likely refactoring
        return True
    
    return False


def detect_skip(record: Dict[str, Any]) -> bool:
    """Detect if this should be skipped."""
    file_path = record.get("file_path", "")
    file_ext = record.get("file_extension", "")
    
    # Skip documentation files
    skip_extensions = {".md", ".txt", ".rst", ".adoc"}
    skip_paths = ["README", "CHANGELOG", "LICENSE", "docs/", ".md"]
    
    if file_ext in skip_extensions:
        return True
    
    for skip_path in skip_paths:
        if skip_path in file_path:
            return True
    
    # Skip if no meaningful code changes
    before = record.get("before_content", "")
    after = record.get("after_content", "")
    
    if not before or not after:
        return True
    
    # Skip image/file reference changes only
    patch = record.get("patch", "")
    if re.search(r'\.(jpg|png|gif|svg|pdf)', patch, re.IGNORECASE):
        if len(re.findall(r'[a-zA-Z]', patch)) < 50:  # Mostly just file paths
            return True
    
    return False


def classify_record(record: Dict[str, Any]) -> str:
    """Classify a single record using heuristics."""
    # Check in order of specificity
    
    if detect_skip(record):
        return "skip"
    
    if detect_import_statement(record):
        return "import_statement"
    
    if detect_getter_setter(record):
        return "getter_setter"
    
    if detect_function_signature_change(record):
        return "function_signature_change"
    
    if detect_function_rename(record):
        return "function_rename"
    
    if detect_variable_rename(record):
        return "variable_rename"
    
    if detect_refactoring(record):
        return "refactoring"
    
    # Default to other if no pattern matches
    return "other"


def auto_label_all(
    records: List[Dict[str, Any]],
    existing_labels: Dict[int, str],
    labels_path: Path,
) -> Tuple[Dict[int, str], Dict[str, int]]:
    """Auto-label all unlabeled records."""
    new_labels = {}
    stats = Counter()
    
    for record in records:
        idx = record["_index"]
        
        # Skip if already manually labeled
        if idx in existing_labels:
            continue
        
        # Auto-classify
        pattern = classify_record(record)
        new_labels[idx] = pattern
        stats[pattern] += 1
    
    # Save all labels
    all_labels = {**existing_labels, **new_labels}
    
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8") as f:
        for idx in sorted(all_labels.keys()):
            f.write(json.dumps({
                "record_index": idx,
                "pattern_type": all_labels[idx],
            }, ensure_ascii=False) + "\n")
    
    return new_labels, stats


def main():
    """Main function."""
    dataset_path = Path("data/filtered_dataset.jsonl")
    labels_path = Path("data/pattern_labels.jsonl")
    
    print("Loading dataset...")
    records = load_records(dataset_path)
    existing_labels = load_labels(labels_path)
    
    print(f"Total records: {len(records)}")
    print(f"Already labeled: {len(existing_labels)}")
    print(f"To auto-label: {len(records) - len(existing_labels)}")
    print()
    
    print("Auto-classifying unlabeled records...")
    new_labels, stats = auto_label_all(records, existing_labels, labels_path)
    
    print(f"\n Auto-labeled {len(new_labels)} records")
    print("\nPattern distribution:")
    for pattern, count in stats.most_common():
        print(f"  {pattern}: {count}")
    
    print(f"\n Labels saved to {labels_path}")
    print(f"  Total labeled: {len(existing_labels) + len(new_labels)}/{len(records)}")


if __name__ == "__main__":
    main()

