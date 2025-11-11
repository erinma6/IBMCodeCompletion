import json
import random
from pathlib import Path

def load_sample_commits(dataset_path, sample_size=5):
    """Load a random sample of commits from the dataset"""
    print(f"Loading dataset from {dataset_path}...")
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total records in dataset: {len(data)}")
    
    # Filter records that have model_input_text and model_target_text
    valid_records = [r for r in data if r.get('model_input_text') and r.get('model_target_text')]
    print(f"Valid records (with input/target text): {len(valid_records)}")
    
    # Random sample
    sample = random.sample(valid_records, min(sample_size, len(valid_records)))
    return sample, len(data), len(valid_records)


def analyze_record_for_code_completion(record, index):
    """Analyze a single record for code completion suitability"""
    print("\n" + "="*80)
    print(f"SAMPLE {index + 1}")
    print("="*80)
    
    # Basic metadata
    print(f"\nCommit: {record.get('commit_short_sha', 'N/A')}")
    print(f"Message: {record.get('commit_message', 'N/A')[:100]}...")
    print(f"File: {record.get('file_path', 'N/A')}")
    print(f"File Extension: {record.get('file_extension', 'N/A')}")
    print(f"Change Type: {record.get('change_type', 'N/A')}")
    print(f"Lines Added: {record.get('lines_added', 0)}")
    print(f"Lines Deleted: {record.get('lines_deleted', 0)}")
    print(f"Chunk {record.get('chunk_id', 0) + 1} of {record.get('total_chunks_in_file', 1)}")
    
    # Show input text (with markers)
    model_input = record.get('model_input_text', '')
    model_target = record.get('model_target_text', '')
    
    print(f"\n--- MODEL INPUT (First 1000 chars) ---")
    print(model_input[:1000])
    if len(model_input) > 1000:
        print(f"... ({len(model_input)} total chars)")
    
    print(f"\n--- MODEL TARGET (First 500 chars) ---")
    print(model_target[:500])
    if len(model_target) > 500:
        print(f"... ({len(model_target)} total chars)")
    
    # Analyze suitability
    print(f"\n--- SUITABILITY ANALYSIS ---")
    
    suitability_score = 0
    max_score = 10
    issues = []
    strengths = []
    
    # Check 1: Has clear editable region markers
    if '<|editable_region_start|>' in model_input and '<|editable_region_end|>' in model_input:
        suitability_score += 2
        strengths.append("✓ Clear editable region markers present")
    else:
        issues.append("✗ Missing or unclear editable region markers")
    
    # Check 2: Reasonable input/output size
    input_lines = len(model_input.split('\n'))
    target_lines = len(model_target.split('\n'))
    
    if 10 <= input_lines <= 500:
        suitability_score += 1
        strengths.append(f"✓ Input size reasonable ({input_lines} lines)")
    else:
        issues.append(f"⚠ Input size may be suboptimal ({input_lines} lines)")
    
    if 1 <= target_lines <= 100:
        suitability_score += 1
        strengths.append(f"✓ Target size reasonable ({target_lines} lines)")
    else:
        issues.append(f"⚠ Target size may be suboptimal ({target_lines} lines)")
    
    # Check 3: Has meaningful changes
    if record.get('lines_added', 0) > 0 or record.get('lines_deleted', 0) > 0:
        suitability_score += 2
        strengths.append(f"✓ Meaningful changes (+ {record.get('lines_added', 0)}, - {record.get('lines_deleted', 0)} lines)")
    else:
        issues.append("✗ No meaningful changes detected")
    
    # Check 4: Code file (not binary or unusual)
    code_extensions = ['py', 'js', 'ts', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php', 'swift', 'kt', 'tsx', 'jsx', 'cs', 'html', 'css', 'scss']
    if record.get('file_extension', '').lower() in code_extensions:
        suitability_score += 2
        strengths.append(f"✓ Common code file type (.{record.get('file_extension')})")
    else:
        issues.append(f"⚠ Unusual file extension (.{record.get('file_extension')})")
    
    # Check 5: Not a deletion
    if record.get('change_type') != 'removed':
        suitability_score += 1
        strengths.append("✓ File not deleted")
    else:
        issues.append("✗ File was deleted (less useful for code completion)")
    
    # Check 6: Has patch data
    if record.get('patch'):
        suitability_score += 1
        strengths.append("✓ Patch data available")
    else:
        issues.append("⚠ No patch data")
    
    print(f"\nSuitability Score: {suitability_score}/{max_score}")
    
    print("\nStrengths:")
    for s in strengths:
        print(f"  {s}")
    
    if issues:
        print("\nPotential Issues:")
        for i in issues:
            print(f"  {i}")
    
    # Overall assessment
    print("\nOVERALL ASSESSMENT:")
    if suitability_score >= 8:
        print("✓ EXCELLENT - This data is well-suited for code completion training")
    elif suitability_score >= 6:
        print("✓ GOOD - This data is suitable for code completion training")
    elif suitability_score >= 4:
        print("⚠ FAIR - This data may work but has some limitations")
    else:
        print("✗ POOR - This data may not be suitable for code completion training")
    
    return suitability_score, max_score


def main():
    dataset_path = Path('data/combined_dataset.json')
    
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return
    
    # Load sample
    sample, total_records, valid_records = load_sample_commits(dataset_path, sample_size=3)
    
    # Analyze each sample
    scores = []
    for i, record in enumerate(sample):
        score, max_score = analyze_record_for_code_completion(record, i)
        scores.append(score)
    
    # Overall summary
    print("\n" + "="*80)
    print("OVERALL DATASET ASSESSMENT")
    print("="*80)
    print(f"\nTotal records: {total_records}")
    print(f"Valid records with input/target: {valid_records} ({valid_records/total_records*100:.1f}%)")
    print(f"\nSamples analyzed: {len(scores)}")
    print(f"Average suitability score: {sum(scores)/len(scores):.1f}/{max_score}")
    
    print("\n--- CONCLUSION ---")
    avg_score = sum(scores) / len(scores) if scores else 0
    
    if avg_score >= 8:
        print("✓ This dataset appears EXCELLENT for code completion prediction!")
        print("  The data has clear markers, reasonable sizes, and meaningful code changes.")
    elif avg_score >= 6:
        print("✓ This dataset appears GOOD for code completion prediction!")
        print("  The data structure supports the task well, though there may be some edge cases.")
    elif avg_score >= 4:
        print("⚠ This dataset is FAIR for code completion prediction.")
        print("  Consider filtering or preprocessing to improve quality.")
    else:
        print("✗ This dataset may have SIGNIFICANT ISSUES for code completion prediction.")
        print("  Review the samples above and consider data quality improvements.")
    
    print("\nKey features of this dataset:")
    print("  • Uses <|editable_region_start|> and <|editable_region_end|> markers")
    print("  • Provides 'before' code with markers as input")
    print("  • Provides edited region content as target")
    print("  • Includes metadata (commit info, file paths, change statistics)")
    print("  • Suitable for training models to predict code edits")


if __name__ == "__main__":
    main()

