from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import datasets
import difflib
import webbrowser
import os
import random

# Load the full dataset
ds = datasets.load_dataset(
    "json", data_files="data/combined_dataset_filtered.json"
)
ds_train = ds["train"]

# Get total dataset length and randomly select 10 commits
total_commits = len(ds_train)
num_commits_to_select = 10
selected_indices = random.sample(range(total_commits), min(num_commits_to_select, total_commits))

# Create HTML console for output
console_html = Console(record=True, file=open(os.devnull, 'w'))

table = Table(title="Commit Comparison")


# Loop through each selected commit and create a table
for idx, commit_idx in enumerate(selected_indices, 1):
    commit_data = ds_train[commit_idx]
    
    # Create a table for this commit
    commit_title = f"Commit {idx} (Index {commit_idx})"
    if 'commit_sha' in commit_data:
        commit_title += f" - SHA: {commit_data['commit_sha'][:8]}"
    
    table = Table(title=commit_title)
    table.add_column("Before")
    table.add_column("After")
    table.add_column("Diff")
    
    lines1 = commit_data["before_content"].splitlines(keepends=True)
    lines2 = commit_data["after_content"].splitlines(keepends=True)
    
    # Generate the unified diff
    diff = difflib.unified_diff(
        lines1, lines2, fromfile="snippet1.py", tofile="snippet2.py", lineterm=""
    )
    
    # Add row to table
    table.add_row(
        Markdown(f"```java\n{commit_data['before_content']}```"),
        Markdown(f"```java\n{commit_data['after_content']}```"),
        Markdown(f"```java{''.join(diff)}```"),
    )
    
    # Print table to console
    console_html.print(table)
    console_html.print()  # Add spacing between tables

# Export to HTML
html_output = console_html.export_html()

# Save to file and open in browser
output_file = "/tmp/comparison_output.html"
with open(output_file, "w") as f:
    f.write(html_output)

webbrowser.open(f"file://{os.path.abspath(output_file)}")
