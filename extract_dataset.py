import os
import sys
import json
import base64
import argparse
import logging
from datetime import datetime
from pathlib import Path
import re
from github import Github

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract dataset from GitHub repositories for next-edit prediction'
    )
    
    # Required arguments
    parser.add_argument(
        '--repos',
        nargs='+',
        required=True,
        help='Repository names (user/repo) or path to file with repo list'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory to save output files'
    )
    
    # Optional arguments with defaults
    parser.add_argument(
        '--min-files',
        type=int,
        default=2,
        help='Minimum files changed in commit (default: 2)'
    )
    parser.add_argument(
        '--max-files',
        type=int,
        default=8,
        help='Maximum files changed in commit (default: 8)'
    )
    parser.add_argument(
        '--context-before',
        type=int,
        default=1,
        help='Context lines before edit region (default: 1)'
    )
    parser.add_argument(
        '--context-after',
        type=int,
        default=5,
        help='Context lines after edit region (default: 5)'
    )
    parser.add_argument(
        '--max-gap',
        type=int,
        default=10,
        help='Max line gap to merge hunks (default: 10)'
    )
    
    return parser.parse_args()


def load_repositories(repos_input):
    """
    Load repository list from input (either direct list or file)
    
    Args:
        repos_input: List of repo names or path to file
        
    Returns:
        List of repository names
    """
    # Check if first item is a file
    if len(repos_input) == 1 and os.path.isfile(repos_input[0]):
        logger.info(f"Loading repositories from file: {repos_input[0]}")
        with open(repos_input[0], 'r') as f:
            repos = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return repos
    else:
        return repos_input


def connect_to_repo(repo_name, token):
    """Connect to GitHub repository"""
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        logger.info(f"Connected to {repo.full_name}")
        return repo
    except Exception as e:
        logger.error(f"Failed to connect to {repo_name}: {e}")
        return None


def filter_commits(repo, min_files, max_files):
    """Filter commits by file count"""
    logger.info(f"Filtering commits ({min_files}-{max_files} files)...")
    
    all_commits = list(repo.get_commits())
    filtered_commits = []
    
    for commit in all_commits:
        files_changed = list(commit.files)
        file_count = len(files_changed)
        
        if min_files <= file_count <= max_files:
            commit_info = {
                'sha': commit.sha,
                'short_sha': commit.sha[:8],
                'message': commit.commit.message.strip(),
                'author': commit.commit.author.name,
                'date': commit.commit.author.date,
                'files_changed': file_count,
                'files': [f.filename for f in files_changed],
                'file_details': []
            }
            
            for file_change in files_changed:
                file_info = {
                    'filename': file_change.filename,
                    'status': file_change.status,
                    'additions': file_change.additions,
                    'deletions': file_change.deletions,
                    'changes': file_change.changes
                }
                commit_info['file_details'].append(file_info)
            
            filtered_commits.append(commit_info)
    
    logger.info(f"Filtered {len(filtered_commits)} commits from {len(all_commits)} total")
    return filtered_commits


def get_file_content(repo, file_path, commit_sha):
    """Get file content at specific commit"""
    try:
        file_obj = repo.get_contents(file_path, ref=commit_sha)
        if file_obj.encoding == 'base64':
            return base64.b64decode(file_obj.content).decode('utf-8')
        else:
            return file_obj.decoded_content.decode('utf-8')
    except Exception as e:
        logger.debug(f"Could not get content for {file_path}: {e}")
        return None


def get_patch_for_file(commit_obj, file_path):
    """Get patch for specific file"""
    try:
        for file_change in commit_obj.files:
            if file_change.filename == file_path:
                return file_change.patch
        return None
    except Exception as e:
        return None


