import json
import re

# Patterns to identify import statements
import_patterns = [
    r'^\s*import\s+',  # Java/JS/TS imports
    r'^\s*from\s+.*\s+import\s+',  # ES6 from imports
    r'^\s*require\(',  # Node.js requires
    r'^\s*package\s+',  # Java packages
    r'^\s*using\s+',  # C# usings
]

def has_import_statement(line):
    """Check if a line contains an import statement"""
    stripped = line.strip()
    for pattern in import_patterns:
        if re.match(pattern, stripped):
            return True
    return False

def extract_imports(content):
    """Extract all import lines from content"""
    if not content:
        return set()
    
    imports = set()
    lines = content.split('\n')
    for line in lines:
        if has_import_statement(line):
            imports.add(line.strip())
    return imports

def has_import_modification(record):
    """Check if a record has actual import modifications"""
    patch = record.get('patch', '')
    before = record.get('before_content', '')
    after = record.get('after_content', '')
    
    # Method 1: Check patch for import additions/removals
    if patch:
        lines = patch.split('\n')
        for line in lines:
            # Look for added lines (start with +) or removed lines (start with -)
            if (line.startswith('+') and not line.startswith('+++')) or \
               (line.startswith('-') and not line.startswith('---')):
                content = line[1:]  # Remove the +/- prefix
                if has_import_statement(content):
                    return True
    
    # Method 2: Compare before and after for import differences
    if before or after:
        before_imports = extract_imports(before)
        after_imports = extract_imports(after)
        if before_imports != after_imports:
            return True
    
    return False

# Read the combined dataset
print("Reading combined_dataset.json...")
with open('/Users/erinma/Documents/IBMCodeCompletion/data/combined_dataset.json', 'r') as f:
    data = json.load(f)

print(f"Total records: {len(data)}")

# Filter for records with actual import modifications
print("Filtering for import modifications (this may take a moment)...")
filtered_data = [record for record in data if has_import_modification(record)]

print(f"Records with import modifications: {len(filtered_data)}")

# Count unique commits
unique_commits = set(record.get('commit_sha') for record in filtered_data)
print(f"Unique commits: {len(unique_commits)}")

# Write to new JSON file
output_path = '/Users/erinma/Documents/IBMCodeCompletion/data/import_modifications_only_dataset.json'
with open(output_path, 'w') as f:
    json.dump(filtered_data, f, indent=2)

print(f"\nNew JSON file created: import_modifications_only_dataset.json")
file_size_mb = len(json.dumps(filtered_data, indent=2)) / (1024*1024)
print(f"File size: {file_size_mb:.2f} MB")
print(f"\nComparison:")
print(f"  Original dataset: 5,781 records")
print(f"  Import commits dataset: 3,914 records (all files from 576 commits with imports)")
print(f"  Import modifications only: {len(filtered_data)} records (only import changes)")
print(f"  Reduction: {((3914 - len(filtered_data)) / 3914 * 100):.1f}% smaller than import commits dataset")
