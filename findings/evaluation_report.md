# Classification Evaluation Report

Generated: 2025-12-24 00:22:09

## Model Comparison

| Model | Accuracy | F1 (macro) | Avg Time (s) |
|-------|----------|------------|--------------|
| gemma3:4b | 84.62% | 0.723 | 2.33 |
| llama3:8b | 76.92% | 0.688 | 4.78 |
| mistral:7b-instruct | 88.46% | 0.747 | 4.61 |
| qwen3:0.6b | 3.85% | 0.018 | 4.16 |
| qwen3:4b | 0.00% | 0.000 | 19.89 |
| qwen3:8b | 42.86% | 0.086 | 37.56 |
| qwen3:latest | 50.00% | 0.467 | 11.49 |
| qwen3:latest | 61.54% | 0.521 | 35.38 |
| qwen3:latest | 69.23% | 0.541 | 32.60 |

## gemma3:4b

- **Total Cases:** 26
- **Accuracy:** 84.62%
- **Macro F1:** 0.723

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.929 | 0.929 | 0.929 | 14 |
| PCA | 0.667 | 1.000 | 0.800 | 2 |
| HODEN | 1.000 | 1.000 | 1.000 | 2 |
| PENIS | 1.000 | 1.000 | 1.000 | 2 |
| UCA | 0.500 | 1.000 | 0.667 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 1.000 | 0.500 | 0.667 | 2 |

### Misclassifications

- **ncc_5** (Muster, Clara): predicted `urothelkarzinom`, actual `nierenzellkarzinom`
- **combi_1** (Draco, Severus): predicted `prostatakarzinom`, actual `polymalignancy`
- **combi_2** (Vega, Orion): predicted `nierenzellkarzinom`, actual `polymalignancy`
- **non_uro_2** (Peter, Dostoyevski): predicted `urothelkarzinom`, actual `non_urological`

## llama3:8b

- **Total Cases:** 26
- **Accuracy:** 76.92%
- **Macro F1:** 0.688

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.917 | 0.786 | 0.846 | 14 |
| PCA | 0.667 | 1.000 | 0.800 | 2 |
| HODEN | 1.000 | 1.000 | 1.000 | 2 |
| PENIS | 1.000 | 1.000 | 1.000 | 2 |
| UCA | 0.333 | 1.000 | 0.500 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 1.000 | 0.500 | 0.667 | 2 |

### Misclassifications

- **ncc_4** (Beispiel, Beta): predicted `urothelkarzinom`, actual `nierenzellkarzinom`
- **ncc_5** (Muster, Clara): predicted `urothelkarzinom`, actual `nierenzellkarzinom`
- **ncc_9** (Muster, Georg): predicted `urothelkarzinom`, actual `nierenzellkarzinom`
- **combi_1** (Draco, Severus): predicted `prostatakarzinom`, actual `polymalignancy`
- **combi_2** (Vega, Orion): predicted `nierenzellkarzinom`, actual `polymalignancy`
- **non_uro_2** (Peter, Dostoyevski): predicted `urothelkarzinom`, actual `non_urological`

## mistral:7b-instruct

- **Total Cases:** 26
- **Accuracy:** 88.46%
- **Macro F1:** 0.747

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.933 | 1.000 | 0.966 | 14 |
| PCA | 0.667 | 1.000 | 0.800 | 2 |
| HODEN | 1.000 | 1.000 | 1.000 | 2 |
| PENIS | 1.000 | 1.000 | 1.000 | 2 |
| UCA | 0.667 | 1.000 | 0.800 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 1.000 | 0.500 | 0.667 | 2 |

### Misclassifications

- **combi_1** (Draco, Severus): predicted `prostatakarzinom`, actual `polymalignancy`
- **combi_2** (Vega, Orion): predicted `nierenzellkarzinom`, actual `polymalignancy`
- **non_uro_2** (Peter, Dostoyevski): predicted `urothelkarzinom`, actual `non_urological`

## qwen3:0.6b

- **Total Cases:** 26
- **Accuracy:** 3.85%
- **Macro F1:** 0.018

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.500 | 0.071 | 0.125 | 14 |
| PCA | 0.000 | 0.000 | 0.000 | 2 |
| HODEN | 0.000 | 0.000 | 0.000 | 2 |
| PENIS | 0.000 | 0.000 | 0.000 | 2 |
| UCA | 0.000 | 0.000 | 0.000 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 0.000 | 0.000 | 0.000 | 2 |

### Misclassifications

- **ncc_2** (Ninja, Son): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_3** (Muster, Alpha): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_4** (Beispiel, Beta): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_5** (Muster, Clara): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_6** (Beispiel, Daniel): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_7** (Muster, Emil): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_8** (Beispiel, Felix): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_9** (Muster, Georg): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_10** (Beispiel, Hanna): predicted `urothelkarzinom`, actual `nierenzellkarzinom`
- **ncc_11** (Muster, Ivan): predicted `urothelkarzinom`, actual `nierenzellkarzinom`
- ... and 15 more

## qwen3:4b

- **Total Cases:** 26
- **Accuracy:** 0.00%
- **Macro F1:** 0.000

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.000 | 0.000 | 0.000 | 14 |
| PCA | 0.000 | 0.000 | 0.000 | 2 |
| HODEN | 0.000 | 0.000 | 0.000 | 2 |
| PENIS | 0.000 | 0.000 | 0.000 | 2 |
| UCA | 0.000 | 0.000 | 0.000 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 0.000 | 0.000 | 0.000 | 2 |

### Misclassifications