def extract_file_level_data(repo, filtered_commits):
    """Extract file-level data from commits"""
    file_level_records = []
    
    logger.info(f"Extracting data from {len(filtered_commits)} commits...")
    
    for commit in filtered_commits:
        commit_sha = commit['sha']
        commit_obj = repo.get_commit(commit_sha)
        
        for file_index, file_detail in enumerate(commit['file_details']):
            file_path = file_detail['filename']
            change_type = file_detail['status']
            
            file_extension = file_path.split('.')[-1] if '.' in file_path else ''
            
            patch = get_patch_for_file(commit_obj, file_path)
            
            before_content = None
            if change_type != 'added':
                parent_commits = commit_obj.parents
                if parent_commits:
                    parent_sha = parent_commits[0].sha
                    before_content = get_file_content(repo, file_path, parent_sha)
            
            after_content = None
            if change_type != 'removed':
                after_content = get_file_content(repo, file_path, commit_sha)
            
            record = {
                'commit_sha': commit_sha,
                'commit_short_sha': commit['short_sha'],
                'commit_message': commit['message'],
                'commit_author': commit['author'],
                'commit_date': commit['date'],
                'total_files_in_commit': len(commit['file_details']),
                'sequence_order': file_index + 1,
                'file_path': file_path,
                'file_extension': file_extension,
                'change_type': change_type,
                'lines_added': file_detail['additions'],
                'lines_deleted': file_detail['deletions'],
                'total_changes': file_detail['changes'],
                'before_content': before_content,
                'after_content': after_content,
                'patch': patch,
                'editable_region_start': None,
                'editable_region_end': None,
                'change_labels': None
            }
            
            file_level_records.append(record)
    
    logger.info(f"Extracted {len(file_level_records)} file-level records")
    return file_level_records


def parse_patch_hunks(patch):
    """Parse patch into separate hunks"""
    if not patch:
        return []
    
    hunks = []
    lines = patch.split('\n')
    
    for line in lines:
        if line.startswith('@@'):
            match = re.search(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                end_line = old_start + old_count
                hunks.append((old_start, end_line))
    
    return hunks


def merge_close_hunks(hunks, max_gap):
    """Merge hunks that are close together"""
    if not hunks:
        return []
    
    sorted_hunks = sorted(hunks, key=lambda x: x[0])
    merged = [sorted_hunks[0]]
    
    for current in sorted_hunks[1:]:
        last = merged[-1]
        
        if current[0] - last[1] <= max_gap:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    
    return merged


def add_editable_region_markers(file_record, context_before, context_after, max_gap):
    """Add editable region markers, splitting into chunks if needed"""
    patch = file_record.get('patch')
    before_content = file_record.get('before_content')
    after_content = file_record.get('after_content')
    
    if not patch or not before_content:
        file_record['chunk_id'] = 0
        file_record['total_chunks_in_file'] = 1
        file_record['is_multi_chunk_file'] = False
        file_record['model_input_text'] = None
        file_record['model_target_text'] = None
        return [file_record]
    
    hunks = parse_patch_hunks(patch)
    
    if not hunks:
        file_record['chunk_id'] = 0
        file_record['total_chunks_in_file'] = 1
        file_record['is_multi_chunk_file'] = False
        file_record['model_input_text'] = None
        file_record['model_target_text'] = None
        return [file_record]
    
    merged_hunks = merge_close_hunks(hunks, max_gap)
    
    before_lines = before_content.split('\n')
    after_lines = after_content.split('\n') if after_content else before_lines
    
    chunk_records = []
    
    for chunk_idx, (hunk_start, hunk_end) in enumerate(merged_hunks):
        chunk_record = file_record.copy()
        
        region_start = max(1, hunk_start - context_before)
        region_end = min(len(before_lines), hunk_end + context_after)
        
        marked_lines = []
        for i, line in enumerate(before_lines, start=1):
            if i == region_start:
                marked_lines.append('<|editable_region_start|>')
            marked_lines.append(line)
            if i == region_end:
                marked_lines.append('<|editable_region_end|>')
        
        model_input_text = '\n'.join(marked_lines)
        
        model_target_text = None
        if region_start <= len(after_lines) and region_end <= len(after_lines):
            target_lines = after_lines[region_start-1:region_end]
            model_target_text = '\n'.join(target_lines)
        
        chunk_record['chunk_id'] = chunk_idx
        chunk_record['total_chunks_in_file'] = len(merged_hunks)
        chunk_record['is_multi_chunk_file'] = len(merged_hunks) > 1
        chunk_record['editable_region_start'] = region_start
        chunk_record['editable_region_end'] = region_end
        chunk_record['model_input_text'] = model_input_text
        chunk_record['model_target_text'] = model_target_text
        
        chunk_records.append(chunk_record)
    
    return chunk_records


def add_markers_to_dataset(file_records, context_before, context_after, max_gap):
    """Process all records to add markers"""
    logger.info(f"Adding editable region markers to {len(file_records)} records...")
    
    all_chunks = []
    processed = 0
    skipped = 0
    
    for record in file_records:
        chunk_records = add_editable_region_markers(record, context_before, context_after, max_gap)
        
        for chunk in chunk_records:
            if chunk.get('model_input_text'):
                processed += 1
            else:
                skipped += 1
            
            all_chunks.append(chunk)
    
    logger.info(f"Processed {processed} chunks, skipped {skipped}")
    return all_chunks


def save_to_json(data, filename):
    """Save data to JSON file"""
    # Convert datetime objects
    for record in data:
        if isinstance(record.get('commit_date'), datetime):
            record['commit_date'] = record['commit_date'].isoformat()
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(data)} records to {filename}")


