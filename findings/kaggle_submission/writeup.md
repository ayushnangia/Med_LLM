# MedGemma Impact Challenge — Writeup

**Tracks:** Main Track + Novel Task Prize

---

## Project Name

**Clinical integration of HAI-DEF Models in uro-oncological decision-making**

---

## Your Team

- **Radu Alexa** — Board-Certified Uro-Oncologist. Clinical lead, domain expert, sole reviewer of 1,242 AI outputs.
- **Ayush Nangia** — AI Researcher. Model pipeline, web application, infrastructure, data engineering.
- **Aman Gokrani** — AI Researcher, ex-Microsoft Health AI. Judge system, evaluation framework, statistical analysis.

---

## Problem Statement

Tumor boards (Tumordiskussionen) are the cornerstone of cancer treatment planning in Germany. Over 500 certified cancer centers hold weekly multidisciplinary meetings where specialists review complex cases and agree on therapy recommendations. Preparation is time-intensive: clinicians must compile patient data, cross-reference national guidelines (IMDC-stratified treatment algorithms), and draft recommendations — all in German medical terminology.

This process is error-prone. Staging typos, guideline drift, and documentation inconsistencies affect quality. Yet there is no validated AI assistant for German-language clinical oncology. Medical AI benchmarks overwhelmingly use English data, and existing tools do not address the structured decision-making required for tumor board preparation.

**Our goal:** Evaluate whether MedGemma can serve as both a therapy recommendation engine and an automated quality evaluator for German renal cell carcinoma (RCC) cases — validated against expert physician judgment.

**Dataset:** 69 anonymized RCC cases from German tumor boards, structured per NCC guidelines. Each case includes demographics, ECOG/Karnofsky scores, TNM staging, IMDC risk factors, histology, imaging, and prior therapies. Ground truth is the actual tumor board consensus decision.

---

## Overall Solution

### HAI-DEF Model Usage

We deploy MedGemma 27B in two novel roles:

**1. MedGemma as Therapy Predictor**

MedGemma 27B receives structured German clinical cases with embedded IMDC-stratified therapy guidelines and generates therapy recommendations with reasoning. Among 6 models tested (MedGemma 27B, Gemma 3 27B, Gemma 3 4B, OLMo 32B Instruct, OLMo 32B Think, Meditron3 7B), MedGemma 27B achieved the best results:

| Metric | MedGemma 27B | All Models Average |
|--------|-------------|-------------------|
| Clinically Acceptable | **75.4%** | 58.7% |
| Exact Therapy Match | **46.4%** | 30.9% |
| Doctor Quality Score | **6.1/9** | 5.1/9 |
| Automated Judge Score | **0.76/1.0** | 0.66/1.0 |

**2. MedGemma as Structured Medical Judge (Novel Task)**

This is our primary contribution to the Novel Task Prize. We repurpose MedGemma 27B as an automated evaluator — a task it was never trained for. The judge receives each model's prediction alongside the ground truth and scores it across four dimensions using a weighted formula:

```
overall = semantic_match(40%) + clinical_appropriateness(40%) + reasoning_quality(20%)
```

MedGemma as judge achieved **substantial agreement** with our uro-oncologist: Cohen's kappa = 0.675, with 84.5% concordance and an F1 score of 0.873. The uro-oncologist agreed with MedGemma's judge assessments in 85.3% of cases, rating its reasoning quality at 7.2/10.

**3. Bias Discovery**

A critical finding: MedGemma exhibits statistically significant self-judging bias when evaluating its own predictions (Mann-Whitney U, p=0.017), scoring them 0.082 points higher on average (0.777 vs 0.695). This has direct implications for responsible AI deployment — self-evaluation pipelines must account for this bias.

---

## Technical Details

### Infrastructure

- **Inference:** Modal vLLM on NVIDIA H100 GPUs
- **Structured output:** Pydantic schema enforcement via vLLM grammar-guided generation
- **Reproducibility:** Deterministic seed (42), fixed temperature (0.3 standard / 0.6 thinking models), nucleus sampling (top-p 0.95)
- **Web application:** Next.js 16, Supabase PostgreSQL, deployed on Vercel
- **Language:** All prompts, cases, and evaluations in German medical terminology

### Three-Tier Evaluation Pipeline

1. **Tier 1 — LLM Prediction:** 6 models generate therapy recommendations from structured clinical JSON (414 total predictions)
2. **Tier 2 — AI Judge:** GPT-5.2 and MedGemma 27B independently score each prediction (828 judge evaluations)
3. **Tier 3 — Expert Validation:** Board-certified uro-oncologist reviews all model predictions AND all judge evaluations (1,242 reviews, 100% coverage)

### Statistical Validation

| Metric | GPT-5.2 Judge | MedGemma 27B Judge |
|--------|--------------|-------------------|
| Cohen's kappa (vs doctor) | 0.629 | **0.675** |
| Agreement rate | 81.8% | **84.5%** |
| F1 score | 0.845 | **0.873** |
| Doctor agrees with judge | 85.0% | **85.3%** |
| False positive rate | **8.2%** | 9.6% |
| Inter-judge kappa | 0.725 | 0.725 |

### Key Results Summary

- **Best predictor:** MedGemma 27B (75.4% acceptable, 6.1/9 quality)
- **Best judge:** MedGemma 27B (kappa = 0.675, F1 = 0.873)
- **Clinical safety:** Both judges are conservative (overly strict), which is safer clinically. GPT-5.2 has the lowest dangerous false positive rate (8.2%)
- **Self-judging bias:** Statistically significant (p = 0.017) — MedGemma scores its own outputs higher
- **Inter-judge reliability:** kappa = 0.725 (substantial), 86.5% concordance

### Links

- **Live demo:** [medical-review-site.vercel.app](https://medical-review-site.vercel.app)
- **Code repository:** [github.com/ayushnangia/Med_LLM](https://github.com/ayushnangia/Med_LLM)
- **Full evaluation report:** See `findings/evaluation_report_2026-02-18.md` in the repository

---

## Why MedGemma?

MedGemma 27B uniquely excels in both roles we tested. As a predictor, its medical specialization produces more guideline-concordant therapy recommendations than general-purpose models of similar or larger size. As a judge, it demonstrates that medical domain knowledge transfers to evaluation tasks — achieving the highest agreement with our physician expert.

The discovery of self-judging bias (p=0.017) is itself a contribution: it demonstrates that model self-evaluation, while efficient, requires calibration against independent judges. This finding generalizes beyond our specific use case to any pipeline where LLMs evaluate their own outputs.

Our work validates MedGemma for German clinical oncology — an underserved language in medical AI — using real patient data and rigorous expert evaluation, not synthetic benchmarks.
