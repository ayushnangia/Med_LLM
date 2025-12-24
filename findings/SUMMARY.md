# Classification Experiment Findings

**Date:** December 24, 2025
**Dataset:** 26 medical oncology cases (German)

---

## Executive Summary

Classification experiments using 6 Ollama models on the Med_LLM dataset. **mistral:7b-instruct** achieved the best results with **88.46% accuracy**.

### Top 3 Models

| Rank | Model | Accuracy | Macro F1 | Avg Time |
|------|-------|----------|----------|----------|
| 1 | **mistral:7b-instruct** | **88.46%** | 0.747 | 4.6s |
| 2 | gemma3:4b | 84.62% | 0.723 | 2.3s |
| 3 | llama3:8b | 76.92% | 0.688 | 4.8s |

---

## All Model Results

| Model | Size | Accuracy | Macro F1 | Time/Case | Notes |
|-------|------|----------|----------|-----------|-------|
| **mistral:7b-instruct** | 7B | **88.46%** | 0.747 | 4.6s | Best performer |
| gemma3:4b | 4B | 84.62% | 0.723 | 2.3s | Fastest, excellent accuracy |
| llama3:8b | 8B | 76.92% | 0.688 | 4.8s | Good balance |
| qwen3:latest (8B) | 8B | 69.23% | 0.541 | 32.6s | Slow, uses thinking tags |
| qwen3:0.6b | 0.6B | 3.85% | 0.018 | 4.2s | Too small |
| qwen3:4b | 4B | 0.00% | 0.000 | 19.9s | Doesn't follow format |

---

## Key Findings

### 1. Model Architecture Matters More Than Size

- **mistral:7b** (7B) outperformed **qwen3:latest** (8B) by 19%
- **gemma3:4b** (4B) outperformed **llama3:8b** (8B) by 8%
- Smaller, well-tuned models beat larger ones

### 2. Qwen3 "Thinking" Mode Issue

Qwen3 models use `<think>` tags for reasoning, which:
- Consumes tokens before giving answers
- Makes responses slower (20-35s vs 2-5s)
- Sometimes doesn't output classification at all

### 3. Common Misclassification Patterns

All models struggle with:
- **Polymalignancy (COMBI)**: Always misclassified as single cancer
- **Non-urological**: Often confused with urological cancers

### 4. Best Per-Class Performance

| Class | Best Model | Accuracy |
|-------|------------|----------|
| NCC (Kidney) | mistral | 100% (14/14) |
| PCA (Prostate) | mistral | 100% (2/2) |
| HODEN (Testicular) | mistral | 100% (2/2) |
| PENIS (Penile) | mistral | 100% (2/2) |
| UCA (Urothelial) | mistral | 100% (2/2) |
| COMBI | All fail | 0% |
| NON_URO | gemma3, llama3 | 50% |

---

## Recommendations

### For Production Use

1. **Primary Model:** mistral:7b-instruct (88.46% accuracy)
2. **Fallback/Fast:** gemma3:4b (84.62%, 2x faster)

### To Improve Results

1. **Add COMBI examples** - All models fail on polymalignancy detection
2. **Add NON_URO examples** - Only 50% accuracy
3. **Fine-tune prompt** for polymalignancy detection
4. **Test medical models** (Med42, ClinicalBERT)

### Models Still to Test (on Deep Learning PC)

- gemma3:12b, gemma3:27b
- qwen3:30b
- qwen2.5:14b-instruct
- Medical: Llama3-Med42-8B

---

## Output Files

```
findings/
├── SUMMARY.md                              # This file
├── evaluation_report.md                    # Detailed per-model metrics
├── confusion_matrix_mistral_7b-instruct.png
├── confusion_matrix_gemma3_4b.png
├── confusion_matrix_llama3_8b.png
├── confusion_matrix_qwen3_*.png
└── results_*.json                          # Raw predictions
```

---

## Technical Notes

### Running More Experiments

```bash
source venv/bin/activate

# Test a new model
ollama pull MODEL_NAME
python scripts/classify_cases.py --model MODEL_NAME

# Regenerate reports
python scripts/evaluate_results.py
```

### Available Models

```bash
ollama list
```
