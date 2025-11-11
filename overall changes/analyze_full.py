#!/usr/bin/env python3
"""
Load and analyze the complete dataset to find patterns for next action prediction.
"""

import json
import sys
from collections import defaultdict, Counter

def main():
    filepath = '/Users/erinma/.cursor/worktrees/IBMCodeCompletion/IAOE3/data/combined_dataset.json'
    
    print(f"Loading dataset from {filepath}...", file=sys.stderr)
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error loading JSON: {e}", file=sys.stderr)
        return
    
    if not isinstance(data, list):
        print(f"Error: Expected list, got {type(data)}", file=sys.stderr)
        return
    
    total_items = len(data)
    print(f"Successfully loaded {total_items} items\n", file=sys.stderr)
    
    # Initialize counters
    ext_counter = Counter()
    change_counter = Counter()
    commit_map = defaultdict(list)
    ext_transitions = defaultdict(Counter)
    change_transitions = defaultdict(Counter)
    
    # Collect data
    for item in data:
        ext = item.get('file_extension', 'unknown')
        change = item.get('change_type', 'unknown')
        commit_sha = item.get('commit_sha', 'unknown')
        
        ext_counter[ext] += 1
        change_counter[change] += 1
        commit_map[commit_sha].append(item)
    
    # Analyze transitions
    for i in range(len(data) - 1):
        curr = data[i]
        next_item = data[i + 1]
        
        curr_ext = curr.get('file_extension', 'unknown')
        next_ext = next_item.get('file_extension', 'unknown')
        curr_change = curr.get('change_type', 'unknown')
        next_change = next_item.get('change_type', 'unknown')
        
        ext_transitions[curr_ext][next_ext] += 1
        change_transitions[curr_change][next_change] += 1
    
    # ============================================================================
    # PRINT ANALYSIS
    # ============================================================================
    
    print("="*80)
    print("PATTERN ANALYSIS FOR NEXT ACTION PREDICTION")
    print("="*80)
    
    print(f"\nDataset Overview:")
    print(f"  Total items: {total_items}")
    print(f"  Unique file extensions: {len(ext_counter)}")
    print(f"  Unique change types: {len(change_counter)}")
    print(f"  Unique commits: {len(commit_map)}")
    
    # File Extension Distribution
    print("\n" + "="*80)
    print("1. FILE EXTENSION DISTRIBUTION")
    print("="*80)
    
    for ext, count in ext_counter.most_common(20):
        pct = (count / total_items) * 100
        print(f"  .{ext:12s}: {count:6d} ({pct:5.1f}%)")
    
    # Change Type Distribution
    print("\n" + "="*80)
    print("2. CHANGE TYPE DISTRIBUTION")
    print("="*80)
    
    for change, count in change_counter.most_common(10):
        pct = (count / total_items) * 100
        print(f"  {change:20s}: {count:6d} ({pct:5.1f}%)")
    
    # Extension Transitions
    print("\n" + "="*80)
    print("3. NEXT FILE TYPE PREDICTION PATTERNS")
    print("(What file extension comes after each type)")
    print("="*80)
    
    for ext in [e for e, _ in ext_counter.most_common(10)]:
        if ext in ext_transitions:
            total_trans = sum(ext_transitions[ext].values())
            print(f"\n  After .{ext} files ({total_trans} transitions):")
            for next_ext, count in ext_transitions[ext].most_common(5):
                confidence = (count / total_trans) * 100
                print(f"    → .{next_ext:12s}: {count:5d}x ({confidence:5.1f}%)")
    
    # Change Type Sequences
    print("\n" + "="*80)
    print("4. NEXT CHANGE TYPE PREDICTION PATTERNS")
    print("(What change type comes after each type)")
    print("="*80)
    
    for change in [c for c, _ in change_counter.most_common(5)]:
        if change in change_transitions:
            total_trans = sum(change_transitions[change].values())
            print(f"\n  After '{change}' changes ({total_trans} transitions):")
            for next_change, count in change_transitions[change].most_common(5):
                confidence = (count / total_trans) * 100
                print(f"    → '{next_change:15s}': {count:5d}x ({confidence:5.1f}%)")
    
    # Commit Patterns
    print("\n" + "="*80)
    print("5. COMMIT-BASED PATTERNS")
    print("="*80)
    
    multi_file = sum(1 for items in commit_map.values() if len(items) > 1)
    print(f"\n  Commits analyzed: {len(commit_map)}")
    print(f"  Commits with multiple changes: {multi_file} ({(multi_file/len(commit_map)*100):.1f}%)")
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
    
    print("\n  Within-commit file type sequences (top extensions):")
    for ext in [e for e, _ in ext_counter.most_common(5)]:
        if ext in within_ext_trans:
            total_trans = sum(within_ext_trans[ext].values())
            if total_trans > 0:
                print(f"\n    After .{ext} (same commit):")
                for next_ext, count in within_ext_trans[ext].most_common(3):
                    conf = (count / total_trans) * 100
                    print(f"      → .{next_ext}: {count}x ({conf:.1f}%)")
    
    # Size patterns
    print("\n" + "="*80)
    print("6. CODE CHANGE SIZE DISTRIBUTION")
    print("="*80)
    
    lines_added = sorted([item.get('lines_added', 0) for item in data])
    lines_deleted = sorted([item.get('lines_deleted', 0) for item in data])
    total_changes = sorted([item.get('total_changes', 0) for item in data])
    
    def percentile(arr, p):
        idx = int(len(arr) * (p / 100.0))
        return arr[min(idx, len(arr) - 1)]
    
    print("\n  Lines Added:")
    print(f"    Mean: {sum(lines_added) / len(lines_added):.1f}, Min: {min(lines_added)}, Max: {max(lines_added)}")
    print(f"    P50: {percentile(lines_added, 50)}, P75: {percentile(lines_added, 75)}, P95: {percentile(lines_added, 95)}")
    
    print("\n  Lines Deleted:")
    print(f"    Mean: {sum(lines_deleted) / len(lines_deleted):.1f}, Min: {min(lines_deleted)}, Max: {max(lines_deleted)}")
    print(f"    P50: {percentile(lines_deleted, 50)}, P75: {percentile(lines_deleted, 75)}, P95: {percentile(lines_deleted, 95)}")
    
    print("\n  Total Changes (Added + Deleted):")
    print(f"    Mean: {sum(total_changes) / len(total_changes):.1f}, Min: {min(total_changes)}, Max: {max(total_changes)}")
    print(f"    P50: {percentile(total_changes, 50)}, P75: {percentile(total_changes, 75)}, P95: {percentile(total_changes, 95)}")
    
    # Key Insights
    print("\n" + "="*80)
    print("7. KEY INSIGHTS FOR NEXT ACTION PREDICTION")
    print("="*80)
    
    print("\n  HIGH-CONFIDENCE EXTENSION PATTERNS (>35%):")
    found = False
    for ext in [e for e, _ in ext_counter.most_common(8)]:
        if ext in ext_transitions:
            total_trans = sum(ext_transitions[ext].values())
            if total_trans > 0:
                most_common = ext_transitions[ext].most_common(1)[0]
                confidence = (most_common[1] / total_trans) * 100
                if confidence > 35:
                    print(f"    • After .{ext:12s} → likely .{most_common[0]:12s} ({confidence:.0f}%)")
                    found = True
    if not found:
        print("    (No extensions with >35% confidence found)")
    
    print("\n  HIGH-CONFIDENCE CHANGE-TYPE PATTERNS (>35%):")
    found = False
    for change in [c for c, _ in change_counter.most_common(5)]:
        if change in change_transitions:
            total_trans = sum(change_transitions[change].values())
            if total_trans > 0:
                most_common = change_transitions[change].most_common(1)[0]
                confidence = (most_common[1] / total_trans) * 100
                if confidence > 35:
                    print(f"    • After '{change:15s}' → likely '{most_common[0]:15s}' ({confidence:.0f}%)")
                    found = True
    if not found:
        print("    (No change types with >35% confidence found)")
    
    print("\n  DIRECTORY/FILE CHANGE PATTERNS:")
    # Analyze by directory
    dir_changes = defaultdict(Counter)
    for item in data:
        path = item.get('file_path', '')
        if '/' in path:
            directory = '/'.join(path.split('/')[:-1])
            change_type = item.get('change_type', 'unknown')
            dir_changes[directory][change_type] += 1
    
    print(f"    Most frequently changed directories:")
    top_dirs = sorted(dir_changes.items(), key=lambda x: sum(x[1].values()), reverse=True)[:5]
    for directory, changes in top_dirs:
        total_in_dir = sum(changes.values())
        most_common_change = changes.most_common(1)[0]
        print(f"      • {directory}: {total_in_dir} changes ({most_common_change[0]}: {most_common_change[1]}x)")
    
    print("\n" + "="*80)
    print("8. SAMPLE DATA POINTS")
    print("="*80)
    
    for idx in range(min(8, len(data))):
        item = data[idx]
        print(f"\n  Sample {idx + 1}:")
        print(f"    Commit: {item.get('commit_message', 'N/A')[:50]}")
        print(f"    File: .../{'/'.join(item.get('file_path', 'N/A').split('/')[-2:])}")
        print(f"    Type: .{item.get('file_extension', '?'):12s} | Change: {item.get('change_type', '?')}")
        print(f"    Changes: +{item.get('lines_added', 0):4d} -{item.get('lines_deleted', 0):4d} (total: {item.get('total_changes', 0)})")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()

