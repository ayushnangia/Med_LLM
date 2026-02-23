# Hyperparameters

Complete documentation of all model hyperparameters used in treatment prediction.

---

## Current Configuration (Aligned)

Both Modal and OpenRouter now use identical hyperparameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| **temperature** | 0.3 | Controls randomness (lower = more deterministic) |
| **top_p** | 0.95 | Nucleus sampling threshold |
| **max_tokens** | 32768 | Maximum output tokens |
| **seed** | 42 (Modal only) | For reproducibility |

---

## Modal Configuration

### Sampling Parameters (Non-Thinking Models)

```python
from vllm.sampling_params import SamplingParams, StructuredOutputsParams

params = SamplingParams(
    temperature=0.3,
    top_p=0.95,
    max_tokens=32768,
    seed=42,
    structured_outputs=StructuredOutputsParams(json=json_schema)
)
```

### Sampling Parameters (Thinking Models - e.g., Olmo-3.1-32B-Think)

```python
params = SamplingParams(
    temperature=0.6,  # Higher for thinking models
    top_p=0.95,
    max_tokens=4096,  # Lower for thinking output
    seed=42,
)
```

### vLLM Engine Configuration

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

### Environment Variables

```python
{
    "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    "PYTHONHASHSEED": "42",
}
```

---

## OpenRouter Configuration

### API Request Parameters

```python
response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
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

### Default Constructor

```python
class OpenRouterTreatmentPredictor:
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        top_p: float = 0.95,
        max_tokens: int = 32768,
    ):
```

---

## Parameter Explanations

### Temperature (0.3)

- **Range:** 0.0 - 2.0
- **Effect:** Lower values make output more deterministic
- **Why 0.3:** Medical recommendations should be consistent, not creative
- **Trade-off:** Too low (0.0) may cause repetitive outputs; too high causes hallucinations

### Top-P (0.95)

- **Range:** 0.0 - 1.0
- **Effect:** Nucleus sampling - only consider tokens in top 95% probability mass
- **Why 0.95:** Balanced between diversity and coherence
- **Alternative:** top_k sampling (not used here)

### Max Tokens (32768)

- **Effect:** Maximum length of generated response
- **Why 32768:** Allows for detailed reasoning without truncation
- **Note:** Most responses use ~500-2000 tokens; this is headroom

### Seed (42)

- **Effect:** Deterministic random number generation
- **Why 42:** Convention (Hitchhiker's Guide reference)
- **Limitation:** Only works in Modal (vLLM), not OpenRouter API

---

## Historical Changes

| Date | Change | Reason |
|------|--------|--------|
| 2025-12-29 | max_tokens: 2048 → 32768 | Prevent truncation |
| 2025-12-29 | Added top_p=0.95 to OpenRouter | Alignment with Modal |
| 2025-12-29 | Removed prompt truncation | Save full prompts |

---

## Thinking Model Special Case

For models with explicit thinking capability (e.g., `olmo-3.1-32b-think`):

| Parameter | Standard | Thinking Model |
|-----------|----------|----------------|
| temperature | 0.3 | 0.6 |
| max_tokens | 32768 | 4096 |
| structured_outputs | Yes | No |

Thinking models produce free-form reasoning in `<think>` tags before JSON output.
