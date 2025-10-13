import os
import sys
import json
import argparse
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import re
from pydriller import Repository
import shutil

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
        description='Extract dataset from GitHub repositories using local git (PyDriller)'
    )
    
    # Required arguments
    parser.add_argument(
        '--repos',
        nargs='+',
        required=True,
        help='Repository URLs or names (user/repo format) or path to file with repo list'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory to save output files'
    )
    
    # Optional arguments with defaults
    parser.add_argument(
        '--clone-dir',
        default='./repo_clones',
        help='Directory to clone repositories (default: ./repo_clones)'
    )
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
        '--max-commits',
        type=int,
        default=None,
        help='Maximum commits to process per repo (default: None = all)'
    )
    parser.add_argument(
        '--since',
        type=str,
        default=None,
        help='Only process commits after this date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--until',
        type=str,
        default=None,
        help='Only process commits before this date (YYYY-MM-DD)'
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
    parser.add_argument(
        '--keep-clones',
        action='store_true',
        help='Keep cloned repositories after processing'
    )
    
    return parser.parse_args()


def load_repositories(repos_input):
    """Load repository list from input"""
    if len(repos_input) == 1 and os.path.isfile(repos_input[0]):
        logger.info(f"Loading repositories from file: {repos_input[0]}")
        with open(repos_input[0], 'r') as f:
            repos = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return repos
    else:
        return repos_input


def clone_repository(repo_identifier, clone_dir, token=None):
    """
    Clone a repository locally
    
    Args:
        repo_identifier: Either 'user/repo' or full URL
        clone_dir: Directory to clone into
        token: GitHub token for authentication (optional)
        
    Returns:
        Path to cloned repository or None if failed
    """
    # Convert user/repo to URL if needed
    if '/' in repo_identifier and not repo_identifier.startswith('http'):
        if token:
            repo_url = f"https://{token}@github.com/{repo_identifier}.git"
        else:
            repo_url = f"https://github.com/{repo_identifier}.git"
        repo_name = repo_identifier.replace('/', '_')
    else:
        repo_url = repo_identifier
        repo_name = repo_identifier.split('/')[-1].replace('.git', '')
    
    clone_path = Path(clone_dir) / repo_name
    
    # Check if already cloned
    if clone_path.exists():
        logger.info(f"Repository already exists at {clone_path}, using existing clone")
        return clone_path
    
    logger.info(f"Cloning {repo_identifier} to {clone_path}")
    
    try:
        # Use shallow clone to save time and space
        subprocess.run(
            ['git', 'clone', '--depth', '1000', repo_url, str(clone_path)],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Successfully cloned {repo_identifier}")
        return clone_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone {repo_identifier}: {e.stderr}")
        return None


def is_text_file(filename):
    """Check if file is likely a text file"""
    text_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb', '.rs',
        '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.swift', '.kt', '.scala',
        '.r', '.R', '.m', '.mm', '.dart', '.lua', '.pl', '.sh', '.bash',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        '.md', '.txt', '.html', '.css', '.scss', '.sass', '.less',
        '.sql', '.graphql', '.proto', '.thrift'
    }
    return any(filename.endswith(ext) for ext in text_extensions)


def process_repository_with_pydriller(repo_path, args):
    """
    Process repository using PyDriller
    
    Args:
        repo_path: Path to cloned repository
        args: Command line arguments
        
    Returns:
        List of file-level records
    """
    logger.info(f"Processing repository with PyDriller: {repo_path}")
    
    file_records = []
    processed_commits = 0
    
    # Parse date arguments
    since = datetime.strptime(args.since, '%Y-%m-%d') if args.since else None
    until = datetime.strptime(args.until, '%Y-%m-%d') if args.until else None
    
    try:
        # Traverse commits with PyDriller
        for commit in Repository(
            path_to_repo=str(repo_path),
            since=since,
            to=until
        ).traverse_commits():
            
            # Skip merge commits
            if len(commit.parents) > 1:
                continue
            
            # Filter by file count
            num_files = len(commit.modified_files)
            if num_files < args.min_files or num_files > args.max_files:
                continue
            
            # Process this commit
            processed_commits += 1
            
            for file_index, modified_file in enumerate(commit.modified_files, start=1):
                # Skip non-text files
                if not modified_file.filename or not is_text_file(modified_file.filename):
                    continue
                
                # Skip files with no content
                if modified_file.change_type.name == 'DELETE':
                    change_type = 'removed'
                elif modified_file.change_type.name == 'ADD':
                    change_type = 'added'
                elif modified_file.change_type.name == 'RENAME':
                    change_type = 'renamed'
                else:
                    change_type = 'modified'
                
                # Get file contents
                before_content = modified_file.source_code_before or ""
                after_content = modified_file.source_code or ""
                patch = modified_file.diff or ""
                
                # Get file path
                file_path = modified_file.new_path or modified_file.old_path or modified_file.filename
                file_extension = file_path.split('.')[-1] if '.' in file_path else ''
                
                # Create record
                record = {
                    'commit_sha': commit.hash,
                    'commit_short_sha': commit.hash[:8],
                    'commit_message': commit.msg.strip(),
                    'commit_author': commit.author.name,
                    'commit_date': commit.author_date,
                    'total_files_in_commit': num_files,
                    'sequence_order': file_index,
                    'file_path': file_path,
                    'file_extension': file_extension,
                    'change_type': change_type,
                    'lines_added': modified_file.added_lines,
                    'lines_deleted': modified_file.deleted_lines,
                    'total_changes': modified_file.added_lines + modified_file.deleted_lines,
                    'before_content': before_content,
                    'after_content': after_content,
                    'patch': patch,
                    'editable_region_start': None,
                    'editable_region_end': None,
                    'change_labels': None
                }
                
                file_records.append(record)
            
            # Check max commits limit
            if args.max_commits and processed_commits >= args.max_commits:
                logger.info(f"Reached max commits limit ({args.max_commits})")
                break
        
        logger.info(f"Processed {processed_commits} commits, extracted {len(file_records)} file records")
        return file_records
        
    except Exception as e:
        logger.error(f"Error processing repository: {e}")
        return []


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
    for record in data:
        if isinstance(record.get('commit_date'), datetime):
            record['commit_date'] = record['commit_date'].isoformat()
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(data)} records to {filename}")


