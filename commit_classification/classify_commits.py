#!/usr/bin/env python3
"""
Classify commits based on primary classification approach.
Categories: Refactoring, Feature Development, Bug Fixes, Documentation, Formatting/Cleanup
"""

import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple

def load_dataset(file_path):
    """Load the combined dataset."""
    with open(file_path, 'r') as f:
        return json.load(f)

def aggregate_by_commit(data):
    """Group file changes by commit_sha."""
    commits = defaultdict(list)
    for entry in data:
        commits[entry['commit_sha']].append(entry)
    return commits

def classify_commit(commit_entries: List[Dict]) -> Tuple[str, float, List[str]]:
    """
    Classify a commit based on primary categories.
    Returns: (primary_class, confidence_score, reasoning)
    """
    # Get commit-level info from first entry (same for all entries in commit)
    first_entry = commit_entries[0]
    message = first_entry['commit_message'].lower()
    
    # Aggregate change statistics
    change_types = defaultdict(int)
    file_extensions = defaultdict(int)
    total_files = len(commit_entries)
    total_lines_added = 0
    total_lines_deleted = 0
    
    for entry in commit_entries:
        change_types[entry['change_type']] += 1
        file_extensions[entry['file_extension']] += 1
        total_lines_added += entry['lines_added']
        total_lines_deleted += entry['lines_deleted']
    
    reasons = []
    scores = {}
    
    # ===== DOCUMENTATION Classification =====
    doc_keywords = ['doc', 'readme', 'document', 'comment', 'guide', 'wiki', 'markdown']
    doc_extensions = ['md', 'txt', 'rst']
    
    if any(keyword in message for keyword in doc_keywords):
        scores['documentation'] = 0.95
        reasons.append(f"Keyword match: {[k for k in doc_keywords if k in message]}")
    elif file_extensions.get('md', 0) > total_files * 0.7:
        scores['documentation'] = 0.90
        reasons.append(f"Primary extension is markdown ({file_extensions.get('md', 0)}/{total_files})")
    elif all(ext in doc_extensions for ext in file_extensions.keys()):
        scores['documentation'] = 0.85
        reasons.append("All files are documentation extensions")
    
    # ===== FORMATTING/CLEANUP Classification =====
    format_keywords = ['format', 'cleanup', 'clean up', 'indent', 'style', 'lint', 'whitespace', 'reformat']
    
    if any(keyword in message for keyword in format_keywords):
        # Check if changes are small and widespread
        avg_change_size = (total_lines_added + total_lines_deleted) / total_files if total_files > 0 else 0
        if total_files >= 3 and avg_change_size <= 6:
            scores['formatting'] = 0.95
            reasons.append(f"Format keyword + multi-file small changes (avg {avg_change_size:.1f} lines)")
        elif total_files >= 2 and avg_change_size <= 6:
            scores['formatting'] = 0.85
            reasons.append(f"Format keyword + small changes (avg {avg_change_size:.1f} lines)")
        else:
            scores['formatting'] = 0.75
            reasons.append("Format keyword detected")
    
    # ===== REFACTORING Classification =====
    refactor_keywords = ['refactor', 'restructure', 'reorganize', 'rename', 'migrate']
    
    if any(keyword in message for keyword in refactor_keywords):
        # Check change patterns
        if change_types.get('renamed', 0) >= 3:
            scores['refactoring'] = 0.95
            reasons.append(f"Refactor keyword + multiple renames ({change_types['renamed']} files)")
        elif change_types.get('modified', 0) >= total_files * 0.8:
            scores['refactoring'] = 0.90
            reasons.append(f"Refactor keyword + mostly modified files ({change_types['modified']}/{total_files})")
        else:
            scores['refactoring'] = 0.85
            reasons.append("Refactor keyword detected")
    
    # Rename pattern (even without explicit keyword)
    if change_types.get('renamed', 0) >= 3 and 'refactoring' not in scores:
        scores['refactoring'] = 0.80
        reasons.append(f"Multiple renames detected ({change_types['renamed']} files)")
    
    # ===== BUG FIX Classification =====
    fix_keywords = ['fix', 'bugfix', 'bug fix', 'resolve', 'patch', 'issue', 'bug', 'error', 'crash']
    
    if any(keyword in message for keyword in fix_keywords):
        # Bug fixes typically modify specific files with targeted changes
        if change_types.get('modified', 0) >= total_files * 0.7:
            scores['bug_fix'] = 0.95
            reasons.append(f"Fix keyword + targeted modifications ({change_types['modified']}/{total_files})")
        else:
            scores['bug_fix'] = 0.85
            reasons.append("Fix keyword detected")
    
    # ===== FEATURE DEVELOPMENT Classification =====
    feature_keywords = ['add', 'implement', 'feature', 'feat:', 'new', 'support', 'enhancement']
    
    if any(keyword in message for keyword in feature_keywords):
        # Features typically add new files or add significant lines
        if change_types.get('added', 0) >= total_files * 0.5:
            scores['feature'] = 0.95
            reasons.append(f"Feature keyword + new files ({change_types['added']}/{total_files})")
        elif total_lines_added > total_lines_deleted * 1.5:
            scores['feature'] = 0.90
            reasons.append(f"Feature keyword + more additions than deletions ({total_lines_added} vs {total_lines_deleted})")
        else:
            scores['feature'] = 0.80
            reasons.append("Feature keyword detected")
    
    # Default: Feature if mostly additions
    if not scores and total_lines_added > 0 and total_lines_added > total_lines_deleted:
        scores['feature'] = 0.70
        reasons.append(f"More additions than deletions ({total_lines_added} vs {total_lines_deleted})")
    
    # Default: Refactoring if mostly modifications
    if not scores and change_types.get('modified', 0) >= total_files * 0.7:
        scores['refactoring'] = 0.65
        reasons.append(f"Mostly modifications ({change_types['modified']}/{total_files})")
    
    # Fallback to feature
    if not scores:
        scores['feature'] = 0.50
        reasons.append("No clear pattern - defaulting to feature")
    
    # Get highest score
    primary_class = max(scores.items(), key=lambda x: x[1])[0]
    confidence = scores[primary_class]
    
    return primary_class, confidence, reasons, {
        'total_files': total_files,
        'change_types': dict(change_types),
        'file_extensions': dict(file_extensions),
        'total_lines_added': total_lines_added,
        'total_lines_deleted': total_lines_deleted,
        'all_scores': scores
    }

