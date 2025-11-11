import json
import sys
from collections import defaultdict, Counter

def stream_json_array(filepath, max_items=3000):
    """Stream JSON array items one by one to avoid loading everything into memory"""
    with open(filepath, 'r') as f:
        f.readline()  # skip opening bracket
        count = 0
        for line in f:
            line = line.strip()
            if line.startswith('{'):
                json_str = line.rstrip(',')
                try:
                    yield json.loads(json_str)
                    count += 1
                    if count >= max_items:
                        break
                except json.JSONDecodeError:
                    continue

def analyze_patterns():
    filepath = '/Users/erinma/.cursor/worktrees/IBMCodeCompletion/IAOE3/data/combined_dataset.json'
    
    print("Streaming dataset...", file=sys.stderr)
    
    # Counters for analysis
    ext_counter = Counter()
    change_counter = Counter()
    commit_analysis = defaultdict(list)
    ext_transitions = defaultdict(Counter)
    change_transitions = defaultdict(Counter)
    
    samples = []
    prev_item = None
    
    for i, item in enumerate(stream_json_array(filepath, max_items=2000)):
        samples.append(item)
        
        # Extract key fields
        ext = item.get('file_extension', 'unknown')
        change = item.get('change_type', 'unknown')
        commit_sha = item.get('commit_sha', 'unknown')
        
        ext_counter[ext] += 1
        change_counter[change] += 1
        commit_analysis[commit_sha].append(item)
        
        # Track transitions
        if prev_item:
            prev_ext = prev_item.get('file_extension', 'unknown')
            prev_change = prev_item.get('change_type', 'unknown')
            ext_transitions[prev_ext][ext] += 1
            change_transitions[prev_change][change] += 1
        
        prev_item = item
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1} items...", file=sys.stderr)
    
    print(f"\nAnalyzed {len(samples)} data points\n", file=sys.stderr)
    
    # Print results
    print("="*80)
    print("FILE EXTENSION DISTRIBUTION")
    print("="*80)
    for ext, count in ext_counter.most_common(15):
        pct = (count / len(samples)) * 100
        print(f"  .{ext}: {count} ({pct:.1f}%)")
    
    print("\n" + "="*80)
    print("CHANGE TYPE DISTRIBUTION")
    print("="*80)
    for change, count in change_counter.most_common(10):
        pct = (count / len(samples)) * 100
        print(f"  {change}: {count} ({pct:.1f}%)")
    
    print("\n" + "="*80)
    print("FILE EXTENSION TRANSITION PATTERNS")
    print("(What file type comes AFTER current type)")
    print("="*80)
    for ext in [e for e, _ in ext_counter.most_common(5)]:
        if ext in ext_transitions:
            print(f"\n  After .{ext}:")
            for next_ext, count in ext_transitions[ext].most_common(5):
                print(f"    -> .{next_ext}: {count} times")
    
    print("\n" + "="*80)
    print("CHANGE TYPE SEQUENCE PATTERNS")
    print("(What change type comes AFTER current type)")
    print("="*80)
    for change in [c for c, _ in change_counter.most_common(5)]:
        if change in change_transitions:
            print(f"\n  After '{change}':")
            for next_change, count in change_transitions[change].most_common(5):
                print(f"    -> '{next_change}': {count} times")
    
    print("\n" + "="*80)
    print("COMMIT PATTERNS")
    print("="*80)
    multi_change_commits = sum(1 for changes in commit_analysis.values() if len(changes) > 1)
    print(f"  Unique commits: {len(commit_analysis)}")
    print(f"  Commits with multiple file changes: {multi_change_commits}")
    print(f"  Average changes per commit: {len(samples) / len(commit_analysis):.2f}")
    
    # Analyze within-commit patterns
    within_commit_ext_trans = defaultdict(Counter)
    within_commit_change_trans = defaultdict(Counter)
    
    for changes in commit_analysis.values():
        if len(changes) > 1:
            for i in range(len(changes) - 1):
                curr_ext = changes[i].get('file_extension', 'unknown')
                next_ext = changes[i+1].get('file_extension', 'unknown')
                curr_change = changes[i].get('change_type', 'unknown')
                next_change = changes[i+1].get('change_type', 'unknown')
                
                within_commit_ext_trans[curr_ext][next_ext] += 1
                within_commit_change_trans[curr_change][next_change] += 1
    
    print("\n  Within-commit file extension transitions:")
    for ext in [e for e, _ in ext_counter.most_common(3)]:
        if ext in within_commit_ext_trans:
            print(f"\n    After .{ext} (same commit):")
            for next_ext, count in within_commit_ext_trans[ext].most_common(3):
                print(f"      -> .{next_ext}: {count} times")
    
    print("\n" + "="*80)
    print("SIZE PATTERNS")
    print("="*80)
    lines_added = sorted([s.get('lines_added', 0) for s in samples])
    lines_deleted = sorted([s.get('lines_deleted', 0) for s in samples])
    
    def percentile(data, p):
        idx = int(len(data) * (p / 100.0))
        return data[idx] if idx < len(data) else 0
    
    print("\n  Lines Added Distribution:")
    print(f"    Median: {percentile(lines_added, 50)}")
    print(f"    75th percentile: {percentile(lines_added, 75)}")
    print(f"    95th percentile: {percentile(lines_added, 95)}")
    print(f"    Max: {max(lines_added)}")
    
    print("\n  Lines Deleted Distribution:")
    print(f"    Median: {percentile(lines_deleted, 50)}")
    print(f"    75th percentile: {percentile(lines_deleted, 75)}")
    print(f"    95th percentile: {percentile(lines_deleted, 95)}")
    print(f"    Max: {max(lines_deleted)}")
    
    print("\n" + "="*80)
    print("KEY INSIGHTS FOR NEXT ACTION PREDICTION")
    print("="*80)
    
    # Find strong predictive patterns
    print("\n1. HIGH-CONFIDENCE EXTENSION TRANSITIONS:")
    for ext in [e for e, _ in ext_counter.most_common(3)]:
        if ext in ext_transitions:
            total = sum(ext_transitions[ext].values())
            most_common = ext_transitions[ext].most_common(1)[0]
            confidence = (most_common[1] / total) * 100
            if confidence > 25:
                print(f"   Pattern: After .{ext} file")
                print(f"     Most likely next: .{most_common[0]} ({confidence:.1f}% confidence)")
    
    print("\n2. HIGH-CONFIDENCE CHANGE TYPE SEQUENCES:")
    for change in [c for c, _ in change_counter.most_common(3)]:
        if change in change_transitions:
            total = sum(change_transitions[change].values())
            most_common = change_transitions[change].most_common(1)[0]
            confidence = (most_common[1] / total) * 100
            if confidence > 25:
                print(f"   Pattern: After '{change}' change")
                print(f"     Most likely next: '{most_common[0]}' ({confidence:.1f}% confidence)")
    
    print("\n3. MULTI-FILE COMMIT PATTERNS:")
    if multi_change_commits > 0:
        print(f"   {(multi_change_commits/len(commit_analysis))*100:.1f}% of commits have multiple file changes")
        print(f"   When multiple files changed in same commit:")
        for ext in [e for e, _ in ext_counter.most_common(2)]:
            if ext in within_commit_ext_trans:
                total = sum(within_commit_ext_trans[ext].values())
                most_common = within_commit_ext_trans[ext].most_common(1)[0]
                if most_common[1] > 0:
                    confidence = (most_common[1] / total) * 100
                    print(f"     After .{ext}: likely .{most_common[0]} ({confidence:.1f}%)")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    analyze_patterns()

