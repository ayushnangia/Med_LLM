# Clinical Integration of HAI-DEF Models in Uro-Oncological Decision-Making

MedGemma Impact Challenge 2026 — Main Track + Edge AI Prize

## Team

- **Radu Alexa** — Board-Certified Uro-Oncologist. Clinical lead, domain expert, sole reviewer of 1,242 AI outputs.
- **Ayush Nangia** — AI Researcher. Model pipeline, web application, infrastructure, data engineering.
- **Aman Gokrani** — AI Researcher, ex-Microsoft Health AI. Judge system, evaluation framework, statistical analysis.

## Overview

This project evaluates whether MedGemma can serve as both a **therapy recommendation engine** and an **automated quality evaluator** for German renal cell carcinoma (RCC) cases — validated against expert physician judgment.

We deploy MedGemma 27B in two roles across 69 anonymized RCC cases from German tumor boards:

1. **Therapy Predictor** — generates guideline-concordant therapy recommendations from structured clinical data
2. **Structured Medical Judge** — evaluates predictions across semantic match, clinical appropriateness, and reasoning quality

## Key Results

| Metric | MedGemma 27B |
|--------|-------------|
| Clinically Acceptable | **75.4%** |
| Exact Therapy Match | **46.4%** |
| Doctor Quality Score | **6.1/9** |
| Judge Cohen's Kappa (vs Doctor) | **0.675** |
| Judge F1 Score | **0.873** |
| Self-Judging Bias | **p=0.017** (significant) |

- **Best predictor** among 6 models tested (MedGemma 27B, Gemma 3 27B, Gemma 3 4B, OLMo 32B Instruct, OLMo 32B Think, Meditron3 7B)
- **Best judge** with substantial agreement (kappa=0.675) against board-certified uro-oncologist
- **Key discovery:** statistically significant self-judging bias when MedGemma evaluates its own predictions

## Three-Tier Evaluation Pipeline

1. **Tier 1 — LLM Prediction:** 6 models generate therapy recommendations from structured clinical JSON (414 total predictions)
2. **Tier 2 — AI Judge:** GPT-5.2 and MedGemma 27B independently score each prediction (828 judge evaluations)
3. **Tier 3 — Expert Validation:** Board-certified uro-oncologist reviews all model predictions AND all judge evaluations (1,242 reviews, 100% coverage)

## Links

- **Live Demo:** [medical-review-site.vercel.app](https://medical-review-site.vercel.app)
- **Evaluation Report:** [`findings/evaluation_report_2026-02-18.md`](findings/evaluation_report_2026-02-18.md)

## Repository Structure

```
Med_LLM/
├── scripts/                    # Python scripts
│   ├── modal_treatment_predict.py  # Modal vLLM inference (main predictor)
│   ├── modal_judge.py              # Modal vLLM judge evaluation
│   ├── evaluate_treatment_llm_judge.py  # Statistical analysis
│   ├── generate_evaluation_report.py    # DOCX report generation
│   ├── create_summary_report.py         # Summary metrics report
│   └── ...                              # Classification, conversion, validation
├── converted_data/             # Converted clinical data (JSON, CSV)
├── results/                    # Experiment results by provider
│   ├── modal_treatment/        # Modal vLLM treatment predictions
│   ├── modal_judge/            # Modal vLLM judge evaluations
│   └── openrouter/             # OpenRouter API results
├── findings/                   # Reports and analysis
│   ├── evaluation_report_*.md  # Comprehensive evaluation report
│   └── SUMMARY_REPORT.md       # Model comparison summary
└── documentation/              # Project documentation
```

## Reproducing Results

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or: pip install python-docx openpyxl pandas requests scikit-learn matplotlib seaborn python-pptx
```

#### Environment variables

```bash
cp .env.example .env
# Edit .env and add your keys:
#   OPENROUTER_API_KEY=sk-or-v1-...    (for OpenRouter inference)
#   HF_TOKEN=hf_...                     (for gated models on Modal)
```

### Inference (requires Modal account)

```bash
# Treatment predictions via Modal vLLM on H100 GPUs
modal run scripts/modal_treatment_predict.py

# Judge evaluations
modal run scripts/modal_judge.py
```

Reproducibility is handled automatically inside the Modal scripts:
- `seed=42` for deterministic sampling
- `VLLM_BATCH_INVARIANT=1` for batch-size-independent outputs
- `CUBLAS_WORKSPACE_CONFIG=:4096:8` for deterministic CUDA operations

### Evaluation

```bash
# Generate statistical analysis and report
python scripts/evaluate_treatment_llm_judge.py
python scripts/create_summary_report.py
```

## Infrastructure

- **Inference:** [Modal](https://modal.com) vLLM on NVIDIA H100 GPUs
- **Structured output:** Pydantic schema enforcement via vLLM grammar-guided generation
- **Reproducibility:** Deterministic seed (42), fixed temperature (0.3 standard / 0.6 thinking models), [vLLM batch invariance](https://docs.vllm.ai/en/latest/features/batch_invariance/) (`VLLM_BATCH_INVARIANT=1`) — outputs are identical regardless of concurrent batch size, eliminating GPU kernel non-determinism
- **Web application:** Next.js, Supabase PostgreSQL, deployed on Vercel
- **Language:** All prompts, cases, and evaluations in German medical terminology

## License

This project contains anonymized clinical data. All patient data has been de-identified in accordance with German data protection regulations.
