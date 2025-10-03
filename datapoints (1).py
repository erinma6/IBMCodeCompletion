import argparse
import requests
import json
import os
from urllib.parse import urlparse

EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".rb": "Ruby",
    ".go": "Go",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP"
}

def get_file_extension_language(file_path):
    _, ext = os.path.splitext(file_path)
    return EXTENSION_TO_LANGUAGE.get(ext)

def get_inserted_lines_from_patch(patch):
    inserted = []
    for line in patch.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            inserted.append(line[1:])
    return inserted

def fetch_base_file_raw_url(repo, base_sha, file_path):
    return f"https://raw.githubusercontent.com/{repo}/{base_sha}/{file_path}"

def extract_pr_number(pr_url):
    parsed = urlparse(pr_url)
    parts = parsed.path.strip("/").split("/")
    return parts[-1]

def fetch_pr_metadata(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def fetch_pr_files(repo, pr_number):
    files = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files?page={page}&per_page=100"
        r = requests.get(url)
        r.raise_for_status()
        page_files = r.json()
        if not page_files:
            break
        files.extend(page_files)
        page += 1
    return files

def main(args):
    pr_number = extract_pr_number(args.pr_url)
    print(f"\n Fetching PR metadata for: {args.pr_url}")
    pr_data = fetch_pr_metadata(args.repo, pr_number)
    base_sha = pr_data["base"]["sha"]
    print(f"Base commit SHA: {base_sha}\n")

    files = fetch_pr_files(args.repo, pr_number)
    datapoints = []

    for file in files:
        path = file["filename"]
        status = file["status"]
        patch = file.get("patch")
        print(f"Processing file: {path} | Status: {status}")
        if not patch:
            print("No patch data available")
            continue

        inserted_lines = get_inserted_lines_from_patch(patch)
        if len(inserted_lines) < args.min_lines:
            print(f"Only {len(inserted_lines)} inserted lines — skipping")
            continue

        language = get_file_extension_language(path)
        if not language:
            print(f"Unknown language for file: {path}")
            continue

        raw_url = fetch_base_file_raw_url(args.repo, base_sha, path)
        base_resp = requests.get(raw_url)
        if base_resp.status_code != 200:
            print(f"Could not fetch base file: {raw_url}")
            continue

        base_content = base_resp.text

        datapoint = {
            "repo": args.repo,
            "pr_url": args.pr_url,
            "file_path": path,
            "language": language,
            "task_type": "code_completion",
            "input": base_content,
            "output": "\n".join(inserted_lines),
            "metadata": {
                "insert_position": "append_inside_class_body",
                "lines_added": len(inserted_lines)
            }
        }
        datapoints.append(datapoint)
        print(f"Added {len(inserted_lines)} inserted lines | Language: {language}")
    lengthDataPoints = len(datapoints)
    if datapoints:
        output_lower = args.output.lower()
        if output_lower.endswith(".json"):
            with open(args.output, "w") as f:
                json.dump(datapoints, f, indent=2, ensure_ascii=False)
                f.write("\n")
        else:
            with open(args.output, "a") as f:
                for dp in datapoints:
                    f.write(json.dumps(dp, ensure_ascii=False) + "\n")
        print(f"\n Done. Wrote {lengthDataPoints} datapoints to {args.output}")
    else:
        print("No usable datapoints found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr_url", required=True)
    parser.add_argument("--output", default="dataset.jsonl")
    parser.add_argument("--min_lines", type=int, default=3)
    args = parser.parse_args()
    main(args)
