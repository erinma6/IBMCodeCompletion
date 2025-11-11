import json
import random
from collections import defaultdict, Counter
from typing import List, Dict, Any
import math

def load_dataset_sample(filepath: str, sample_size: int = 5000):
    """Load a random sample from the large JSON file"""
    samples = []
    
    with open(filepath, 'r') as f:
        # Read entire file and parse as JSON array
        try:
            data = json.load(f)
            if isinstance(data, list):
                # Sample randomly from the dataset
                if len(data) > sample_size:
                    samples = random.sample(data, sample_size)
                else:
                    samples = data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
    
    return samples

def analyze_file_extension_patterns(samples: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns in file extensions"""
    extensions = [s.get('file_extension', 'unknown') for s in samples]
    change_types = [s.get('change_type', 'unknown') for s in samples]
    
    ext_counter = Counter(extensions)
    change_counter = Counter(change_types)
    
    # Analyze what comes after different file extensions
    ext_to_changes = defaultdict(Counter)
    ext_to_next_ext = defaultdict(Counter)
    
    for i, sample in enumerate(samples[:-1]):
        curr_ext = sample.get('file_extension', 'unknown')
        next_ext = samples[i+1].get('file_extension', 'unknown')
        next_change = samples[i+1].get('change_type', 'unknown')
        
        ext_to_next_ext[curr_ext][next_ext] += 1
        ext_to_changes[curr_ext][next_change] += 1
    
    return {
        'extension_distribution': dict(ext_counter.most_common(15)),
        'change_type_distribution': dict(change_counter.most_common(10)),
        'extension_transitions': {k: dict(v.most_common(5)) for k, v in ext_to_next_ext.items() if k in dict(ext_counter.most_common(5))},
        'extension_to_change_type': {k: dict(v.most_common(3)) for k, v in ext_to_changes.items() if k in dict(ext_counter.most_common(5))}
    }

def analyze_change_patterns(samples: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns in change types and sizes"""
    change_sequence_pairs = defaultdict(Counter)
    
    # Track what comes after each change type
    for i, sample in enumerate(samples[:-1]):
        curr_change = sample.get('change_type', 'unknown')
        next_change = samples[i+1].get('change_type', 'unknown')
        change_sequence_pairs[curr_change][next_change] += 1
    
    # Analyze lines changed patterns
    lines_added_dist = []
    lines_deleted_dist = []
    
    for sample in samples:
        lines_added_dist.append(sample.get('lines_added', 0))
        lines_deleted_dist.append(sample.get('lines_deleted', 0))
    
    lines_added_dist.sort()
    lines_deleted_dist.sort()
    
    return {
        'change_type_sequences': {k: dict(v.most_common(5)) for k, v in change_sequence_pairs.items()},
        'lines_added_percentiles': {
            'p25': lines_added_dist[len(lines_added_dist)//4],
            'p50': lines_added_dist[len(lines_added_dist)//2],
            'p75': lines_added_dist[3*len(lines_added_dist)//4],
            'p95': lines_added_dist[int(0.95*len(lines_added_dist))],
            'max': max(lines_added_dist)
        },
        'lines_deleted_percentiles': {
            'p25': lines_deleted_dist[len(lines_deleted_dist)//4],
            'p50': lines_deleted_dist[len(lines_deleted_dist)//2],
            'p75': lines_deleted_dist[3*len(lines_deleted_dist)//4],
            'p95': lines_deleted_dist[int(0.95*len(lines_deleted_dist))],
            'max': max(lines_deleted_dist)
        }
    }

def analyze_commit_patterns(samples: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns related to commits"""
    commit_shas = defaultdict(list)
    commits_with_multiple_changes = 0
    
    for sample in samples:
        sha = sample.get('commit_sha')
        if sha:
            commit_shas[sha].append(sample)
    
    commits_with_multiple_changes = sum(1 for changes in commit_shas.values() if len(changes) > 1)
    
    # Analyze sequences within same commit
    within_commit_ext_transitions = defaultdict(Counter)
    within_commit_change_transitions = defaultdict(Counter)
    
    for changes in commit_shas.values():
        if len(changes) > 1:
            for i in range(len(changes) - 1):
                curr_ext = changes[i].get('file_extension', 'unknown')
                next_ext = changes[i+1].get('file_extension', 'unknown')
                curr_change = changes[i].get('change_type', 'unknown')
                next_change = changes[i+1].get('change_type', 'unknown')
                
                within_commit_ext_transitions[curr_ext][next_ext] += 1
                within_commit_change_transitions[curr_change][next_change] += 1
    
    return {
        'unique_commits': len(commit_shas),
        'commits_with_multiple_changes': commits_with_multiple_changes,
        'avg_changes_per_commit': len(samples) / len(commit_shas),
        'within_commit_extension_transitions': {k: dict(v.most_common(5)) for k, v in within_commit_ext_transitions.items() if len(v) > 0},
        'within_commit_change_transitions': {k: dict(v.most_common(5)) for k, v in within_commit_change_transitions.items() if len(v) > 0}
    }

def analyze_directory_patterns(samples: List[Dict]) -> Dict[str, Any]:
    """Analyze directory/path patterns"""
    path_to_ext = defaultdict(Counter)
    path_to_change = defaultdict(Counter)
    directory_changes = Counter()
    
    for sample in samples:
        path = sample.get('file_path', '')
        if path:
            # Extract directory
            parts = path.split('/')
            if len(parts) > 1:
                directory = '/'.join(parts[:-1])
                directory_changes[directory] += 1
                file_ext = sample.get('file_extension', 'unknown')
                change_type = sample.get('change_type', 'unknown')
                path_to_ext[directory][file_ext] += 1
                path_to_change[directory][change_type] += 1
    
    top_dirs = dict(directory_changes.most_common(10))
    
    return {
        'top_directories': top_dirs,
        'directory_file_patterns': {k: dict(v.most_common(3)) for k, v in path_to_ext.items() if k in [d for d, _ in directory_changes.most_common(5)]},
        'directory_change_patterns': {k: dict(v.most_common(3)) for k, v in path_to_change.items() if k in [d for d, _ in directory_changes.most_common(5)]}
    }

def identify_next_action_patterns(samples: List[Dict]) -> Dict[str, Any]:
    """Identify high-confidence patterns for predicting next action"""
    patterns = []
    
    for i in range(len(samples) - 1):
        current = samples[i]
        next_action = samples[i+1]
        
        pattern = {
            'current_ext': current.get('file_extension'),
            'current_change': current.get('change_type'),
            'current_lines_added': current.get('lines_added', 0),
            'current_lines_deleted': current.get('lines_deleted', 0),
            'next_ext': next_action.get('file_extension'),
            'next_change': next_action.get('change_type'),
            'same_commit': current.get('commit_sha') == next_action.get('commit_sha')
        }
        patterns.append(pattern)
    
    # Find high-confidence patterns
    pattern_frequencies = defaultdict(int)
    pattern_outcomes = defaultdict(Counter)
    
    for pattern in patterns:
        key = (pattern['current_ext'], pattern['current_change'], pattern['same_commit'])
        next_key = pattern['next_ext']
        pattern_frequencies[key] += 1
        pattern_outcomes[key][next_key] += 1
    
    # Filter for high-confidence predictions (>2% of data)
    confidence_threshold = len(patterns) * 0.02
    high_confidence_patterns = {}
    
    for pattern_key, count in pattern_frequencies.items():
        if count > confidence_threshold:
            outcomes = pattern_outcomes[pattern_key]
            total_outcomes = sum(outcomes.values())
            top_outcome = outcomes.most_common(1)[0]
            confidence = top_outcome[1] / total_outcomes
            
            if confidence > 0.4:  # At least 40% confidence
                high_confidence_patterns[str(pattern_key)] = {
                    'frequency': count,
                    'predicted_next_extension': top_outcome[0],
                    'confidence': round(confidence, 3),
                    'outcome_distribution': dict(outcomes.most_common(5))
                }
    
    return {
        'high_confidence_patterns': high_confidence_patterns,
        'pattern_count': len(patterns),
        'unique_pattern_combinations': len(pattern_frequencies)
    }

def main():
    print("Loading dataset sample...")
    samples = load_dataset_sample('/Users/erinma/.cursor/worktrees/IBMCodeCompletion/IAOE3/data/combined_dataset.json')
    print(f"Loaded {len(samples)} samples\n")
    
    print("="*80)
    print("FILE EXTENSION PATTERNS")
    print("="*80)
    ext_analysis = analyze_file_extension_patterns(samples)
    print(f"\nTop Extensions: {ext_analysis['extension_distribution']}")
    print(f"\nChange Types: {ext_analysis['change_type_distribution']}")
    print(f"\nExtension Transitions (what file type comes after current type):")
    for ext, transitions in list(ext_analysis['extension_transitions'].items())[:3]:
        print(f"  After .{ext}: {transitions}")
    
    print("\n" + "="*80)
    print("CHANGE TYPE PATTERNS")
    print("="*80)
    change_analysis = analyze_change_patterns(samples)
    print(f"\nChange Type Sequences (what change type comes after current):")
    for change, sequences in change_analysis['change_type_sequences'].items():
        print(f"  After '{change}': {sequences}")
    
    print(f"\nLines Added Distribution:")
    for percentile, value in change_analysis['lines_added_percentiles'].items():
        print(f"  {percentile}: {value}")
    
    print("\n" + "="*80)
    print("COMMIT PATTERNS")
    print("="*80)
    commit_analysis = analyze_commit_patterns(samples)
    print(f"\nUnique Commits: {commit_analysis['unique_commits']}")
    print(f"Commits with Multiple Changes: {commit_analysis['commits_with_multiple_changes']}")
    print(f"Average Changes per Commit: {commit_analysis['avg_changes_per_commit']:.2f}")
    
    print(f"\nWithin-Commit Extension Transitions:")
    for ext, transitions in list(commit_analysis['within_commit_extension_transitions'].items())[:3]:
        print(f"  {ext} -> {transitions}")
    
    print("\n" + "="*80)
    print("DIRECTORY PATTERNS")
    print("="*80)
    dir_analysis = analyze_directory_patterns(samples)
    print(f"\nTop Directories: {dir_analysis['top_directories']}")
    
    print("\n" + "="*80)
    print("NEXT ACTION PREDICTION PATTERNS")
    print("="*80)
    next_action_analysis = identify_next_action_patterns(samples)
    print(f"\nTotal Patterns Analyzed: {next_action_analysis['pattern_count']}")
    print(f"Unique Pattern Combinations: {next_action_analysis['unique_pattern_combinations']}")
    print(f"\nHigh-Confidence Prediction Rules:")
    for pattern, details in list(next_action_analysis['high_confidence_patterns'].items())[:10]:
        print(f"\n  Pattern: {pattern}")
        print(f"    Frequency: {details['frequency']}")
        print(f"    Next Action: .{details['predicted_next_extension']}")
        print(f"    Confidence: {details['confidence']*100:.1f}%")
        print(f"    Outcomes: {details['outcome_distribution']}")
    
    # Print sample data
    print("\n" + "="*80)
    print("SAMPLE DATA POINTS")
    print("="*80)
    for i, sample in enumerate(random.sample(samples, min(5, len(samples)))):
        print(f"\nSample {i+1}:")
        print(f"  Commit: {sample.get('commit_message', 'N/A')}")
        print(f"  File: {sample.get('file_path', 'N/A')}")
        print(f"  Extension: {sample.get('file_extension', 'N/A')}")
        print(f"  Change Type: {sample.get('change_type', 'N/A')}")
        print(f"  Lines Added: {sample.get('lines_added', 0)}, Deleted: {sample.get('lines_deleted', 0)}")

if __name__ == '__main__':
    main()


