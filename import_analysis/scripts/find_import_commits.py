import json
import re
from collections import defaultdict

# Read the JSON file
with open('/Users/erinma/Documents/IBMCodeCompletion/data/combined_dataset.json', 'r') as f:
    data = json.load(f)

# Track commits with import changes
import_commits = defaultdict(lambda: {
    'commit_sha': None,
    'commit_short_sha': None,
    'commit_message': None,
    'commit_author': None,
    'commit_date': None,
    'files_with_imports': [],
    'total_files': 0
})

# Regular expressions to identify import statements
import_patterns = [
    r'^\s*import\s+',  # ES6/JS/TS imports
    r'^\s*from\s+.*\s+import\s+',  # ES6 from imports
    r'^\s*require\(',  # Node.js requires
    r'^\s*from\s+.*\s+import\s+',  # Python imports
    r'^\s*import\s+',  # Python imports
    r'^\s*package\s+',  # Java packages
    r'^\s*import\s+',  # Java imports
    r'^\s*using\s+',  # C# usings
]

def has_import_in_patch(patch):
    """Check if a patch contains import additions or modifications"""
    if not patch:
        return False
    
    lines = patch.split('\n')
    for line in lines:
        # Look for added or modified lines with imports
        if line.startswith('+') and not line.startswith('+++'):
            content = line[1:]  # Remove the '+' prefix
            for pattern in import_patterns:
                if re.match(pattern, content.strip()):
                    return True
    return False

def has_import_change(before, after):
    """Check if before/after content shows import changes"""
    before_imports = extract_imports(before)
    after_imports = extract_imports(after)
    return before_imports != after_imports

def extract_imports(content):
    """Extract all import lines from content"""
    if not content:
        return set()
    
    imports = set()
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        for pattern in import_patterns:
            if re.match(pattern, stripped):
                imports.add(stripped)
                break
    return imports

# Process each record
for record in data:
    commit_sha = record.get('commit_sha')
    patch = record.get('patch', '')
    before = record.get('before_content', '')
    after = record.get('after_content', '')
    file_path = record.get('file_path', '')
    change_type = record.get('change_type', '')
    
    # Check if this record has import changes
    has_import = False
    
    if has_import_in_patch(patch):
        has_import = True
    elif change_type == 'modified' and has_import_change(before, after):
        has_import = True
    elif change_type == 'added' and has_import_change('', after):
        has_import = True
    
    if has_import:
        if commit_sha not in import_commits:
            import_commits[commit_sha] = {
                'commit_sha': record.get('commit_sha'),
                'commit_short_sha': record.get('commit_short_sha'),
                'commit_message': record.get('commit_message'),
                'commit_author': record.get('commit_author'),
                'commit_date': record.get('commit_date'),
                'files_with_imports': [],
                'total_files': record.get('total_files_in_commit', 0)
            }
        
        import_commits[commit_sha]['files_with_imports'].append({
            'file_path': file_path,
            'change_type': change_type,
            'file_extension': record.get('file_extension', '')
        })

# Sort by commit date
sorted_commits = sorted(
    import_commits.values(),
    key=lambda x: x['commit_date'] if x['commit_date'] else ''
)

# Generate report
print("=" * 100)
print("COMMITS WITH IMPORT ADDITIONS OR MODIFICATIONS")
print("=" * 100)
print()

for i, commit in enumerate(sorted_commits, 1):
    print(f"{i}. Commit: {commit['commit_short_sha']}")
    print(f"   SHA: {commit['commit_sha']}")
    print(f"   Message: {commit['commit_message']}")
    print(f"   Author: {commit['commit_author']}")
    print(f"   Date: {commit['commit_date']}")
    print(f"   Total files in commit: {commit['total_files']}")
    print(f"   Files with import changes: {len(commit['files_with_imports'])}")
    print(f"   Files:")
    for file_info in commit['files_with_imports']:
        print(f"     - {file_info['file_path']} ({file_info['file_extension']}) [{file_info['change_type']}]")
    print()

print("=" * 100)
print(f"SUMMARY: Found {len(sorted_commits)} commits with import changes")
print("=" * 100)

# Save detailed report to file
with open('/Users/erinma/Documents/IBMCodeCompletion/import_commits_report.txt', 'w') as f:
    f.write("COMMITS WITH IMPORT ADDITIONS OR MODIFICATIONS\n")
    f.write("=" * 100 + "\n\n")
    
    for i, commit in enumerate(sorted_commits, 1):
        f.write(f"{i}. Commit: {commit['commit_short_sha']}\n")
        f.write(f"   SHA: {commit['commit_sha']}\n")
        f.write(f"   Message: {commit['commit_message']}\n")
        f.write(f"   Author: {commit['commit_author']}\n")
        f.write(f"   Date: {commit['commit_date']}\n")
        f.write(f"   Total files in commit: {commit['total_files']}\n")
        f.write(f"   Files with import changes: {len(commit['files_with_imports'])}\n")
        f.write(f"   Files:\n")
        for file_info in commit['files_with_imports']:
            f.write(f"     - {file_info['file_path']} ({file_info['file_extension']}) [{file_info['change_type']}]\n")
        f.write("\n")
    
    f.write("=" * 100 + "\n")
    f.write(f"SUMMARY: Found {len(sorted_commits)} commits with import changes\n")
    f.write("=" * 100 + "\n")

print("\nReport saved to: import_commits_report.txt")
