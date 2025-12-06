#!/usr/bin/env python3


from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


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
    """Load pattern labels."""
    labels = {}
    if not path.exists():
        return labels
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                labels[data["record_index"]] = data["pattern_type"]
    return labels


def format_for_training(record: Dict[str, Any], pattern: str) -> Dict[str, Any]:
    """Format a record for training."""
    before = record.get("before_content", "").strip()
    after = record.get("after_content", "").strip()
    file_path = record.get("file_path", "")
    file_ext = record.get("file_extension", "")
    
    # Create training example
    training_example = {
        "id": record["_index"],
        "pattern_type": pattern,
        "file_path": file_path,
        "file_extension": file_ext,
        "input": before,
        "output": after,
        "metadata": {
            "commit_sha": record.get("commit_short_sha", ""),
            "lines_added": record.get("lines_added", 0),
            "lines_deleted": record.get("lines_deleted", 0),
            "total_changes": record.get("total_changes", 0),
            "chunks": record.get("total_chunks_in_file", 0),
        }
    }
    
    return training_example


def create_splits(
    examples: List[Dict[str, Any]],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Create train/validation/test splits stratified by pattern."""
    random.seed(seed)
    
    # Group by pattern
    by_pattern: Dict[str, List[Dict]] = {}
    for ex in examples:
        pattern = ex["pattern_type"]
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(ex)
    
    train, val, test = [], [], []
    
    # Stratified split
    for pattern, pattern_examples in by_pattern.items():
        random.shuffle(pattern_examples)
        n = len(pattern_examples)
        
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        
        train.extend(pattern_examples[:n_train])
        val.extend(pattern_examples[n_train:n_train + n_val])
        test.extend(pattern_examples[n_train + n_val:])
    
    # Shuffle final splits
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    
    return train, val, test


def save_jsonl(data: List[Dict[str, Any]], path: Path) -> None:
    """Save data to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def generate_statistics(
    train: List[Dict],
    val: List[Dict],
    test: List[Dict],
    all_examples: List[Dict],
) -> Dict[str, Any]:
    """Generate comprehensive statistics."""
    def count_patterns(examples: List[Dict]) -> Dict[str, int]:
        return Counter(ex["pattern_type"] for ex in examples)
    
    stats = {
        "total_examples": len(all_examples),
        "train_size": len(train),
        "val_size": len(val),
        "test_size": len(test),
        "splits": {
            "train_ratio": len(train) / len(all_examples) if all_examples else 0,
            "val_ratio": len(val) / len(all_examples) if all_examples else 0,
            "test_ratio": len(test) / len(all_examples) if all_examples else 0,
        },
        "pattern_distribution": {
            "all": dict(count_patterns(all_examples)),
            "train": dict(count_patterns(train)),
            "val": dict(count_patterns(val)),
            "test": dict(count_patterns(test)),
        },
        "file_type_distribution": dict(
            Counter(ex["file_extension"] for ex in all_examples)
        ),
    }
    
    return stats


def main():
    """Main function."""
    dataset_path = Path("data/filtered_dataset.jsonl")
    labels_path = Path("data/pattern_labels.jsonl")
    output_dir = Path("data/training")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading dataset and labels...")
    records = load_records(dataset_path)
    labels = load_labels(labels_path)
    
    # Filter to only labeled records (exclude "skip")
    training_examples = []
    for record in records:
        idx = record["_index"]
        pattern = labels.get(idx)
        
        if pattern and pattern != "skip":
            example = format_for_training(record, pattern)
            training_examples.append(example)
    
    print(f"Prepared {len(training_examples)} training examples (excluding 'skip')")
    
    # Create splits
    print("Creating train/val/test splits...")
    train, val, test = create_splits(training_examples)
    
    # Save splits
    save_jsonl(train, output_dir / "train.jsonl")
    save_jsonl(val, output_dir / "val.jsonl")
    save_jsonl(test, output_dir / "test.jsonl")
    
    print(f" Saved splits:")
    print(f"   Train: {len(train)} examples -> {output_dir / 'train.jsonl'}")
    print(f"   Val: {len(val)} examples -> {output_dir / 'val.jsonl'}")
    print(f"   Test: {len(test)} examples -> {output_dir / 'test.jsonl'}")
    
    # Generate statistics
    stats = generate_statistics(train, val, test, training_examples)
    
    stats_path = output_dir / "dataset_statistics.json"
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f" Statistics saved to {stats_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("DATASET SUMMARY")
    print("="*60)
    print(f"Total training examples: {stats['total_examples']}")
    print(f"Train: {stats['train_size']} ({stats['splits']['train_ratio']*100:.1f}%)")
    print(f"Val: {stats['val_size']} ({stats['splits']['val_ratio']*100:.1f}%)")
    print(f"Test: {stats['test_size']} ({stats['splits']['test_ratio']*100:.1f}%)")
    print("\nPattern Distribution (All):")
    for pattern, count in sorted(stats["pattern_distribution"]["all"].items()):
        print(f"  {pattern}: {count}")


if __name__ == "__main__":
    main()

