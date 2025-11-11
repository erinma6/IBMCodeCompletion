#!/usr/bin/env python3
import json
import sys
import io
from collections import defaultdict, Counter

def parse_json_stream(filepath, max_items=2000):
    """Parse JSON array from file, handling multiline objects"""
    items = []
    current_obj = io.StringIO()
    in_object = False
    brace_count = 0
    
    with open(filepath, 'r') as f:
        for line in f:
            # Skip the opening bracket
            if line.strip() == '[':
                continue
            # Skip the closing bracket
            if line.strip() == ']':
                break
            
            # Track braces to know when object is complete
            if '{' in line:
                in_object = True
                brace_count += line.count('{')
            
            if in_object:
                current_obj.write(line)
                brace_count -= line.count('}')
                
                # When braces balanced, we have a complete object
                if brace_count == 0 and in_object:
                    obj_str = current_obj.getvalue().strip()
                    if obj_str.endswith(','):
                        obj_str = obj_str[:-1]  # Remove trailing comma
                    
                    try:
                        obj = json.loads(obj_str)
                        items.append(obj)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}", file=sys.stderr)
                    
                    current_obj = io.StringIO()
                    in_object = False
                    
                    if len(items) >= max_items:
                        break
    
    return items

def analyze():
    filepath = '/Users/erinma/.cursor/worktrees/IBMCodeCompletion/IAOE3/data/combined_dataset.json'
    
    print(f"Parsing dataset from {filepath}...", file=sys.stderr)
    samples = parse_json_stream(filepath, max_items=2000)
    print(f"Successfully parsed {len(samples)} items\n", file=sys.stderr)
    
    if not samples:
        print("ERROR: No samples loaded!", file=sys.stderr)
        return
    
    # Initialize counters
    ext_counter = Counter()
    change_counter = Counter()
    commit_data = defaultdict(list)
    ext_transitions = defaultdict(Counter)
    change_transitions = defaultdict(Counter)
    
    # First pass: collect all data
    for item in samples:
        ext = item.get('file_extension', 'unknown')
        change = item.get('change_type', 'unknown')
        commit_sha = item.get('commit_sha', 'unknown')
        
        ext_counter[ext] += 1
        change_counter[change] += 1
        commit_data[commit_sha].append(item)
    
    # Second pass: analyze transitions
    for i in range(len(samples) - 1):
        curr = samples[i]
        next_item = samples[i + 1]
        
        curr_ext = curr.get('file_extension', 'unknown')
        next_ext = next_item.get('file_extension', 'unknown')
        curr_change = curr.get('change_type', 'unknown')
        next_change = next_item.get('change_type', 'unknown')
        
        ext_transitions[curr_ext][next_ext] += 1
        change_transitions[curr_change][next_change] += 1
    
    # Print analysis
    print("="*80)
    print("FILE EXTENSION DISTRIBUTION")
    print("="*80)
    total = len(samples)
    for ext, count in ext_counter.most_common(15):
        pct = (count / total) * 100
        print(f"  .{ext}: {count:4d} ({pct:5.1f}%)")
    
    print("\n" + "="*80)
    print("CHANGE TYPE DISTRIBUTION")
    print("="*80)
    for change, count in change_counter.most_common(10):
        pct = (count / total) * 100
        print(f"  {change:15s}: {count:4d} ({pct:5.1f}%)")
    
    print("\n" + "="*80)
    print("FILE EXTENSION TRANSITIONS")
    print("(Next file type most likely to follow)")
    print("="*80)
    
    top_exts = [ext for ext, _ in ext_counter.most_common(5)]
    for ext in top_exts:
        if ext in ext_transitions:
            total_after = sum(ext_transitions[ext].values())
            print(f"\n  After .{ext}:")
            for next_ext, count in ext_transitions[ext].most_common(5):
                conf = (count / total_after) * 100
                print(f"    -> .{next_ext:10s}: {count:3d} times ({conf:5.1f}%)")
    
    print("\n" + "="*80)
    print("CHANGE TYPE SEQUENCES")
    print("(Next change type most likely to follow)")
    print("="*80)
    
    top_changes = [chg for chg, _ in change_counter.most_common(4)]
    for change in top_changes:
        if change in change_transitions:
            total_after = sum(change_transitions[change].values())
            print(f"\n  After '{change}':")
            for next_change, count in change_transitions[change].most_common(4):
                conf = (count / total_after) * 100
                print(f"    -> '{next_change:10s}': {count:3d} times ({conf:5.1f}%)")
    
    print("\n" + "="*80)
    print("COMMIT PATTERNS")
    print("="*80)
    multi_file_commits = sum(1 for items in commit_data.values() if len(items) > 1)
    print(f"  Total unique commits: {len(commit_data)}")
    print(f"  Commits with multiple changes: {multi_file_commits}")
    if len(commit_data) > 0:
        avg = len(samples) / len(commit_data)
        print(f"  Average changes per commit: {avg:.2f}")
    
    # Analyze within-commit patterns
    within_ext_trans = defaultdict(Counter)
    within_change_trans = defaultdict(Counter)
    
    for commit_items in commit_data.values():
        if len(commit_items) > 1:
            for i in range(len(commit_items) - 1):
                curr = commit_items[i]
                next_item = commit_items[i + 1]
                
                curr_ext = curr.get('file_extension', 'unknown')
                next_ext = next_item.get('file_extension', 'unknown')
                curr_change = curr.get('change_type', 'unknown')
                next_change = next_item.get('change_type', 'unknown')
                
                within_ext_trans[curr_ext][next_ext] += 1
                within_change_trans[curr_change][next_change] += 1
    
    print("\n  WITHIN SAME COMMIT - File extension sequences:")
    for ext in [e for e, _ in ext_counter.most_common(3)]:
        if ext in within_ext_trans:
            print(f"\n    After .{ext}:")
            for next_ext, count in within_ext_trans[ext].most_common(3):
                print(f"      -> .{next_ext}: {count} times")
    
    # Analyze sizes
    print("\n" + "="*80)
    print("CODE CHANGE SIZE PATTERNS")
    print("="*80)
    
    lines_added_vals = sorted([s.get('lines_added', 0) for s in samples])
    lines_deleted_vals = sorted([s.get('lines_deleted', 0) for s in samples])
    
    def get_percentile(data, p):
        if not data:
            return 0
        idx = int(len(data) * (p / 100.0))
        return data[min(idx, len(data) - 1)]
    
    print("\n  Lines Added:")
    print(f"    Min: {min(lines_added_vals)}, Max: {max(lines_added_vals)}")
    print(f"    P50 (median): {get_percentile(lines_added_vals, 50)}")
    print(f"    P75: {get_percentile(lines_added_vals, 75)}")
    print(f"    P95: {get_percentile(lines_added_vals, 95)}")
    
    print("\n  Lines Deleted:")
    print(f"    Min: {min(lines_deleted_vals)}, Max: {max(lines_deleted_vals)}")
    print(f"    P50 (median): {get_percentile(lines_deleted_vals, 50)}")
    print(f"    P75: {get_percentile(lines_deleted_vals, 75)}")
    print(f"    P95: {get_percentile(lines_deleted_vals, 95)}")
    
    # Summary insights
    print("\n" + "="*80)
    print("KEY INSIGHTS FOR NEXT ACTION PREDICTION")
    print("="*80)
    
    print("\n1. STRONGEST PREDICTIVE PATTERNS (>40% confidence):")
    
    found_patterns = False
    for ext in [e for e, _ in ext_counter.most_common(3)]:
        if ext in ext_transitions:
            total_after = sum(ext_transitions[ext].values())
            if total_after > 0:
                most_common = ext_transitions[ext].most_common(1)[0]
                conf = (most_common[1] / total_after) * 100
                if conf > 40:
                    print(f"   • After a .{ext} file: next is likely .{most_common[0]} ({conf:.0f}%)")
                    found_patterns = True
    
    for change in [c for c, _ in change_counter.most_common(3)]:
        if change in change_transitions:
            total_after = sum(change_transitions[change].values())
            if total_after > 0:
                most_common = change_transitions[change].most_common(1)[0]
                conf = (most_common[1] / total_after) * 100
                if conf > 40:
                    print(f"   • After a '{change}': next is likely '{most_common[0]}' ({conf:.0f}%)")
                    found_patterns = True
    
    if not found_patterns:
        print("   No patterns with >40% confidence found in this sample")
        print("\n2. MODERATE PATTERNS (>25% confidence):")
        for ext in [e for e, _ in ext_counter.most_common(3)]:
            if ext in ext_transitions:
                total_after = sum(ext_transitions[ext].values())
                if total_after > 0:
                    most_common = ext_transitions[ext].most_common(1)[0]
                    conf = (most_common[1] / total_after) * 100
                    if 25 < conf <= 40:
                        print(f"   • After .{ext}: likely .{most_common[0]} ({conf:.0f}%)")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    analyze()