def main():
    """Main classification routine."""
    # Load data
    print("Loading dataset...")
    data = load_dataset('/Users/erinma/Documents/IBMCodeCompletion/data/combined_dataset_filtered.json')
    print(f"Loaded {len(data)} entries")
    
    # Aggregate by commit
    print("Aggregating by commit...")
    commits = aggregate_by_commit(data)
    print(f"Found {len(commits)} unique commits")
    
    # Classify each commit
    print("Classifying commits...")
    classifications = []
    class_counts = defaultdict(int)
    
    for commit_sha, entries in commits.items():
        primary_class, confidence, reasons, metadata = classify_commit(entries)
        
        classifications.append({
            'commit_sha': commit_sha,
            'commit_short_sha': entries[0]['commit_short_sha'],
            'commit_message': entries[0]['commit_message'],
            'commit_author': entries[0]['commit_author'],
            'commit_date': entries[0]['commit_date'],
            'primary_class': primary_class,
            'confidence': confidence,
            'reasoning': reasons,
            'metadata': metadata
        })
        
        class_counts[primary_class] += 1
    
    # Print statistics
    print("\n" + "="*80)
    print("CLASSIFICATION RESULTS")
    print("="*80)
    
    for class_name in ['documentation', 'formatting', 'refactoring', 'bug_fix', 'feature']:
        count = class_counts[class_name]
        percentage = (count / len(commits)) * 100
        print(f"{class_name.upper():20} {count:5d} commits ({percentage:6.2f}%)")
    
    print("="*80)
    
    # Print sample classifications
    print("\nSAMPLE CLASSIFICATIONS (by category):")
    print("-" * 80)
    
    for primary_class in ['documentation', 'formatting', 'refactoring', 'bug_fix', 'feature']:
        samples = [c for c in classifications if c['primary_class'] == primary_class][:3]
        if samples:
            print(f"\n{primary_class.upper()}:")
            for sample in samples:
                print(f"  SHA: {sample['commit_short_sha']} | Conf: {sample['confidence']:.2f}")
                print(f"  Message: {sample['commit_message']}")
                print(f"  Files: {sample['metadata']['total_files']} | "
                      f"Added: {sample['metadata']['total_lines_added']} | "
                      f"Deleted: {sample['metadata']['total_lines_deleted']}")
                print()
    
    # Save classifications
    output_path = '/Users/erinma/Documents/IBMCodeCompletion/data/classified_commits.json'
    print(f"\nSaving classifications to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(classifications, f, indent=2)
    
    print(f"Saved {len(classifications)} classified commits")
    
    # Create summary report
    report_path = '/Users/erinma/Documents/IBMCodeCompletion/CLASSIFICATION_REPORT.txt'
    print(f"\nGenerating report at {report_path}...")
    
    with open(report_path, 'w') as f:
        f.write("╔" + "═"*78 + "╗\n")
        f.write("║" + " "*78 + "║\n")
        f.write("║" + "COMMIT CLASSIFICATION REPORT - PRIMARY CATEGORIES".center(78) + "║\n")
        f.write("║" + " "*78 + "║\n")
        f.write("╚" + "═"*78 + "╝\n\n")
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total commits: {len(commits)}\n")
        f.write(f"Total file changes: {len(data)}\n\n")
        
        f.write("DISTRIBUTION BY PRIMARY CLASS\n")
        f.write("-" * 80 + "\n")
        for class_name in ['documentation', 'formatting', 'refactoring', 'bug_fix', 'feature']:
            count = class_counts[class_name]
            percentage = (count / len(commits)) * 100
            bar = "█" * int(percentage / 2)
            f.write(f"{class_name.upper():20} {count:5d} ({percentage:6.2f}%) {bar}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("DETAILED BREAKDOWNS\n")
        f.write("="*80 + "\n\n")
        
        for primary_class in ['documentation', 'formatting', 'refactoring', 'bug_fix', 'feature']:
            class_entries = [c for c in classifications if c['primary_class'] == primary_class]
            if not class_entries:
                continue
            
            f.write(f"\n{primary_class.upper()}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Count: {len(class_entries)}\n")
            
            # Confidence statistics
            confidences = [c['confidence'] for c in class_entries]
            avg_conf = sum(confidences) / len(confidences)
            f.write(f"Average confidence: {avg_conf:.2f}\n")
            
            # Sample commits
            f.write(f"\nSample commits (showing 5):\n")
            for sample in class_entries[:5]:
                f.write(f"\n  {sample['commit_short_sha']} | {sample['commit_message']}\n")
                f.write(f"  Confidence: {sample['confidence']:.2f}\n")
                f.write(f"  Files: {sample['metadata']['total_files']} | ")
                f.write(f"Added: {sample['metadata']['total_lines_added']} | ")
                f.write(f"Deleted: {sample['metadata']['total_lines_deleted']}\n")
                f.write(f"  Reasoning: {'; '.join(sample['reasoning'][:2])}\n")
        
    print("Report generated successfully!")

if __name__ == '__main__':
    main()

