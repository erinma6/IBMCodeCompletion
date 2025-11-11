# Next Action Prediction Patterns - Analysis Report

## Executive Summary

Analyzed **5,781 code changes** across **1,016 commits** from the combined_dataset.json to identify predictive patterns for next action prediction in code completion.

### Key Finding
The dataset shows **strong sequential patterns** in both file types and change types, which can be leveraged for accurate next action prediction.

---

## 1. Dataset Overview

| Metric | Value |
|--------|-------|
| Total Code Changes | 5,781 |
| Unique File Extensions | 16 |
| Unique Change Types | 4 |
| Unique Commits | 1,016 |
| Multi-file Commits | 97.2% (988/1,016) |
| Average Files per Commit | 5.69 |

---

## 2. File Extension Distribution

The dataset is heavily dominated by Java files with clear secondary patterns:

| Extension | Count | Percentage |
|-----------|-------|-----------|
| `.java` | 4,220 | 73.0% |
| `.xml` | 490 | 8.5% |
| `.md` | 216 | 3.7% |
| `.tsx` | 181 | 3.1% |
| `.js` | 171 | 3.0% |
| `.yaml` | 132 | 2.3% |
| `.yml` | 100 | 1.7% |
| `.ts` | 81 | 1.4% |
| `.html` | 62 | 1.1% |
| `.json` | 61 | 1.1% |

**Insight:** Backend-heavy codebase (Java/XML dominate), with significant frontend components (TSX/JS).

---

## 3. Change Type Distribution

| Change Type | Count | Percentage |
|-------------|-------|-----------|
| `modified` | 4,925 | 85.2% |
| `added` | 649 | 11.2% |
| `renamed` | 111 | 1.9% |
| `removed` | 96 | 1.7% |

**Insight:** The vast majority of changes are modifications, suggesting an established codebase.

---

## 4. HIGH-CONFIDENCE NEXT FILE TYPE PATTERNS

### 📌 Strong Predictors (>70% Confidence)

These patterns are highly reliable for predicting the next file type:

#### After `.java` files (4,219 transitions)
- **→ .java** (89.8% confidence) ⭐ **PRIMARY PATTERN**
- → .xml (4.9%)
- → .md (1.6%)

**Implication:** When editing Java files, the developer is likely to edit more Java files in the same context.

#### After `.yaml` files (132 transitions)
- **→ .yaml** (81.1% confidence) ⭐
- → .java (9.1%)

#### After `.tsx` files (181 transitions)
- **→ .tsx** (72.4% confidence) ⭐
- → .ts (14.9%)

#### After `.js` files (171 transitions)
- **→ .js** (72.5% confidence) ⭐
- → .java (12.9%)
- → .html (4.7%)

### 📌 Medium-Confidence Patterns (50-70%)

#### After `.md` files (216 transitions)
- **→ .md** (54.2% confidence)
- → .java (24.5%)
- → .xml (14.8%)

#### After `.html` files (62 transitions)
- **→ .html** (50.0% confidence)
- → .js (25.8%)

#### After `.json` files (61 transitions)
- **→ .json** (49.2% confidence)
- → .java (16.4%)
- → .tsx (8.2%)

#### After `.ts` files (81 transitions)
- **→ .ts** (42.0% confidence)
- → .java (22.2%)
- → .tsx (18.5%)

### 📌 Secondary Patterns (Cross-Type)

#### After `.xml` files (490 transitions)
- → .java (53.5% confidence) **Cross-type pattern**
- → .xml (41.2%)

**Implication:** XML files are often paired with Java files (config/implementation relationship).

---

## 5. HIGH-CONFIDENCE NEXT CHANGE TYPE PATTERNS

### 📌 Strong Predictors (>50% Confidence)

#### After `modified` changes (4,924 transitions)
- **→ modified** (92.2% confidence) ⭐ **STRONGEST PATTERN**
- → added (5.9%)
- → removed (1.2%)

**Implication:** Once modifications start, more modifications follow in the same operation.

#### After `renamed` changes (111 transitions)
- **→ renamed** (62.2% confidence) ⭐
- → modified (27.9%)

#### After `removed` changes (96 transitions)
- **→ modified** (58.3% confidence)
- → removed (26.0%)

#### After `added` changes (649 transitions)
- **→ added** (51.5% confidence)
- → modified (45.9%)

**Implication:** Adding files is often followed by either more additions or modifications.

---

## 6. WITHIN-COMMIT PATTERNS

When multiple files are changed in the same commit, predictability is even higher:

### Same-Commit File Type Sequences

#### `.java` files within commit
- → .java (95.3%) **VERY HIGH**
- → .xml (1.8%)
- → .yml (1.0%)

#### `.tsx` files within commit
- → .tsx (77.5%)
- → .ts (16.9%)
- → .css (1.9%)

#### `.js` files within commit
- → .js (91.7%)
- → .html (4.5%)
- → .css (2.3%)

#### `.xml` files within commit
- → .java (51.8%) **Cross-type pattern**
- → .xml (45.7%)

#### `.md` files within commit
- → .md (62.7%)
- → .java (17.4%)
- → .xml (13.0%)

**Key Insight:** Within-commit patterns show HIGHER confidence than overall sequence patterns, indicating that commit context is crucial for prediction.

---

## 7. CODE CHANGE SIZE PATTERNS

Understanding change magnitude helps contextualize next actions:

### Lines Added Distribution
- **Median:** 12 lines
- **75th percentile:** 43 lines
- **95th percentile:** 204 lines
- **Max:** 14,083 lines

