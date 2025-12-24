# AI Model Evaluation: Medical Cancer Classification

## Executive Summary

We tested **14 AI models** on their ability to classify German medical oncology cases
into the correct cancer type. The cases come from real tumor board discussions.

### Key Findings

- **Best Performing Model:** MiMo v2 (Free)
- **Top Accuracy:** 100.0%
- **Cases Tested:** 26 per model
- **Cancer Types:** 7 categories (5 urological + multiple cancers + non-urological)

---

## Model Rankings

| Rank | Model | Accuracy | Avg Response Time |
|------|-------|----------|-------------------|
| 1 🥇 | MiMo v2 (Free) | 100.0% | 1.54s |
| 2 🥈 | Kimi K2 | 96.2% | 5.62s |
| 3 🥉 | Gemini 3 Pro | 96.2% | 2.68s |
| 4  | Claude Opus 4.5 | 96.2% | 1.71s |
| 5  | GPT-5.2 | 96.2% | 0.73s |
| 6  | DeepSeek v3.2 | 96.2% | 4.17s |
| 7  | Gemma 3 (12B) | 92.3% | 0.79s |
| 8  | Gemma 3n (E4B) | 92.3% | 0.80s |
| 9  | OLMo 3.1 (Free) | 92.3% | 10.88s |
| 10  | Gemini 3 Flash | 92.3% | 0.86s |
| 11  | Gemma 3 (27B) | 92.3% | 1.50s |
| 12  | Gemma 3 (4B) | 84.6% | 0.80s |
| 13  | Nemotron 3 (Free) | 80.8% | 4.63s |
| 14  | RNJ-1 | 73.1% | 0.67s |


---

## What This Means

### For Clinical Use

The top-performing models achieve **over 90% accuracy**, which is promising for
clinical decision support. However, this is an initial benchmark and further validation
with larger datasets and clinical review is essential before any real-world deployment.

### Cancer Types Tested

| German Term | English | Description |
|-------------|---------|-------------|
| Nierenzellkarzinom | Kidney Cancer | Renal cell carcinoma |
| Prostatakarzinom | Prostate Cancer | Adenocarcinoma of the prostate |
| Hodentumor | Testicular Cancer | Germ cell and other testicular tumors |
| Peniskarzinom | Penile Cancer | Squamous cell carcinoma of the penis |
| Urothelkarzinom | Bladder Cancer | Transitional cell carcinoma |
| Polymalignancy | Multiple Cancers | Patients with more than one cancer type |
| Non-Urological | Non-Urological | Cancers outside the urological system |

---

## Visualizations

1. **accuracy_comparison.png** - Model accuracy ranking
2. **confusion_matrix.png** - Detailed classification results
3. **speed_vs_accuracy.png** - Speed vs accuracy trade-off
4. **category_accuracy.png** - Accuracy by cancer type

---

## Methodology

- **Dataset:** 26 German medical oncology cases
- **Source:** Anonymized tumor board discussions
- **Task:** Classify each case into one of 7 cancer categories
- **Models:** Tested via OpenRouter API (commercial LLM providers)
- **Date:** December 2025

---

*Report generated automatically from classification experiments.*