def process_single_repository(repo_identifier, args, output_dir, clone_dir, token):
    """Process a single repository"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing repository: {repo_identifier}")
    logger.info(f"{'='*60}")
    
    try:
        # Clone repository
        repo_path = clone_repository(repo_identifier, clone_dir, token)
        if not repo_path:
            return None
        
        # Extract data using PyDriller
        file_records = process_repository_with_pydriller(repo_path, args)
        
        if not file_records:
            logger.warning(f"No records extracted from {repo_identifier}")
            return None
        
        # Add markers and split chunks
        chunks = add_markers_to_dataset(
            file_records,
            args.context_before,
            args.context_after,
            args.max_gap
        )
        
        # Save individual repo dataset
        safe_name = repo_identifier.replace('/', '_').replace('.git', '')
        output_file = output_dir / f"{safe_name}_dataset.json"
        save_to_json(chunks, output_file)
        
        return {
            'repo_name': repo_identifier,
            'file_records': len(file_records),
            'chunks': len(chunks),
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error processing {repo_identifier}: {e}")
        return {
            'repo_name': repo_identifier,
            'success': False,
            'error': str(e)
        }


def main():
    """Main execution function"""
    args = parse_arguments()
    
    # Add GitHub token
    token = " "
    # token = os.getenv('GITHUB_TOKEN')
    if not token:
        logger.warning("GITHUB_TOKEN not set. Only public repositories will be accessible.")
    
    # Create directories
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    clone_dir = Path(args.clone_dir)
    clone_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Clone directory: {clone_dir}")
    
    # Load repositories
    repos = load_repositories(args.repos)
    logger.info(f"Processing {len(repos)} repositories")
    
    # Process each repository
    results = []
    all_data = []
    
    for repo_identifier in repos:
        result = process_single_repository(repo_identifier, args, output_dir, clone_dir, token)
        if result:
            results.append(result)
            
            # Load data for combined file
            if result.get('success'):
                safe_name = repo_identifier.replace('/', '_').replace('.git', '')
                try:
                    with open(output_dir / f"{safe_name}_dataset.json", 'r') as f:
                        repo_data = json.load(f)
                        all_data.extend(repo_data)
                except Exception as e:
                    logger.error(f"Could not load data for {repo_identifier}: {e}")
    
    # Save combined dataset
    if all_data:
        combined_file = output_dir / "combined_dataset.json"
        save_to_json(all_data, combined_file)
    
    # Clean up clones if requested
    if not args.keep_clones:
        logger.info(f"Cleaning up cloned repositories from {clone_dir}")
        try:
            shutil.rmtree(clone_dir)
        except Exception as e:
            logger.warning(f"Could not remove clone directory: {e}")
    
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





    # python local_extract.py  --repos "alibaba/spring-ai-alibaba" --output-dir "./datasets"