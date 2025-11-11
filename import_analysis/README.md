# Import Analysis Task

This folder contains all files related to analyzing import additions and modifications in the IBM Code Completion dataset.

## Folder Structure

### `/scripts`
Python scripts used to analyze and extract import-related commits:
- `find_import_commits.py` - Identifies all commits containing import additions/modifications
- `extract_import_commits.py` - Extracts all records from those commits into a new JSON file
- `create_import_modifications_dataset.py` - Creates a focused dataset with only import modifications

### `/reports`
Analysis results:
- `import_commits_report.txt` - Detailed report of all 576 commits with import changes

### `/datasets`
Generated datasets:
- `import_commits_dataset.json` (248.76 MB) - All 3,914 records from 576 commits with import changes
- `import_modifications_only_dataset.json` (76.54 MB) - 2,484 records containing only actual import modifications

## Summary

| Dataset | Records | Commits | Focus |
|---------|---------|---------|-------|
| import_commits_dataset.json | 3,914 | 576 | All files from commits with import changes |
| import_modifications_only_dataset.json | 2,484 | 589 | Only files with actual import modifications |

## Usage

To run the analysis from scratch:

```bash
cd scripts
python3 find_import_commits.py
python3 extract_import_commits.py
python3 create_import_modifications_dataset.py
```

The datasets generated are suitable for training models on import completion and code pattern recognition.