- **ncc_1** (Turtle, Ninja): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_2** (Ninja, Son): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_3** (Muster, Alpha): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_4** (Beispiel, Beta): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_5** (Muster, Clara): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_6** (Beispiel, Daniel): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_7** (Muster, Emil): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_8** (Beispiel, Felix): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_9** (Muster, Georg): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_10** (Beispiel, Hanna): predicted `unknown`, actual `nierenzellkarzinom`
- ... and 16 more

## qwen3:8b

- **Total Cases:** 26
- **Accuracy:** 42.86%
- **Macro F1:** 0.086

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 1.000 | 0.429 | 0.600 | 7 |
| PCA | 0.000 | 0.000 | 0.000 | 0 |
| HODEN | 0.000 | 0.000 | 0.000 | 0 |
| PENIS | 0.000 | 0.000 | 0.000 | 0 |
| UCA | 0.000 | 0.000 | 0.000 | 0 |
| COMBI | 0.000 | 0.000 | 0.000 | 0 |
| NON_URO | 0.000 | 0.000 | 0.000 | 0 |

### Misclassifications

- **ncc_1** (Turtle, Ninja): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_4** (Beispiel, Beta): predicted `polymalignancy`, actual `nierenzellkarzinom`
- **ncc_5** (Muster, Clara): predicted `polymalignancy`, actual `nierenzellkarzinom`
- **ncc_6** (Beispiel, Daniel): predicted `unknown`, actual `nierenzellkarzinom`

## qwen3:latest

- **Total Cases:** 26
- **Accuracy:** 50.00%
- **Macro F1:** 0.467

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 1.000 | 0.500 | 0.667 | 14 |
| PCA | 0.667 | 1.000 | 0.800 | 2 |
| HODEN | 0.000 | 0.000 | 0.000 | 2 |
| PENIS | 1.000 | 1.000 | 1.000 | 2 |
| UCA | 0.667 | 1.000 | 0.800 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 0.000 | 0.000 | 0.000 | 2 |

### Misclassifications

- **ncc_1** (Turtle, Ninja): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_3** (Muster, Alpha): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_6** (Beispiel, Daniel): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_7** (Muster, Emil): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_9** (Muster, Georg): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_12** (Beispiel, Julia): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_13** (Muster, Karl): predicted `unknown`, actual `nierenzellkarzinom`
- **hoden_ca_1** (Test, Test1): predicted `unknown`, actual `hodentumor`
- **hoden_ca_2** (Bruno, Brunovici): predicted `unknown`, actual `hodentumor`
- **combi_1** (Draco, Severus): predicted `prostatakarzinom`, actual `polymalignancy`
- ... and 3 more

## qwen3:latest

- **Total Cases:** 26
- **Accuracy:** 61.54%
- **Macro F1:** 0.521

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.846 | 0.786 | 0.815 | 14 |
| PCA | 1.000 | 0.500 | 0.667 | 2 |
| HODEN | 1.000 | 0.500 | 0.667 | 2 |
| PENIS | 1.000 | 0.500 | 0.667 | 2 |
| UCA | 0.500 | 0.500 | 0.500 | 2 |
| COMBI | 0.250 | 0.500 | 0.333 | 2 |
| NON_URO | 0.000 | 0.000 | 0.000 | 2 |

### Misclassifications

- **ncc_1** (Turtle, Ninja): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_5** (Muster, Clara): predicted `polymalignancy`, actual `nierenzellkarzinom`
- **ncc_10** (Beispiel, Hanna): predicted `polymalignancy`, actual `nierenzellkarzinom`
- **pca_1** (Test, Testovoci): predicted `non_urological`, actual `prostatakarzinom`
- **hoden_ca_1** (Test, Test1): predicted `unknown`, actual `hodentumor`
- **penis_ca_1** (Bruno, Brandon): predicted `nierenzellkarzinom`, actual `peniskarzinom`
- **uca_2** (Holman, Elisa): predicted `unknown`, actual `urothelkarzinom`
- **combi_2** (Vega, Orion): predicted `nierenzellkarzinom`, actual `polymalignancy`
- **non_uro_1** (Mumbasa, Lion): predicted `polymalignancy`, actual `non_urological`
- **non_uro_2** (Peter, Dostoyevski): predicted `urothelkarzinom`, actual `non_urological`

## qwen3:latest

- **Total Cases:** 26
- **Accuracy:** 69.23%
- **Macro F1:** 0.541

### Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NCC | 0.857 | 0.857 | 0.857 | 14 |
| PCA | 0.667 | 1.000 | 0.800 | 2 |
| HODEN | 1.000 | 0.500 | 0.667 | 2 |
| PENIS | 1.000 | 0.500 | 0.667 | 2 |
| UCA | 0.667 | 1.000 | 0.800 | 2 |
| COMBI | 0.000 | 0.000 | 0.000 | 2 |
| NON_URO | 0.000 | 0.000 | 0.000 | 2 |

### Misclassifications

- **ncc_1** (Turtle, Ninja): predicted `unknown`, actual `nierenzellkarzinom`
- **ncc_10** (Beispiel, Hanna): predicted `unknown`, actual `nierenzellkarzinom`
- **hoden_ca_1** (Test, Test1): predicted `unknown`, actual `hodentumor`
- **penis_ca_1** (Bruno, Brandon): predicted `nierenzellkarzinom`, actual `peniskarzinom`
- **combi_1** (Draco, Severus): predicted `prostatakarzinom`, actual `polymalignancy`
- **combi_2** (Vega, Orion): predicted `nierenzellkarzinom`, actual `polymalignancy`
- **non_uro_1** (Mumbasa, Lion): predicted `polymalignancy`, actual `non_urological`
- **non_uro_2** (Peter, Dostoyevski): predicted `urothelkarzinom`, actual `non_urological`
