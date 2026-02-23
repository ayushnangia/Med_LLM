# Infrastructure Comparison

Detailed comparison of Modal (vLLM) and OpenRouter infrastructure.

---

## Overview

| Aspect | Modal | OpenRouter |
|--------|-------|------------|
| **Type** | Serverless GPU compute | API service |
| **Framework** | vLLM | Proprietary |
| **Processing** | Batched | Sequential |
| **Cost Model** | Per-second GPU | Per-token |

---

## Modal (Primary Platform)

### Hardware

```python
GPU = "H100"  # NVIDIA H100 80GB
MEMORY = "51.4 GiB"  # Model memory footprint
```

### vLLM Configuration

```python
llm = LLM(
    model="google/gemma-3-27b-it",
    trust_remote_code=True,
    dtype="bfloat16",
    seed=42,
    max_model_len=32768,
    enforce_eager=True,
    disable_log_stats=True,
)
```

### Key Features

1. **Batched Processing**
   - All cases processed in one batch
   - GPU parallelism maximized

2. **Structured Outputs**
   - JSON schema enforcement via vLLM
   - Pydantic validation
   - Guaranteed valid JSON

3. **Reproducibility**
   - Seed=42 for deterministic results
   - Environment variables for CUDA determinism

### Modal App Structure

```python
@app.function(
    image=image,
    gpu=GPU(count=1),
    timeout=1800,
    memory=65536,
)
def run_prediction(model_key: str, hf_token: str) -> dict:
    # Load model
    # Build prompts
    # Batch inference
    # Return results
```

---

## OpenRouter (Comparison Platform)

### API Access

```python
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
```

### Request Format

```python
response = requests.post(
    BASE_URL,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://med-llm.local",
        "X-Title": "Med_LLM Treatment Prediction"
    },
    json={
        "model": "google/gemma-3-27b-it",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 32768
    },
    timeout=300
)
```

### Key Features

1. **Sequential Processing**
   - One case at a time
   - Rate limiting built-in

2. **No Structured Outputs**
   - Manual JSON parsing with regex
   - No schema enforcement
   - May return malformed JSON

3. **No Reproducibility**
   - No seed support
   - Results may vary between runs

---

## Performance Comparison

### Speed

Modal is significantly faster than OpenRouter due to batched GPU processing vs sequential API calls.

### Reliability

| Metric | Modal | OpenRouter |
|--------|-------|------------|
| JSON Parse Success | High (structured outputs) | Occasional parse failures |
| Timeout Failures | Rare | Occasional |
| Rate Limiting | None | Possible |

### Cost

| Platform | Cost Model |
|----------|------------|
| Modal | Per-second GPU billing |
| OpenRouter | Per-token billing |

---

## Model Registry

### Modal Models

```python
MODEL_CONFIGS = {
    "meditron3-7b": {
        "hf_id": "OpenMeditron/Meditron3-Qwen2.5-7B",
        "gpu": "H100",
    },
    "medgemma-4b": {
        "hf_id": "google/medgemma-4b-it",
        "gpu": "H100",
        "multimodal": True,
    },
    "medgemma-27b": {
        "hf_id": "google/medgemma-27b-text-it",
        "gpu": "H100",
    },
    "gemma-3-4b": {
        "hf_id": "google/gemma-3-4b-it",
        "gpu": "H100",
        "multimodal": True,
    },
    "gemma-3-27b": {
        "hf_id": "google/gemma-3-27b-it",
        "gpu": "H100",
        "multimodal": True,
    },
    "olmo-3.1-32b-instruct": {
        "hf_id": "allenai/Olmo-3.1-32B-Instruct",
        "gpu": "H100",
    },
    "olmo-3.1-32b-think": {
        "hf_id": "allenai/Olmo-3.1-32B-Think",
        "gpu": "H100",
        "thinking": True,
    },
}
```

### OpenRouter Models

Uses full model IDs directly:
- `google/gemma-3-27b-it`
- `google/gemma-3-12b-it`
- `qwen/qwq-32b`
- `anthropic/claude-sonnet-4`
- etc.

---

## When to Use Each

### Use Modal When:
- Running reproducible experiments (seed support)
- Processing many cases (batching efficiency)
- Need guaranteed JSON output (structured outputs)
- Cost is a concern (cheaper for batch)

### Use OpenRouter When:
- Quick validation of results
- Testing different models not on Modal
- Don't have Modal GPU quota
- Single-case testing

---

## Script Locations

| Script | Platform | Purpose |
|--------|----------|---------|
| `scripts/modal_treatment_predict.py` | Modal | Primary treatment prediction |
| `scripts/treatment_openrouter.py` | OpenRouter | Comparison/validation |
| `scripts/evaluate_treatment_llm_judge.py` | OpenRouter | LLM-as-Judge evaluation |
