# Data Collection Pipeline

Run these 4 scripts in order to collect and prepare training data.

---

## Prerequisites

```bash
pip install PyGithub
export GITHUB_TOKEN='your_github_token_here'
```

---

## Step 1: Collect Data → `extract_dataset.py`

Extracts commit data from GitHub repositories.

```bash
python extract_dataset.py \
    --repos "apache/kafka" "spring-projects/spring-boot" "alibaba/nacos" \
    --output-dir ./data \
    --min-files 2 \
    --max-files 8
```

**Output:** `data/combined_dataset.json`

---

## Step 2: Filter Data → `analysis/filter_dataset.py`

Filters to small, focused, multi-hunk changes.

```bash
python analysis/filter_dataset.py \
    --input-file data/combined_dataset.json \
    --output-file data/filtered_dataset.jsonl \
    --summary-file data/filtered_dataset_summary.json \
    --max-total-changes 20 \
    --max-files-per-commit 2 \
    --min-chunks-per-file 2
```

**Output:** `data/filtered_dataset.jsonl`

---

## Step 3: Auto-Classify → `analysis/auto_classify.py`

Labels each record by pattern type (import, refactoring, getter_setter, etc).

```bash
python analysis/auto_classify.py
```

**Output:** `data/pattern_labels.jsonl`

---

## Step 4: Create Train/Test Split → `analysis/prepare_training_data.py`

Creates stratified train/val/test splits.

```bash
python analysis/prepare_training_data.py
```

**Output:**
- `data/training/train.jsonl`
- `data/training/val.jsonl`
- `data/training/test.jsonl`

---

## Quick Run (All Steps)

```bash
export GITHUB_TOKEN='your_token'

python extract_dataset.py --repos "apache/kafka" "alibaba/nacos" --output-dir ./data --min-files 2 --max-files 8
python analysis/filter_dataset.py --input-file data/combined_dataset.json --output-file data/filtered_dataset.jsonl --summary-file data/filtered_dataset_summary.json --max-total-changes 20 --max-files-per-commit 2 --min-chunks-per-file 2
python analysis/auto_classify.py
python analysis/prepare_training_data.py
```

---

## Recommended Repos

```
apache/kafka
apache/flink
spring-projects/spring-boot
spring-projects/spring-framework
alibaba/nacos
alibaba/arthas
elastic/elasticsearch
google/guava
apache/dubbo
```

---

## Target: 5,000-10,000 examples

Current: 186 examples (from 1 repo)
Need: ~10-15 repos to reach 5,000+ examples