### Lines Deleted Distribution
- **Median:** 3 lines
- **75th percentile:** 13 lines
- **95th percentile:** 97 lines
- **Max:** 18,514 lines

### Total Changes Distribution
- **Median:** 20 lines
- **75th percentile:** 64 lines
- **95th percentile:** 300 lines

**Pattern:** Most changes are small (< 50 lines), but occasional large refactorings occur.

---

## 8. DIRECTORY-BASED PATTERNS

Frequently modified directories show consistent change types:

| Directory | Changes | Primary Change Type |
|-----------|---------|-------------------|
| spring-ai-alibaba-graph/core | 141 | modified (135x) |
| community/openmanus/agent | 106 | modified (101x) |
| spring-ai-alibaba-graph/ui | 104 | modified (103x) |
| spring-ai-alibaba-graph/test | 95 | modified (81x) |
| community/openmanus/tool | 90 | modified (88x) |

**Insight:** Core and utility directories are primarily modified, rarely refactored or removed.

---

## 9. ACTIONABLE PREDICTIVE RULES

### Rule 1: File Type Continuation
**Condition:** Current file has extension `.java`
**Prediction:** Next file likely `.java` (90% confidence)
**Use Case:** Can prioritize Java file completions in next action

### Rule 2: Configuration Pattern
**Condition:** After editing `.xml` file
**Prediction:** Next file likely `.java` (54% confidence)
**Use Case:** Configuration/implementation pairing - very common in Spring projects

### Rule 3: Frontend Coherence
**Condition:** After editing `.tsx` file
**Prediction:** Next file likely `.tsx` (72% confidence)
**Alternative:** `.ts` (15% chance) - related TypeScript file
**Use Case:** TypeScript React development shows strong cohesion

### Rule 4: Change Type Momentum
**Condition:** Last action was `modified`
**Prediction:** Next action likely `modified` (92% confidence)
**Use Case:** Single operation often involves multiple file modifications

### Rule 5: Within-Commit Clustering
**Condition:** Inside same commit + after `.java`
**Prediction:** Next file is `.java` (95.3% confidence)
**Use Case:** Commit context increases predictability significantly

### Rule 6: Addition Followed by Modification
**Condition:** File was `added`
**Prediction:** Next action is either `added` (51%) or `modified` (46%)
**Use Case:** New features often require follow-up modifications

---

## 10. RECOMMENDED MODEL APPROACH

### Primary Features for Next Action Prediction

**Rank 1 (Highest Impact):**
- Current file extension
- Current change type
- Commit context (same commit vs. different)

**Rank 2 (High Impact):**
- File directory/project structure
- File change size (small/medium/large)
- Sequence history (last 2-3 actions)

**Rank 3 (Supporting):**
- Time patterns in commits
- Author patterns (if available)
- Semantic file relationships

### Confidence Thresholds

- **Very High (>80%):** `.java`, `.yaml`, `.tsx`, `.js` files
- **High (70-80%):** Change type continuation (`modified` leads to `modified`)
- **Medium (50-70%):** Cross-type transitions (`.xml` → `.java`)
- **Low (<50%):** Rare file types and change types

---

## 11. SAMPLE DATA PATTERNS

### Typical Workflow Example
```
Commit: "update playground example"

1. .ts (modified)        +26 lines - Vaadin integration
2. .tsx (modified)       +3/-4 lines - React component update
3. .tsx (modified)       +3/-4 lines - More component updates
4. .java (modified)      +7/-17 lines - Data model refactor
5. .java (modified)      +11/-13 lines - Booking tools
6. .java (modified)      +11/-11 lines - Support assistant
7. .java (modified)      +13/-18 lines - Booking service
```

**Pattern Observed:**
- Frontend files grouped (.ts, .tsx)
- Backend files grouped (.java)
- Modification is the primary change type
- ~5-6 files per commit

---

## 12. Recommendations for Implementation

### 1. **Use Markov Model Approach**
Build a state-machine where:
- Current state = (file_extension, change_type, commit_context)
- Transition probabilities based on empirical data above
- Confidence scores from relative frequencies

### 2. **Incorporate Commit Context**
- Much higher accuracy when considering within-commit patterns (95%+ for java)
- Fallback to global patterns if not in same commit

### 3. **Implement Fallback Strategy**
1. Try specific file type + change type prediction
2. If low confidence, use file type alone
3. If still low, use change type patterns
4. Default to "modified" (92% prior probability)

### 4. **Handle Edge Cases**
- Rare file types (.py, .sql): High uncertainty, use directory heuristics
- Large changes (>200 lines): May indicate refactoring, less predictable
- Different commits: Lower confidence, but still useful

### 5. **Continuous Learning**
- Retrain on new commits periodically
- Monitor prediction accuracy
- Adjust confidence thresholds based on performance

---

## 13. Conclusion

The dataset reveals **highly predictable patterns** for next action prediction:

✅ **Most Reliable:** File type continuation (90% for Java) and change type momentum (92% for modifications)

✅ **Strong Cross-Patterns:** Configuration/implementation pairing (XML→Java: 54%)

✅ **Context-Dependent:** Within-commit predictions are significantly more accurate than global predictions

✅ **Few Change Types:** Only 4 change types makes prediction feasible

✅ **Bimodal Distribution:** Backend (Java/XML) and frontend (TSX/JS) show independent patterns

**Estimated Prediction Accuracy:** 75-85% achievable with simple models using these patterns.

---

## Files Generated

- `analysis_full.py` - Complete analysis script
- `analysis_results.txt` - Full analysis output
- `PATTERN_FINDINGS.md` - This document