def process_repository(repo_name, token, args, output_dir):
    """Process a single repository"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing repository: {repo_name}")
    logger.info(f"{'='*60}")
    
    try:
        # Connect to repo
        repo = connect_to_repo(repo_name, token)
        if not repo:
            return None
        
        # Filter commits
        filtered = filter_commits(repo, args.min_files, args.max_files)
        if not filtered:
            logger.warning(f"No commits found matching criteria for {repo_name}")
            return None
        
        # Extract file-level data
        file_records = extract_file_level_data(repo, filtered)
        
        # Add markers and split chunks
        chunks = add_markers_to_dataset(
            file_records,
            args.context_before,
            args.context_after,
            args.max_gap
        )
        
        # Save individual repo dataset
        safe_name = repo_name.replace('/', '_')
        output_file = output_dir / f"{safe_name}_dataset.json"
        save_to_json(chunks, output_file)
        
        return {
            'repo_name': repo_name,
            'total_commits': len(list(repo.get_commits())),
            'filtered_commits': len(filtered),
            'file_records': len(file_records),
            'chunks': len(chunks),
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error processing {repo_name}: {e}")
        return {
            'repo_name': repo_name,
            'success': False,
            'error': str(e)
        }


def main():
    """Main execution function"""
    # Parse arguments
    args = parse_arguments()
    
    # Enter your GitHub token here
    token = ""
    # token = os.getenv('GITHUB_TOKEN')
    if not token:
        logger.error("GITHUB_TOKEN environment variable not set!")
        logger.error("Set it with: export GITHUB_TOKEN='your_token_here'")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # Load repositories
    repos = load_repositories(args.repos)
    logger.info(f"Processing {len(repos)} repositories")
    
    # Process each repository
    results = []
    all_data = []
    
    for repo_name in repos:
        result = process_repository(repo_name, token, args, output_dir)
        if result:
            results.append(result)
            
            # Load data for combined file
            if result.get('success'):
                safe_name = repo_name.replace('/', '_')
                try:
                    with open(output_dir / f"{safe_name}_dataset.json", 'r') as f:
                        repo_data = json.load(f)
                        all_data.extend(repo_data)
                except Exception as e:
                    logger.error(f"Could not load data for {repo_name}: {e}")
    
    # Save combined dataset
    if all_data:
        combined_file = output_dir / "combined_dataset.json"
        save_to_json(all_data, combined_file)
    
    # Generate summary
    summary_file = output_dir / "summary.txt"
    with open(summary_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write("EXTRACTION SUMMARY\n")
        f.write("="*60 + "\n\n")
        
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        f.write(f"Total repositories: {len(repos)}\n")
        f.write(f"Successful: {len(successful)}\n")
        f.write(f"Failed: {len(failed)}\n\n")
        
        if successful:
            f.write("Per-repository statistics:\n")
            f.write("-"*60 + "\n")
            for r in successful:
                f.write(f"\n{r['repo_name']}:\n")
                f.write(f"  Total commits: {r['total_commits']}\n")
                f.write(f"  Filtered commits: {r['filtered_commits']}\n")
                f.write(f"  File records: {r['file_records']}\n")
                f.write(f"  Chunks created: {r['chunks']}\n")
        
        if failed:
            f.write("\nFailed repositories:\n")
            f.write("-"*60 + "\n")
            for r in failed:
                f.write(f"{r['repo_name']}: {r.get('error', 'Unknown error')}\n")
        
        f.write(f"\nTotal training examples: {len(all_data)}\n")
    
    logger.info(f"\n{'='*60}")
    logger.info("EXTRACTION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total training examples: {len(all_data)}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Summary: {summary_file}")


if __name__ == "__main__":
    main()

# How to run the script

# Run with multiple repos directly:

    # python extract_dataset.py \
    # --repos "user/repo1" "user/repo2" "org/repo3" \
    # --output-dir "./datasets"


# Or use a repos list file:

# python extract_dataset.py \
#     --repos repos.txt \
#     --output-dir "./datasets"