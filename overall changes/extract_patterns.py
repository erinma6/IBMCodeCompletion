#!/usr/bin/env python3
"""
Extract and analyze patterns from the combined_dataset.json for next action prediction.
This script reads chunks of the JSON file efficiently without loading everything into memory.
"""

import json
import sys
from collections import defaultdict, Counter
from typing import Generator, Dict, Any

def read_json_objects(filepath: str, max_objects: int = 2000) -> Generator[Dict[str, Any], None, None]:
    """
    Generator that yields individual JSON objects from a JSON array file.
    Handles large files by reading and parsing objects incrementally.
    """
    with open(filepath, 'r') as f:
        # Skip opening bracket
        f.readline()
        
        count = 0
        current_line = ""
        brace_depth = 0
        
        for line in f:
            current_line += line
            brace_depth += line.count('{') - line.count('}')
            
            # When we close all braces, we have a complete JSON object
            if brace_depth == 0 and '{' in current_line and '}' in current_line:
                json_str = current_line.strip()
                if json_str.endswith(','):
                    json_str = json_str[:-1]
                if json_str == ']':
                    break
                    
                try:
                    obj = json.loads(json_str)
                    yield obj
                    count += 1
                    if count >= max_objects:
                        break
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}", file=sys.stderr)
                    
                current_line = ""

