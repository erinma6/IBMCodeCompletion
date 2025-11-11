import json
import re

# Read the import_commits_report.txt to extract all commit SHAs
commit_shas = set()

with open('/Users/erinma/Documents/IBMCodeCompletion/import_commits_report.txt', 'r') as f:
    for line in f:
        # Look for lines like "   SHA: <sha>"
        if line.strip().startswith('SHA:'):
            sha = line.strip().split('SHA:')[1].strip()
            commit_shas.add(sha)

print(f"Found {len(commit_shas)} unique commits from the report")

# Read the combined_dataset.json and filter for these commits
print("Reading combined_dataset.json...")
with open('/Users/erinma/Documents/IBMCodeCompletion/data/combined_dataset.json', 'r') as f:
    data = json.load(f)

print(f"Total records in combined_dataset.json: {len(data)}")

# Filter records
filtered_data = [record for record in data if record.get('commit_sha') in commit_shas]

print(f"Filtered records with import changes: {len(filtered_data)}")

# Write to new JSON file
output_path = '/Users/erinma/Documents/IBMCodeCompletion/data/import_commits_dataset.json'
with open(output_path, 'w') as f:
    json.dump(filtered_data, f, indent=2)

print(f"\nNew JSON file created: import_commits_dataset.json")
print(f"File size: {len(json.dumps(filtered_data, indent=2)) / (1024*1024):.2f} MB")
print(f"File contains {len(filtered_data)} records from {len(commit_shas)} unique commits")
