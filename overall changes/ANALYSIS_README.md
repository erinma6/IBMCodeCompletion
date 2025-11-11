# Dataset Analysis: Next Action Prediction Patterns

## Overview

This directory contains comprehensive analysis of the `combined_dataset.json` file to identify patterns for **next action prediction** in code completion scenarios.

### Analysis Results
- **Dataset Size:** 5,781 code changes across 1,016 commits
- **File Types:** 16 unique extensions
- **Change Types:** 4 types (modified, added, renamed, removed)
- **Analysis Date:** November 2025

---

## 📄 Key Documents

### 1. **QUICK_SUMMARY.txt** ⭐ START HERE
A visual, easy-to-read summary of the main findings with:
- Dataset composition
- Top prediction patterns
- Actionable rules
- Expected performance estimates

**Best for:** Quick overview and high-level insights

### 2. **PATTERN_FINDINGS.md** 📊 DETAILED REPORT
Comprehensive 13-section analysis including:
- Complete statistics and distributions
- High-confidence prediction patterns
- Within-commit pattern analysis
- Actionable prediction rules
- Implementation recommendations

**Best for:** Understanding full context and building models

### 3. **analysis_results.txt**
Raw output from the complete dataset analysis script showing all patterns and transitions.

**Best for:** Reference data and verification

---

## 🎯 Key Findings at a Glance

### Pattern 1: File Type Clustering (Strongest)
```
After .java    → .java  (90% confidence) ⭐⭐⭐
After .yaml    → .yaml  (81% confidence) ⭐⭐⭐
After .tsx     → .tsx   (72% confidence) ⭐⭐⭐
After .js      → .js    (73% confidence) ⭐⭐⭐
```
**Implication:** Developers work on one file type at a time

### Pattern 2: Change Type Momentum (Very Strong)
```
After modified → modified (92% confidence) ⭐⭐⭐⭐
After renamed  → renamed  (62% confidence) ⭐⭐⭐
After added    → added    (52% confidence) ⭐⭐
```
**Implication:** Operations cluster by type (mass modifications, then additions, etc.)

### Pattern 3: Cross-Type Relationships
```
After .xml → .java (54% confidence)  Configuration/Implementation pairing
After .md  → .java (25% confidence)  Documentation/Implementation
```
**Implication:** Specific file types are frequently paired

### Pattern 4: Commit Context Boost
```
.java within same commit → .java (95.3% vs 89.8% overall) [+5.5%]
.js within same commit   → .js   (91.7% vs 72.5% overall) [+19.2%]
```
**Implication:** Within-commit context significantly increases prediction accuracy

---

## 🔍 Analysis Scripts

### `analyze_full.py` (RECOMMENDED)
Complete analysis of the entire dataset with:
- File extension distributions
- Change type sequences
- Within-commit patterns
- Code change size analysis
- Predictive rules extraction

```bash
python3 analyze_full.py
```

### `extract_patterns.py`
Alternative extraction script with streaming parser for large files.

### `pattern_analysis.py`
Original analysis script with comprehensive statistics.

---

## 📈 Prediction Accuracy Expectations

### With Simple Markov Model
- **Overall Accuracy:** 75-80%
- **Within-commit Accuracy:** 85-90%
- **Top-5 Predictions:** 95%+

### With Enhanced Model (+ commit context + directory)
- **Overall Accuracy:** 80-85%
- **Top-5 Predictions:** 97%+

---

## 🛠️ Implementation Guide

### Step 1: Build State Space
States = (file_extension, change_type, commit_context)

### Step 2: Create Transition Matrix
Use empirical probabilities from patterns above:
- `java → java: 0.898`
- `modified → modified: 0.922`
- `xml → java: 0.535`

### Step 3: Implement Prediction
```python
def predict_next_action(current_ext, current_change, in_same_commit):
    if in_same_commit:
        # Use within-commit probabilities (more accurate)
        return within_commit_transitions[(current_ext, current_change)]
    else:
        # Use global probabilities
        return global_transitions[(current_ext, current_change)]
```

### Step 4: Add Fallback Strategy
1. Try exact (file_type + change_type) prediction
2. Fall back to file_type patterns only
3. Fall back to change_type patterns only
4. Default to "modified" (92% baseline)

### Step 5: Handle Edge Cases
- Rare file types (.py, .sql): Use directory-based heuristics
- Very large changes (>200 lines): May be refactoring, lower predictability
- Unknown context: Use prior probabilities

---

## 📊 Data Distribution Summary

| Metric | Value |
|--------|-------|
| Java files | 4,220 (73.0%) |
| XML files | 490 (8.5%) |
| Other files | 1,071 (18.5%) |
| Modifications | 4,925 (85.2%) |
| Additions | 649 (11.2%) |
| Renames | 111 (1.9%) |
| Deletions | 96 (1.7%) |
| Median lines per change | 20 |
| P95 lines per change | 300 |

---

## 💡 Insights for Model Development

### High-Value Features
1. **File extension** (highest signal)
2. **Change type** (second highest)
3. **Commit context** (binary boost)
4. **File size** (relative)
5. **Directory** (secondary)

### Implementation Priority
1. **MUST:** File type + change type transition matrix
2. **SHOULD:** Commit context tracking
3. **COULD:** Directory-based heuristics
4. **NICE:** Author patterns, temporal patterns

### Performance Optimization
- Pre-compute all transition matrices
- Cache within-commit histories
- Use lazy loading for rare file types
- Implement top-5 ranking (not just top-1)

---

## 📌 Common Patterns by Language

### Backend (Java, XML, Config)
- Java → Java → Java (cluster)
- XML → Java (config follows code)
- Primarily modifications (85%+)
- Large commits (5-6 files average)

### Frontend (TSX, JS, CSS)
- TSX → TSX or TS (cohesive)
- JS → JS or HTML (linked)
- Similar modification patterns
- Smaller clusters than backend

### Configuration
- YAML → YAML (config clusters)
- YML/YAML often mixed with Java

### Documentation
- MD → MD or Java (docs near code)
- Rarer than code changes

---

## 🚀 Next Steps

1. **Review QUICK_SUMMARY.txt** for high-level patterns
2. **Read PATTERN_FINDINGS.md** for detailed implementation guidance
3. **Run analyze_full.py** to verify on your system
4. **Implement prediction model** using the rules and probabilities
5. **Evaluate accuracy** on held-out test commits
6. **Iterate** with community feedback

---

## 📝 Technical Notes

### Dataset Characteristics
- **Source:** IBM Code Completion project commits
- **Language:** Primarily Java + Spring Framework
- **Project Types:** Java library + AI/ML components
- **Size:** ~150MB JSON file with streaming parser

### Analysis Methodology
- Markov chain analysis of commit sequences
- Empirical transition probability calculation
- Within-commit context analysis
- Directory and size distribution analysis

### Limitations
- Analysis is retrospective (past behavior)
- Assumes similar future workflows
- Limited to 4 change types
- Java-heavy bias

---

## 📧 Questions & Notes

For questions or improvements:
1. Check if answer exists in PATTERN_FINDINGS.md (section 1-13)
2. Review the analysis scripts for implementation details
3. Experiment with analyze_full.py on custom data

---

**Last Updated:** November 2025
**Dataset:** combined_dataset.json (5,781 items)
**Analysis Status:** ✅ Complete and verified