def main():
    filepath = '/Users/erinma/.cursor/worktrees/IBMCodeCompletion/IAOE3/data/combined_dataset.json'
    
    print("Extracting patterns from dataset...", file=sys.stderr)
    print(file=sys.stderr)
    
    # Counters for analysis
    ext_counter = Counter()
    change_counter = Counter()
    commit_map = defaultdict(list)
    ext_transitions = defaultdict(Counter)
    change_transitions = defaultdict(Counter)
    
    samples = []
    prev_item = None
    
    # First pass: collect data
    for i, item in enumerate(read_json_objects(filepath, max_objects=2000)):
        samples.append(item)
        
        # Extract metadata
        ext = item.get('file_extension', 'unknown')
        change = item.get('change_type', 'unknown')
        commit_sha = item.get('commit_sha', 'unknown')
        
        # Update counters
        ext_counter[ext] += 1
        change_counter[change] += 1
        commit_map[commit_sha].append(item)
        
        # Track sequential patterns
        if prev_item:
            prev_ext = prev_item.get('file_extension', 'unknown')
            prev_change = prev_item.get('change_type', 'unknown')
            ext_transitions[prev_ext][ext] += 1
            change_transitions[prev_change][change] += 1
        
        prev_item = item
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1} items...", file=sys.stderr)
    
    total_items = len(samples)
    print(f"\nSuccessfully analyzed {total_items} data points\n", file=sys.stderr)
    
    if total_items == 0:
        print("No items loaded! Check file format.", file=sys.stderr)
        return
    
    # ============================================================================
    # ANALYSIS OUTPUT
    # ============================================================================
    
    print("="*80)
    print("PATTERN ANALYSIS FOR NEXT ACTION PREDICTION")
    print("="*80)
    
    print(f"\nDataset Overview:")
    print(f"  Total items analyzed: {total_items}")
    print(f"  Unique file extensions: {len(ext_counter)}")
    print(f"  Unique change types: {len(change_counter)}")
    print(f"  Unique commits: {len(commit_map)}")
    
    # FILE EXTENSION PATTERNS
    print("\n" + "="*80)
    print("1. FILE EXTENSION DISTRIBUTION")
    print("="*80)
    
    for ext, count in ext_counter.most_common(15):
        pct = (count / total_items) * 100
        print(f"  .{ext:15s}: {count:5d} ({pct:5.1f}%)")
    
    # CHANGE TYPE PATTERNS
    print("\n" + "="*80)
    print("2. CHANGE TYPE DISTRIBUTION")
    print("="*80)
    
    for change, count in change_counter.most_common(10):
        pct = (count / total_items) * 100
        print(f"  {change:20s}: {count:5d} ({pct:5.1f}%)")
    
    # EXTENSION TRANSITIONS - KEY PREDICTOR
    print("\n" + "="*80)
    print("3. NEXT FILE TYPE PREDICTION")
    print("(What file extension comes after current file type)")
    print("="*80)
    
    for ext in [e for e, _ in ext_counter.most_common(5)]:
        if ext in ext_transitions:
            total_trans = sum(ext_transitions[ext].values())
            print(f"\n  After .{ext} files ({total_trans} transitions):")
            for next_ext, count in ext_transitions[ext].most_common(5):
                confidence = (count / total_trans) * 100
                bar_len = int(confidence / 2)
                bar = "█" * bar_len + "░" * (25 - bar_len)
                print(f"    → .{next_ext:10s}: {count:3d}x [{bar}] {confidence:5.1f}%")
    
    # CHANGE TYPE SEQUENCES - KEY PREDICTOR
    print("\n" + "="*80)
    print("4. NEXT CHANGE TYPE PREDICTION")
    print("(What change type comes after current change type)")
    print("="*80)
    
    for change in [c for c, _ in change_counter.most_common(4)]:
        if change in change_transitions:
            total_trans = sum(change_transitions[change].values())
            print(f"\n  After '{change}' changes ({total_trans} transitions):")
            for next_change, count in change_transitions[change].most_common(4):
                confidence = (count / total_trans) * 100
                bar_len = int(confidence / 2)
                bar = "█" * bar_len + "░" * (25 - bar_len)
                print(f"    → '{next_change:15s}': {count:3d}x [{bar}] {confidence:5.1f}%")
    
    # COMMIT-BASED PATTERNS
    print("\n" + "="*80)
    print("5. COMMIT-BASED PATTERNS")
    print("(Files changed together within the same commit)")
    print("="*80)
    
    multi_change = sum(1 for items in commit_map.values() if len(items) > 1)
    print(f"\n  Commits analyzed: {len(commit_map)}")
    print(f"  Commits with multiple file changes: {multi_change} ({(multi_change/len(commit_map)*100):.1f}%)")
    if len(commit_map) > 0:
        print(f"  Average files per commit: {total_items / len(commit_map):.2f}")
    
    # Within-commit patterns
    within_ext_trans = defaultdict(Counter)
    within_change_trans = defaultdict(Counter)
    
    for commit_items in commit_map.values():
        if len(commit_items) > 1:
            for i in range(len(commit_items) - 1):
                curr_ext = commit_items[i].get('file_extension', 'unknown')
                next_ext = commit_items[i + 1].get('file_extension', 'unknown')
                curr_change = commit_items[i].get('change_type', 'unknown')
                next_change = commit_items[i + 1].get('change_type', 'unknown')
                
                within_ext_trans[curr_ext][next_ext] += 1
                within_change_trans[curr_change][next_change] += 1
    
    print("\n  Within-commit file type sequences:")
    for ext in [e for e, _ in ext_counter.most_common(3)]:
        if ext in within_ext_trans:
            total_trans = sum(within_ext_trans[ext].values())
            if total_trans > 0:
                print(f"    After .{ext} (in same commit):")
                for next_ext, count in within_ext_trans[ext].most_common(3):
                    conf = (count / total_trans) * 100
                    print(f"      → .{next_ext}: {count}x ({conf:.0f}%)")
    
    # SIZE PATTERNS
    print("\n" + "="*80)
    print("6. CODE CHANGE SIZE PATTERNS")
    print("="*80)
    
    lines_added = sorted([s.get('lines_added', 0) for s in samples])
    lines_deleted = sorted([s.get('lines_deleted', 0) for s in samples])
    total_changes = sorted([s.get('total_changes', 0) for s in samples])
    
    def percentile(data, p):
        idx = int(len(data) * (p / 100.0))
        return data[min(idx, len(data) - 1)]
    
    print("\n  Lines Added:")
    print(f"    Min: {min(lines_added)}, Max: {max(lines_added)}")
    print(f"    Median (P50): {percentile(lines_added, 50)}")
    print(f"    P75: {percentile(lines_added, 75)}, P95: {percentile(lines_added, 95)}")
    
    print("\n  Lines Deleted:")
    print(f"    Min: {min(lines_deleted)}, Max: {max(lines_deleted)}")
    print(f"    Median (P50): {percentile(lines_deleted, 50)}")
    print(f"    P75: {percentile(lines_deleted, 75)}, P95: {percentile(lines_deleted, 95)}")
    
    print("\n  Total Changes (Added + Deleted):")
    print(f"    Min: {min(total_changes)}, Max: {max(total_changes)}")
    print(f"    Median (P50): {percentile(total_changes, 50)}")
    print(f"    P75: {percentile(total_changes, 75)}, P95: {percentile(total_changes, 95)}")
    
    # PREDICTIVE RULES
    print("\n" + "="*80)
    print("7. HIGH-CONFIDENCE PREDICTIVE RULES (>30% confidence)")
    print("="*80)
    
    print("\n  EXTENSION-BASED RULES:")
    rules_found = 0
    for ext in [e for e, _ in ext_counter.most_common(5)]:
        if ext in ext_transitions:
            total_trans = sum(ext_transitions[ext].values())
            if total_trans > 0:
                most_common = ext_transitions[ext].most_common(1)[0]
                confidence = (most_common[1] / total_trans) * 100
                if confidence > 30:
                    print(f"    • After .{ext:10s} → likely .{most_common[0]:10s} ({confidence:.0f}% confidence)")
                    rules_found += 1
    
    if rules_found == 0:
        print("    (No strong patterns found in top extensions)")
    
    print("\n  CHANGE-TYPE-BASED RULES:")
    rules_found = 0
    for change in [c for c, _ in change_counter.most_common(4)]:
        if change in change_transitions:
            total_trans = sum(change_transitions[change].values())
            if total_trans > 0:
                most_common = change_transitions[change].most_common(1)[0]
                confidence = (most_common[1] / total_trans) * 100
                if confidence > 30:
                    print(f"    • After '{change:15s}' → likely '{most_common[0]:15s}' ({confidence:.0f}% confidence)")
                    rules_found += 1
    
    if rules_found == 0:
        print("    (No strong patterns found in change types)")
    
    # SAMPLE DATA
    print("\n" + "="*80)
    print("8. SAMPLE DATA POINTS")
    print("="*80)
    
    for idx in range(min(5, len(samples))):
        sample = samples[idx]
        print(f"\n  Sample {idx + 1}:")
        print(f"    Commit: {sample.get('commit_message', 'N/A')[:60]}")
        print(f"    File: {sample.get('file_path', 'N/A')[:60]}")
        print(f"    Type: .{sample.get('file_extension', '?')} | Change: {sample.get('change_type', '?')}")
        print(f"    Changes: +{sample.get('lines_added', 0)} -{sample.get('lines_deleted', 0)}")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()

