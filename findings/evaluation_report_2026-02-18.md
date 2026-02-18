# Evaluation Report

**Doctor vs AI Judges in Medical Oncology — Therapy Recommendation Assessment**

> February 2026 | Renal Cell Carcinoma (RCC) — 69 Cases from German Tumor Boards
>
> Prepared for Google AI Hackathon 2026
>
> Reviewer: Dr. Radu Alexa, Board-Certified Oncologist

---

## 1. Executive Summary

This report presents a novel three-tier evaluation pipeline for assessing AI-generated therapy recommendations in clinical oncology. Across 414 predictions from 6 LLMs on 69 renal cell carcinoma (Nierenzellkarzinom, RCC) cases from German tumor boards (Tumordiskussionen), the pipeline combines automated AI judging with expert physician validation to establish a scalable, reproducible evaluation framework.

Through iterative pipeline refinement between January and February 2026, the average clinically acceptable therapy rate improved from 25% to 100% (+75 pp), and exact match rate from 21% to 0% (+-21 pp).

### Key Findings

- Across all 414 predictions: **64%** metastatic detection accuracy, **31%** exact therapy match, **59%** clinically acceptable therapies.
- **Best model by doctor review:** MedGemma 27B (6.1/9 quality, 75% acceptable).
- **Best model by automated judge score:** MedGemma 27B (avg overall 0.76/1.0).
- GPT-5.2 shows **substantial agreement** with the doctor (Cohen's κ = 0.629).
- MedGemma 27B shows **substantial agreement** with the doctor (Cohen's κ = 0.675).
- **Inter-judge agreement:** κ = 0.725, 86% concordance across 414 evaluation pairs.
- **MedGemma self-judging bias:** higher scores for own predictions (0.78 vs 0.69), significant (p=0.017).
- **Clinical safety:** GPT-5.2 has lowest dangerous error rate (8.2% false positives).

---

## 2. Project Overview

This project investigates whether large language models (LLMs) can support clinical decision-making in oncology by generating appropriate therapy recommendations for renal cell carcinoma (RCC) patients presented at German tumor board discussions.

### Clinical Context

Tumor boards (Tumordiskussionen) are multidisciplinary meetings where specialists review complex cancer cases and agree on treatment recommendations. Each case includes patient demographics, comorbidities, TNM staging, histological subtype, prior therapies, and imaging findings. The ground truth for this study is the consensus therapy recommendation from the tumor board.

### Project Scope: Two Evaluation Pipelines

| Pipeline | Task | Models Tested | Best Result | Status |
| --- | --- | --- | --- | --- |
| 1. Classification | 7-class cancer type detection | 14 models | 100% accuracy (MiMo v2 Flash) | Complete |
| 2. Treatment Prediction | RCC therapy recommendation | 6 models | See detailed results below | Complete + Validated |

Pipeline 1 established that modern LLMs can reliably classify German oncology cases by cancer type. **This report focuses exclusively on Pipeline 2** (treatment prediction), which is the clinically more challenging task requiring guideline-aware therapeutic reasoning.

### Evaluation Pipeline (Treatment Prediction)

The study uses a **three-tier evaluation pipeline:**

1. **Tier 1 — LLM Prediction:** Each model receives the full clinical case and generates a therapy recommendation with reasoning.
2. **Tier 2 — AI Judge Evaluation:** Two AI judges (GPT-5.2 and MedGemma 27B) independently score each prediction on semantic match, clinical appropriateness, reasoning quality, and overall correctness.
3. **Tier 3 — Doctor Validation:** A board-certified oncologist blindly reviews model predictions and judge evaluations.

### Models Evaluated

| Model | Type | Description |
| --- | --- | --- |
| Meditron3 7B | Medical | Medical-specialized 7B model based on Qwen2.5 |
| OLMo 32B Instruct | General | Allen AI's open 32B instruction-tuned model |
| OLMo 32B Think | General | Allen AI's 32B chain-of-thought reasoning model |
| Gemma 3 27B | General | Google's general-purpose 27B instruction-tuned model |
| Gemma 3 4B | General | Google's compact 4B instruction-tuned model |
| MedGemma 27B | Medical | Google's medical-specialized 27B model (also used as AI judge) |

---

## 3. Technical Innovation & Impact

This project introduces a comprehensive, reproducible evaluation methodology for clinical AI that addresses key challenges in deploying LLMs for medical decision support.

### Three-Tier Evaluation Pipeline

Unlike single-layer evaluations (model vs. ground truth), this project implements a three-tier pipeline that separates automated scoring from expert validation:

- **Tier 1 — LLM Prediction:** Six models with diverse architectures (2B–32B parameters, general-purpose and medical-specialized) generate therapy recommendations from structured German clinical case data.
- **Tier 2 — AI Judge Evaluation:** Two independent AI judges score each prediction across four dimensions: semantic match, clinical appropriateness, reasoning quality, and overall correctness.
- **Tier 3 — Physician Validation:** A board-certified oncologist blindly reviews both model predictions and judge evaluations, creating a ground truth for evaluating the evaluators themselves.

### Multi-Schema Data Handling

The clinical dataset spans **four distinct JSON schema variants** across the 69 cases:

| Schema | Cases | Structure | Key Differences |
| --- | --- | --- | --- |
| v1.1 Standard | 1–14, 36–61 | Top-level patient, entitäten | Nested performance_status, separate cTNM/pTNM |
| v1.0 Template | 15–35, 67–69 | Wrapped in case_template | Flat ECOG, single TNM field, different IMDC path |
| case-de | 62–63 | case.patient, case.diagnose | mRCC schema with therapieplan |
| diagnosen | 64–66 | diagnosen[], tumor_history | Array-based diagnosis, geplantes_vorgehen |

A critical bug affecting cases 15–35 (missing ECOG/Karnofsky due to changed schema paths) was identified and fixed between the January and February evaluation rounds.

### Medical Review Web Platform

A purpose-built Next.js web application enables structured physician review of AI predictions and judge evaluations. The platform supports blinded review workflows, Likert-scale and binary ratings, and exports data to Supabase for statistical analysis.

### Inference Infrastructure

| Aspect | Modal (Primary) | OpenRouter (Validation) |
| --- | --- | --- |
| Hardware | NVIDIA H100 80GB | Cloud API |
| Framework | vLLM (batched) | Sequential API |
| JSON Handling | vLLM structured output | Manual regex parsing |
| Reproducibility | Seed=42, deterministic | Non-deterministic |
| Speed (69 cases) | ~3 minutes | ~15 minutes |
| Cost per run | ~$0.10 | ~$0.40 |

### Scalability & Impact

- **Cancer type expansion:** Pipeline is cancer-agnostic — same framework applies to prostate, urothelial, testicular, and non-urological cancers.
- **Language adaptability:** German-language evaluation demonstrates LLM capability beyond English, relevant for non-English healthcare systems.
- **Open-source potential:** Three-tier methodology, review platform, and evaluation scripts designed for reproducibility.

---

## 4. Methodology

### Treatment Prediction Prompt

Each model receives a structured German-language prompt with the role "Du bist ein erfahrener Onkologe, spezialisiert auf Nierenzellkarzinom" (You are an experienced oncologist specialized in RCC). The prompt contains:

- **Patient demographics:** name, age, ECOG, Karnofsky, comorbidity, life expectancy
- **Clinical data:** diagnosis, TNM staging (clinical + pathological), histology subtype, grading
- **Medical history:** anamnesis, secondary diagnoses, medication, imaging, IMDC risk factors, ICI eligibility, prior systemic therapies
- **Embedded therapy guidelines:** Complete IMDC-stratified treatment algorithm for metastatic clear-cell RCC and non-metastatic RCC with GoR A/B/0
- **Structured output:** JSON with is_metastatic, IMDC risk, therapy, category, reasoning, and confidence

### Inference Hyperparameters

| Parameter | Standard Models | Thinking Models | Rationale |
| --- | --- | --- | --- |
| Temperature | 0.3 | 0.6 | Low for deterministic medical output; higher for thinking chains |
| Top-p | 0.95 | 0.95 | Nucleus sampling for balanced diversity |
| Max tokens | 32,768 | 65,536 | Headroom for reasoning; thinking models consume tokens before JSON |
| Seed | 42 (Modal only) | 42 | Deterministic results for reproducibility |
| Structured output | Yes (Pydantic) | No | Thinking models produce `<think>` blocks before JSON |

### LLM-as-Judge Evaluation

Two AI judges independently evaluate each prediction using a structured German prompt with the role "Du bist ein erfahrener Uro-Onkologe, der als Gutachter für KI-generierte Therapieempfehlungen fungiert."

**Judge Scoring Formula:**

```
overall_score = (semantic_score × 0.4) + (clinical_score × 0.4) + (reasoning_quality × 0.2)
```

| Dimension | Weight | Scale | Criteria |
| --- | --- | --- | --- |
| Semantic Match | 40% | 0–1 | Same drug=1.0, same class=0.5–0.7, different=0–0.3 |
| Clinical Appropriateness | 40% | 0–1 | First-choice=0.9–1.0, acceptable alternative=0.6–0.8 |
| Reasoning Quality | 20% | 0–1 | Complete and correct=0.8–1.0, errors=0–0.4 |

### Physician Validation Protocol

| Review Type | Target | Metrics | Scale |
| --- | --- | --- | --- |
| Model Review | LLM prediction | Therapy acceptable, exact match, patient-oriented, quality | Boolean, 0–100, 0–100, 0–9 |
| Judge Review | AI judge evaluation | Judge correct, reasoning quality, comment | Agree/Partial/Disagree, 0–10, free text |

---

## 5. Patient Cohort

The dataset comprises **69 anonymized RCC cases** from German tumor board discussions. All patient names are pseudonymized.

![Patient Demographics](charts/demographics.png)

| Characteristic | Value |
| --- | --- |
| Total cases | 69 |
| Age range | 43–82 years |
| Age mean / median | 67 / 67 years |
| Metastatic | 36 (52%) |
| Localized | 33 (48%) |
| Clear cell (ccRCC) | 12 |
| Non-clear cell | 3 |
| Histology not specified | 54 |

---

## 6. Study Design & Data Overview

| Component | Count | Details |
| --- | --- | --- |
| RCC Cases | 69 | Anonymized from German tumor boards |
| LLM Models | 6 | Gemma 3 27B, Gemma 3 4B, MedGemma 27B, Meditron3 7B, OLMo 32B Instruct, OLMo 32B Think |
| AI Judges | 2 | GPT-5.2, MedGemma 27B |
| Total Predictions | 414 | 69 cases × 6 models |
| Judge Evaluations | 828 | 69 cases × 6 models × 2 judges |
| Doctor Model Reviews | 414 | 69 cases × 6 models |
| Doctor Judge Reviews | 828 | 69 cases × 6 models × 2 judges |

---

## 7. Model Performance — Automated Evaluation

All 414 predictions across 69 cases were evaluated by both AI judges.

![Model Performance](charts/full_model_performance.png)

| Model | Cases | Met. Detect. | Exact Match | Judge Acc. | Avg Score |
| --- | --- | --- | --- | --- | --- |
| MedGemma 27B | 69 | 6522% | 4638% | 6522% | 0.76 |
| OLMo 32B Think | 69 | 6522% | 3333% | 6232% | 0.72 |
| Gemma 3 27B | 69 | 6522% | 3623% | 5942% | 0.71 |
| OLMo 32B Instruct | 69 | 6377% | 3043% | 5362% | 0.68 |
| Gemma 3 4B | 69 | 5942% | 2899% | 4348% | 0.57 |
| Meditron3 7B | 69 | 6232% | 1014% | 4203% | 0.51 |

Overall: **64%** metastatic detection accuracy, **31%** exact therapy match, **59%** clinically acceptable.

### Detailed Judge Scores

| Model | Semantic | Clinical | Reasoning | Overall |
| --- | --- | --- | --- | --- |
| MedGemma 27B | 0.75 | 0.81 | 0.64 | 0.76 |
| OLMo 32B Think | 0.69 | 0.79 | 0.61 | 0.72 |
| Gemma 3 27B | 0.70 | 0.79 | 0.60 | 0.71 |
| OLMo 32B Instruct | 0.67 | 0.75 | 0.58 | 0.68 |
| Gemma 3 4B | 0.59 | 0.62 | 0.44 | 0.57 |
| Meditron3 7B | 0.51 | 0.56 | 0.39 | 0.51 |

---

## 8. Performance Across Evaluation Rounds

The evaluation pipeline was run twice: **January 2026** (initial, 35 cases) and **February 2026** (expanded to 69 cases, improved prompts, fixed data extraction).

![Run Comparison](charts/run_comparison.png)

| Model | Jan Exact % | Feb Exact % | Jan Accept % | Feb Accept % |
| --- | --- | --- | --- | --- |
| Meditron3 7B | 9% | 0% | 26% | 100% |
| OLMo 32B Instruct | 14% | 0% | 20% | 100% |
| OLMo 32B Think | 23% | 0% | 23% | 100% |
| Gemma 3 27B | 29% | 0% | 31% | 100% |
| Gemma 3 4B | 17% | 0% | 20% | 100% |
| MedGemma 27B | 37% | 0% | 31% | 100% |

**Average improvement:** +-21 pp exact match, +75 pp clinically acceptable. Key drivers: improved prompt engineering, fixed ECOG/Karnofsky extraction for v1.0 cases, increased max_tokens for thinking models.

---

## 9. Therapy Category Analysis

![Therapy Categories](charts/therapy_categories.png)

| Therapy Category | Count | % of Predictions |
| --- | --- | --- |
| IO + TKI | 165 | 40% |
| TKI Mono | 136 | 33% |
| Surgery | 69 | 17% |
| Other | 16 | 4% |
| TKI + mTOR | 10 | 2% |
| Surveillance | 9 | 2% |
| IO Mono | 8 | 2% |
| IO + IO | 1 | 0% |

---

## 10. Model Performance — Doctor Review

Dr. Alexa reviewed **414 model predictions** across 69 cases in a blinded fashion.

![Acceptability](charts/model_acceptability.png)

![Quality](charts/model_quality.png)

| Model | Cases | Acceptable % | Avg Exact Match | Avg Patient-Oriented | Avg Quality (0–9) |
| --- | --- | --- | --- | --- | --- |
| MedGemma 27B | 69 | 75% | 64 | 63 | 6.1 |
| Gemma 3 27B | 69 | 75% | 62 | 62 | 5.8 |
| OLMo 32B Instruct | 69 | 64% | 50 | 51 | 5.5 |
| OLMo 32B Think | 69 | 69% | 54 | 54 | 5.3 |
| Meditron3 7B | 69 | 49% | 41 | 41 | 4.2 |
| Gemma 3 4B | 69 | 48% | 40 | 40 | 3.9 |

---

## 11. Case Studies

### Case Study A: Model Consensus — Correct Prediction

**Case ncc_37:** 69-year-old patient, ECOG 1, metastatic . Diagnosis: Metastasiertes Nierenzellkarzinom (mRCC) mit Progress unter 1. Linie (Pembrolizumab + Axitinib).

**Tumor Board Recommendation:** Start 2. Linie Cabozantinib; Monitoring: Blutdruck/Proteinurie, Leberwerte, TSH; Re-Staging nach 8–12 Wochen.

| Model | Predicted Category | Exact Match | Acceptable |
| --- | --- | --- | --- |
| Meditron3 7B | IO+TKI | No | Yes |
| OLMo 32B Instruct | Biopsie → IO+IO/TKI | Yes | Yes |
| OLMo 32B Think | TKI mono | Yes | Yes |
| Gemma 3 27B | TKI mono | Yes | Yes |
| Gemma 3 4B | TKI | Yes | Yes |
| MedGemma 27B | TKI mono | Yes | Yes |

All or most models agreed on the correct therapy category, demonstrating reliable LLM performance for well-defined clinical scenarios.

### Case Study B: Model Disagreement

**Case ncc_32:** 62-year-old patient, ECOG 1, localized . Diagnosis: Metastasiertes RCC (ED 12.06.2023), 1. Linie Cabozantinib (2023–2025); CT 10.12.2025 mit Lokalrezidiv in Nephrektomie-Loge links (OP-Status angenommen) und peritonealer Metastasierung; keine pulmonalen/ossären Metastasen im CT..

**Tumor Board Recommendation:** Start 2. Linie (z. B. IO-basierte Kombination oder alternative Sequenz je nach Vorbehandlung und Nierenfunktion). Monitoring: Nierenwerte, Blutdruck, Proteinurie, klinische Symptomkontrolle.

| Model | Predicted Category | Exact Match | Acceptable |
| --- | --- | --- | --- |
| Meditron3 7B | IO+TKI | No | No |
| OLMo 32B Instruct | TKI mono / IO | Yes | No |
| OLMo 32B Think | IO | No | No |
| Gemma 3 27B | IO mono | No | No |
| Gemma 3 4B | TKI | No | No |
| MedGemma 27B | TKI mono | No | No |

Models predicted **6 different therapy categories**, highlighting clinical ambiguity.

### Case Study C: Doctor–Judge Divergence

**Case ncc_1:** 52-year-old patient, ECOG 0, metastatic papillär. Diagnosis: Metastasiertes papilläres RCC.

**Tumor Board Recommendation:** Einleitung palliative Systemtherapie TKI/IO (z.B. Nivolumab/Cabozantinib).

| Model | Predicted Category | Exact Match | Acceptable |
| --- | --- | --- | --- |
| Meditron3 7B | Surgery | No | No |
| OLMo 32B Instruct | TKI mono | No | Yes |
| OLMo 32B Think | TKI mono | No | Yes |
| Gemma 3 27B | TKI mono | Yes | Yes |
| Gemma 3 4B | IO+TKI | No | Yes |
| MedGemma 27B | TKI mono | Yes | Yes |

The physician rated the therapy as acceptable, but both AI judges classified it as incorrect — illustrating how strict semantic matching may reject clinically valid alternatives.

---

## 12. Judge Score Distributions

![Score Distributions](charts/score_distributions.png)

![Score Types](charts/score_types.png)

| Judge | Score Type | Mean | Median | Std Dev | Min | Max |
| --- | --- | --- | --- | --- | --- | --- |
| GPT-5.2 | Semantic | 0.651 | 0.820 | 0.317 | 0.00 | 1.00 |
| GPT-5.2 | Clinical | 0.722 | 0.835 | 0.237 | 0.10 | 0.95 |
| GPT-5.2 | Reasoning | 0.545 | 0.600 | 0.182 | 0.10 | 0.88 |
| GPT-5.2 | Overall | 0.658 | 0.760 | 0.248 | 0.08 | 0.96 |
| MedGemma 27B | Semantic | 0.671 | 0.900 | 0.362 | 0.00 | 1.00 |
| MedGemma 27B | Clinical | 0.798 | 0.900 | 0.227 | 0.00 | 1.00 |
| MedGemma 27B | Reasoning | 0.712 | 0.700 | 0.145 | 0.10 | 0.90 |
| MedGemma 27B | Overall | 0.708 | 0.810 | 0.218 | 0.07 | 0.98 |

---

## 13. Agreement: Doctor vs AI Judge

![Confusion Matrices](charts/confusion_matrices.png)

| Metric | GPT-5.2 | MedGemma 27B |
| --- | --- | --- |
| N pairs | 407 | 407 |
| Cohen's κ | 0.629 | 0.675 |
| Agreement Rate | 81.8% | 84.5% |
| Sensitivity | 0.782 | 0.844 |
| Specificity | 0.880 | 0.847 |
| Precision | 0.918 | 0.904 |
| F1 Score | 0.845 | 0.873 |

**GPT-5.2:** κ = 0.629 (substantial agreement), Sensitivity = 78.2%, Specificity = 88.0%.
**MedGemma 27B:** κ = 0.675 (substantial agreement), Sensitivity = 84.4%, Specificity = 84.7%.

---

## 14. Score Correlations

![Scatter Correlations](charts/scatter_correlations.png)

| Comparison | GPT-5.2 | MedGemma 27B |
| --- | --- | --- |
| Overall Score vs Quality (ρ) | 0.722 | 0.661 |
|   p-value | 0.0000 | 0.0000 |
| Overall Score vs Exact Match (ρ) | 0.766 | 0.694 |
|   p-value | 0.0000 | 0.0000 |
| N pairs | 414 | 414 |

---

## 15. Doctor's Direct Rating of AI Judges

![Judge Ratings](charts/judge_ratings.png)

| Metric | GPT-5.2 | MedGemma 27B |
| --- | --- | --- |
| Total Reviews | 414 | 414 |
| Agree | 352 (85%) | 353 (85%) |
| Partial | 4 (1%) | 24 (6%) |
| Disagree | 58 (14%) | 37 (9%) |
| Avg Reasoning Quality | 7.1/10 | 7.2/10 |

---

## 16. Per-Model Judge Accuracy

![Per-Model Accuracy](charts/per_model_accuracy.png)

---

## 17. Inter-Judge Agreement

Agreement between GPT-5.2 and MedGemma 27B across 414 evaluation pairs (69 cases × 6 models).

![Inter-Judge](charts/inter_judge.png)

**Cohen's κ = 0.725** (substantial agreement). Overall concordance: 86.5%.

---

## 18. MedGemma Self-Judging Bias

MedGemma serves dual roles: both as a predictive model and as a judge.

![MedGemma Bias](charts/medgemma_bias.png)

| Metric | Self-Judging | Judging Others |
| --- | --- | --- |
| N evaluations | 69 | 345 |
| Mean Overall Score | 0.777 | 0.695 |
| Median Overall Score | 0.850 | 0.780 |

**Mann-Whitney U test:** U = 14062, p = 0.0170 (statistically significant). MedGemma gives higher scores to its own predictions by 0.082 points on average.

---

## 19. Clinical Safety Analysis

- **False Positive (dangerous):** Judge approves a prediction the doctor rejects → could lead to inappropriate treatment.
- **False Negative (overly strict):** Judge rejects a prediction the doctor approves → could prevent appropriate treatment.

| Safety Metric | GPT-5.2 | MedGemma 27B |
| --- | --- | --- |
| Total Pairs | 407 | 407 |
| Judge Approvals | 219 | 240 |
| Judge Rejections | 188 | 167 |
| False Positives (dangerous) | 18 (8.2%) | 23 (9.6%) |
| False Negatives (overly strict) | 56 (29.8%) | 40 (24.0%) |

---

## 20. Summary Comparison: GPT-5.2 vs MedGemma 27B

| Metric | GPT-5.2 | MedGemma 27B |
| --- | --- | --- |
| Cohen's κ (vs Doctor) | 0.629 | 0.675 |
| Agreement Rate | 81.8% | 84.5% |
| F1 Score | 0.845 | 0.873 |
| Doctor Agree % | 85% | 85% |
| Avg Reasoning Quality | 7.1/10 | 7.2/10 |
| False Positive Rate | 8.2% | 9.6% |
| Avg Overall Score | 0.658 | 0.708 |
| Avg Clinical Score | 0.722 | 0.798 |

---

## 21. German–English Medical Glossary

| German Term | English Translation | Context |
| --- | --- | --- |
| Nierenzellkarzinom (NCC/RCC) | Renal Cell Carcinoma | Primary cancer type in this study |
| Tumordiskussion / Tumorboard | Tumor Board Discussion | Multidisciplinary case conference |
| Systemtherapie | Systemic Therapy | Drug-based treatment (chemo, IO, TKI) |
| Klarzellig (ccRCC) | Clear Cell | Most common RCC histological subtype |
| Metastasiert | Metastatic | Cancer spread beyond primary organ |
| Lokalisiert | Localized | Cancer confined to primary organ |
| Nephrektomie | Nephrectomy | Surgical removal of kidney |
| Erstlinientherapie | First-line Therapy | Initial treatment regimen |
| Zweitlinientherapie | Second-line Therapy | Treatment after first-line failure |
| Lebenserwartung | Life Expectancy | Estimated patient survival |
| Nebendiagnosen | Comorbidities | Co-existing medical conditions |
| Bildgebung | Imaging | Radiological examinations (CT, MRI) |
| Histologie-Subtyp | Histology Subtype | Microscopic tissue classification |
| Leitlinienkonform | Guideline-Concordant | Consistent with clinical practice guidelines |

---

## 22. Conclusions & Recommendations

### Key Findings

- **Model Performance:** MedGemma 27B achieved the highest doctor-rated quality (6.1/9) with 75% therapy acceptability. MedGemma 27B scored highest on automated judge evaluation (0.76/1.0).
- **Best AI Judge:** MedGemma 27B showed the strongest agreement with the doctor (κ = 0.675).
- **Therapy Categories:** IO+TKI and TKI Mono dominate model predictions, consistent with current RCC guidelines for the 36/69 metastatic cases.
- **Clinical Safety:** GPT-5.2 has the lowest dangerous error rate (8.2%). Both judges tend to be overly strict, which is safer in a clinical context.
- **Self-Judging Bias:** MedGemma shows statistically significant self-judging bias. Self-evaluations should be interpreted with caution.

### Recommendations

1. AI judges should be used as **screening tools**, not final arbiters. Doctor review remains essential for clinical safety.
2. Using **both GPT-5.2 and MedGemma** as judges and flagging disagreements could improve evaluation reliability.
3. Models with high acceptability but lower exact match may still provide clinically valid alternative recommendations.
4. Strong Spearman correlations (ρ > 0.64) suggest automated judge scores are useful proxies for prediction quality, enabling scalable evaluation.
5. Future work should expand to additional cancer types, test with multiple physician reviewers, and evaluate newer medical-specialized models.

### Limitations

- Single physician reviewer (potential individual assessment bias)
- Dataset limited to RCC from a single institution's tumor boards
- Doctor reviewed all 69 cases for both model and judge evaluation (complete coverage)
- Ground truth = tumor board consensus (not necessarily the only correct therapy)
- All cases use German medical terminology, which may affect model performance

### Open Questions

- **Ground Truth Definition:** Is `ground_truth_therapy` the tumor board consensus or the actual treatment administered?
- **IMDC for Non-Clear-Cell RCC:** Should IMDC be skipped entirely or calculated with disclaimer for papillary/chromophobe subtypes?
- **ICI Eligibility:** Criteria for determining ICI combination feasibility (autoimmune disease, prior transplant) are not explicitly coded.
- **Therapy Guidelines Completeness:** Embedded guidelines may not include adjuvant pembrolizumab, non-clear-cell protocols, third-line options, oligometastatic management, or cytoreductive nephrectomy criteria.
- **Four JSON Schema Variants:** Edge cases in field mapping across four schema variants may introduce subtle data quality issues.
