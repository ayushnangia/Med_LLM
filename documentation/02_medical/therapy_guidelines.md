# Therapy Guidelines

Complete therapy guidelines as embedded in the LLM prompt.

---

## Overview

The prompt contains two therapy algorithms:
1. **Metastatic Clear-Cell RCC** - IMDC-based systemic therapy
2. **Non-Metastatic RCC** - Surgical/local therapy

---

## Metastatic Clear-Cell RCC Algorithm

### IMDC Risk Stratification

**Risk Categories:**
| Category | Risk Factors |
|----------|--------------|
| Favorable (Günstig) | 0 risk factors |
| Intermediate (Intermediär) | 1-2 risk factors |
| Unfavorable (Ungünstig) | ≥3 risk factors |

**Risk Factors:**
1. Karnofsky performance status <80%
2. Time from diagnosis to systemic therapy <1 year
3. Hemoglobin below lower limit of normal
4. Corrected calcium above upper limit of normal
5. Neutrophils above upper limit of normal
6. Platelets above upper limit of normal

### First-Line Therapy (ICI Combination Possible)

| Risk | Therapies | Strength |
|------|-----------|----------|
| **Favorable** | Nivolumab+Cabozantinib | A |
| | Pembrolizumab+Axitinib | A |
| | Pembrolizumab+Lenvatinib | A |
| | Avelumab+Axitinib | B |
| **Intermediate** | Nivolumab+Cabozantinib | A |
| | Nivolumab+Ipilimumab | A |
| | Pembrolizumab+Axitinib | A |
| | Pembrolizumab+Lenvatinib | A |
| **Unfavorable** | Nivolumab+Cabozantinib | A |
| | Nivolumab+Ipilimumab | A |
| | Pembrolizumab+Axitinib | A |
| | Pembrolizumab+Lenvatinib | A |

### First-Line Therapy (ICI NOT Possible)

| Risk | Therapies | Strength |
|------|-----------|----------|
| **Favorable** | Pazopanib | A |
| | Sunitinib | A |
| | Tivozanib | A |
| | Bevacizumab+Interferon | A |
| **Intermediate** | Cabozantinib | B |
| | Pazopanib | B |
| | Sunitinib | B |
| **Unfavorable** | Cabozantinib | B |
| | Sunitinib | B |
| | Temsirolimus | 0 |

### Second-Line Therapy

**After ICI Combination:**
| Therapy | Strength |
|---------|----------|
| Cabozantinib | A |
| Lenvatinib+Everolimus | A |
| Sunitinib | A |

**After VEGF/R Monotherapy:**
| Therapy | Strength |
|---------|----------|
| Cabozantinib | A |
| Nivolumab | A |

### Recommendation Strength Legend

| Code | Meaning (German) | Meaning (English) |
|------|------------------|-------------------|
| A | Starke Empfehlung | Strong recommendation |
| B | Schwache Empfehlung | Weak recommendation |
| 0 | Option | Option |

---

## Non-Metastatic RCC Algorithm

### Treatment Options by Indication

#### 1. Active Surveillance (GoR 0)

**Indications:**
- Small renal tumors (typically <3-4cm)
- High comorbidity
- Limited life expectancy

**Requirements:**
- Biopsy BEFORE surveillance

#### 2. Ablation (GoR 0)

**Types:**
- Cryoablation
- Radiofrequency ablation (RFA)

**Indications:**
- Small renal tumors
- High comorbidity
- Limited life expectancy

**Requirements:**
- Biopsy BEFORE ablation

#### 3. Partial Nephrectomy (Nephron-sparing Surgery)

**cT1 tumors (≤7cm):**
- SHOULD be performed (GoR A)

**>T1 tumors:**
- SHOULD be considered if technically possible (GoR B)

**Approaches:**
- Open
- Laparoscopic
- Robotic

#### 4. Radical Nephrectomy

**Indication:**
- When partial resection not possible (GoR A)

**Approach:**
- Minimally invasive when local findings allow (GoR A)

### Perioperative Principles

| Principle | Recommendation |
|-----------|----------------|
| Adrenalectomy | NO if imaging unremarkable (GoR A) |
| Systematic lymphadenectomy | NO if imaging unremarkable (GoR A) |
| Lymphadenectomy | Acceptable for enlarged lymph nodes |

### TNM Staging Reference

| Stage | Definition |
|-------|------------|
| T1a | ≤4cm, confined to kidney |
| T1b | >4-7cm, confined to kidney |
| T2a | >7-10cm, confined to kidney |
| T2b | >10cm, confined to kidney |
| T3 | Extension into major veins or perinephric tissue |
| T4 | Beyond Gerota's fascia |

---

## Non-Clear-Cell RCC Note

> **Important:** The guidelines apply primarily to **clear-cell RCC**.
>
> For **non-clear-cell RCC** (papillary, chromophobe, etc.):
> - TKI monotherapy is often preferred
> - IMDC risk stratification is NOT validated
> - Consider clinical trials

---

## Drug Abbreviations

| Abbreviation | Full Name | Class |
|--------------|-----------|-------|
| NIVO | Nivolumab | PD-1 inhibitor (ICI) |
| PEMBRO | Pembrolizumab | PD-1 inhibitor (ICI) |
| IPI | Ipilimumab | CTLA-4 inhibitor (ICI) |
| AVELU | Avelumab | PD-L1 inhibitor (ICI) |
| CABO | Cabozantinib | TKI (VEGFR, MET, AXL) |
| AXI | Axitinib | TKI (VEGFR) |
| LEN | Lenvatinib | TKI (VEGFR, FGFR) |
| SUN | Sunitinib | TKI (VEGFR, PDGFR) |
| PAZ | Pazopanib | TKI (VEGFR, PDGFR) |
| TIV | Tivozanib | TKI (VEGFR) |
| TEM | Temsirolimus | mTOR inhibitor |
| EVE | Everolimus | mTOR inhibitor |
| BEV | Bevacizumab | VEGF antibody |
| IFN | Interferon | Cytokine |

---

## Source

These guidelines are based on NCC (Nationales Centrum für Tumorerkrankungen) recommendations for renal cell carcinoma, as documented in `therapy_structure_*.docx` files.
