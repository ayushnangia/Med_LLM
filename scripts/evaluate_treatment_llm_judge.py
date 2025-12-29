#!/usr/bin/env python3
"""
LLM-as-a-Judge Evaluation for Treatment Predictions

Uses OpenRouter with QwQ-32B (or other models) to evaluate treatment predictions.
Implements structured output with Pydantic validation and model-specific hyperparameters.

Usage:
    python scripts/evaluate_treatment_llm_judge.py --results-dir results/modal_treatment/openmeditron_meditron3-qwen2.5-7b/2025-12-29_22-42-06
    python scripts/evaluate_treatment_llm_judge.py --results-dir results/modal_treatment/... --model qwen3-32b --limit 5
"""

import os
import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import time
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# OpenRouter API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# =============================================================================
# MODEL CONFIGURATIONS (matching modal_classify.py pattern)
# =============================================================================

JUDGE_MODELS: Dict[str, Dict[str, Any]] = {
    # QwQ - thinking model, needs special handling
    "qwq-32b": {
        "openrouter_id": "qwen/qwq-32b",
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 8192,
        "thinking": True,  # Outputs <think> blocks
    },
    # Qwen3 standard models
    "qwen3-32b": {
        "openrouter_id": "qwen/qwen3-32b",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    "qwen3-235b": {
        "openrouter_id": "qwen/qwen3-235b-a22b",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    "qwen3-30b": {
        "openrouter_id": "qwen/qwen3-30b-a3b",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    # GPT-4o - supports structured output
    "gpt-4o": {
        "openrouter_id": "openai/gpt-4o",
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    "gpt-4o-mini": {
        "openrouter_id": "openai/gpt-4o-mini",
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    # Claude - supports structured output
    "claude-sonnet": {
        "openrouter_id": "anthropic/claude-sonnet-4",
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    "claude-haiku": {
        "openrouter_id": "anthropic/claude-3-5-haiku",
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 2048,
        "supports_json_schema": True,
    },
    # Gemma
    "gemma-3-27b": {
        "openrouter_id": "google/gemma-3-27b-it",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 2048,
    },
}


# =============================================================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# =============================================================================

class JudgeEvaluation(BaseModel):
    """Structured evaluation from judge LLM with validation."""

    therapy_semantic_match: bool = Field(
        ...,
        description="True if predicted therapy is semantically equivalent to ground truth"
    )
    therapy_semantic_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score 0-1"
    )
    clinical_appropriateness: bool = Field(
        ...,
        description="True if therapy is clinically appropriate per RCC guidelines"
    )
    clinical_appropriateness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Clinical appropriateness score 0-1"
    )
    reasoning_quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality of reasoning 0-1"
    )
    reasoning_critique: str = Field(
        ...,
        description="Brief critique of the reasoning quality"
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall evaluation score 0-1"
    )
    judge_reasoning: str = Field(
        ...,
        description="Judge's reasoning for the scores given"
    )

    @field_validator('therapy_semantic_score', 'clinical_appropriateness_score', 'reasoning_quality', 'overall_score', mode='before')
    @classmethod
    def clamp_score(cls, v):
        """Ensure scores are within valid range."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


class EvaluationResult(BaseModel):
    """Complete evaluation result for a case."""
    case_id: str
    evaluation: Optional[JudgeEvaluation] = None
    raw_response: str = ""
    error: Optional[str] = None
    inference_time_seconds: float = 0.0


# =============================================================================
# PROMPT BUILDING
# =============================================================================

def build_judge_prompt(case_result: dict) -> str:
    """Build evaluation prompt for the judge LLM."""

    input_case = case_result.get("input_case", {})
    prediction = case_result.get("prediction", {})
    gt_metastatic = case_result.get("ground_truth_metastatic")
    gt_therapy = case_result.get("ground_truth_therapy", "")

    # Format prediction
    if prediction:
        pred_metastatic = prediction.get("is_metastatic")
        pred_reasoning = prediction.get("metastatic_reasoning", "")
        pred_imdc = prediction.get("imdc_risk", "")
        pred_imdc_reasoning = prediction.get("imdc_reasoning", "")
        pred_treatment_reasoning = prediction.get("treatment_reasoning", "")
        pred_therapy = prediction.get("recommended_therapy", "")
        pred_category = prediction.get("therapy_category", "")
    else:
        pred_metastatic = None
        pred_reasoning = "Keine Vorhersage generiert"
        pred_imdc = ""
        pred_imdc_reasoning = ""
        pred_treatment_reasoning = ""
        pred_therapy = ""
        pred_category = ""

    prompt = f"""Du bist ein erfahrener Onkologe, der als Gutachter für KI-generierte Therapieempfehlungen bei Nierenzellkarzinom (RCC) fungiert.

=== KLINISCHER FALL ===
Patient: {input_case.get('patient_name', 'Unbekannt')}, {input_case.get('age', '?')} Jahre
ECOG: {input_case.get('ecog', '?')}
Diagnose: {input_case.get('diagnose_kurz', '')}
Stadium: {input_case.get('stadium', '')}
Anamnese: {input_case.get('anamnese', '')[:500]}

=== GROUND TRUTH (Tumorboard-Empfehlung) ===
Metastasiert: {gt_metastatic}
Therapieempfehlung: {gt_therapy}

=== KI-VORHERSAGE ===
Metastasiert: {pred_metastatic}
Metastasierungs-Begründung: {pred_reasoning}
IMDC-Risiko: {pred_imdc}
IMDC-Begründung: {pred_imdc_reasoning}
Therapie-Begründung: {pred_treatment_reasoning}
Empfohlene Therapie: {pred_therapy}
Therapie-Kategorie: {pred_category}

=== BEWERTUNGSAUFGABE ===
Bewerte die KI-Vorhersage anhand folgender Kriterien:

1. **Therapie Semantische Übereinstimmung** (therapy_semantic_match, therapy_semantic_score):
   - "NIVO+CABO" = "Nivolumab/Cabozantinib" = "Nivolumab + Cabozantinib" → TRUE, 1.0
   - "TKI/IO Kombination" wenn spezifische IO+TKI empfohlen → TRUE, 0.9
   - Gleiche Wirkstoffklasse aber anderes Medikament → FALSE, 0.5-0.7
   - Komplett unterschiedlich → FALSE, 0.0-0.3

2. **Klinische Angemessenheit** (clinical_appropriateness, clinical_appropriateness_score):
   - Metastasiert + ICI möglich: IO+TKI (Nivo+Cabo, Pembro+Axi, Pembro+Len) oder IO+IO (Nivo+Ipi)
   - Metastasiert + ICI nicht möglich: TKI mono (Pazopanib, Sunitinib, Cabozantinib)
   - Nicht-metastasiert: Chirurgie (Nephrektomie, Teilresektion) oder Überwachung
   - Leitlinienkonform → TRUE, 0.8-1.0
   - Akzeptabel aber nicht erste Wahl → TRUE, 0.6-0.8
   - Nicht leitlinienkonform → FALSE, 0.0-0.5

3. **Begründungsqualität** (reasoning_quality):
   - Vollständig, logisch, medizinisch korrekt → 0.8-1.0
   - Größtenteils korrekt mit kleinen Mängeln → 0.5-0.7
   - Unvollständig oder fehlerhaft → 0.0-0.4

4. **Gesamtbewertung** (overall_score):
   - Gewichteter Durchschnitt: 40% Semantik, 40% Klinik, 20% Begründung

Antworte NUR mit einem validen JSON-Objekt (keine Erklärung davor oder danach):
{{
    "therapy_semantic_match": true/false,
    "therapy_semantic_score": 0.0-1.0,
    "clinical_appropriateness": true/false,
    "clinical_appropriateness_score": 0.0-1.0,
    "reasoning_quality": 0.0-1.0,
    "reasoning_critique": "Kurze Kritik...",
    "overall_score": 0.0-1.0,
    "judge_reasoning": "Begründung für Bewertung..."
}}"""

    return prompt


# =============================================================================
# OPENROUTER API CALL
# =============================================================================

def call_openrouter(
    prompt: str,
    model_key: str = "qwq-32b",
    retry_count: int = 3
) -> tuple[Optional[str], float]:
    """
    Call OpenRouter API with model-specific hyperparameters.

    Returns:
        Tuple of (response_text, inference_time_seconds)
    """
    import requests

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set! Add to .env file or export.")

    cfg = JUDGE_MODELS.get(model_key)
    if not cfg:
        raise ValueError(f"Unknown model: {model_key}. Available: {list(JUDGE_MODELS.keys())}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/med-llm",
        "X-Title": "Med-LLM Treatment Evaluation"
    }

    data = {
        "model": cfg["openrouter_id"],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": cfg.get("temperature", 0.3),
        "top_p": cfg.get("top_p", 0.95),
        "max_tokens": cfg.get("max_tokens", 2048),
    }

    # Add JSON schema for models that support it (structured output)
    if cfg.get("supports_json_schema") and not cfg.get("thinking"):
        data["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "judge_evaluation",
                "strict": True,
                "schema": JudgeEvaluation.model_json_schema()
            }
        }

    for attempt in range(retry_count):
        try:
            start_time = time.time()
            response = requests.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=data,
                timeout=120
            )
            inference_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return content, inference_time
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = (attempt + 1) * 5
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"API error {response.status_code}: {response.text[:200]}")
                if attempt < retry_count - 1:
                    time.sleep(2)

        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt + 1}")
            if attempt < retry_count - 1:
                time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            if attempt < retry_count - 1:
                time.sleep(2)

    return None, 0.0


# =============================================================================
# RESPONSE PARSING WITH PYDANTIC VALIDATION
# =============================================================================

def parse_judge_response(text: str, is_thinking: bool = False) -> Optional[JudgeEvaluation]:
    """
    Parse judge response into structured evaluation with Pydantic validation.

    Args:
        text: Raw response text from LLM
        is_thinking: True if model outputs <think> blocks (like QwQ)

    Returns:
        JudgeEvaluation object or None if parsing fails
    """
    json_text = text

    # Handle thinking model output - extract content after </think>
    if is_thinking:
        if "</think>" in text:
            json_text = text.split("</think>")[-1].strip()
        elif "<think>" in text:
            # Model started thinking but didn't close - try to find JSON after think block
            think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
            if think_match:
                json_text = think_match.group(1).strip()

    # Try direct Pydantic validation (works with structured output)
    try:
        return JudgeEvaluation.model_validate_json(json_text)
    except Exception:
        pass

    # Fallback: Find JSON block in response
    json_match = re.search(r'\{[\s\S]*"therapy_semantic_match"[\s\S]*\}', json_text)
    if not json_match:
        # Try finding any JSON object
        json_match = re.search(r'\{[\s\S]*"overall_score"[\s\S]*\}', json_text)
    if not json_match:
        json_match = re.search(r'\{[\s\S]*\}', json_text)

    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            return JudgeEvaluation.model_validate(parsed)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Pydantic validation error: {e}")

    return None


# =============================================================================
# MAIN EVALUATION LOGIC
# =============================================================================

def evaluate_results(
    results_dir: str,
    model_key: str = "qwq-32b",
    limit: Optional[int] = None
) -> dict:
    """
    Evaluate all results in a directory using LLM judge.

    Args:
        results_dir: Path to results directory containing ncc_*.json files
        model_key: Judge model key from JUDGE_MODELS
        limit: Optional limit on number of cases to evaluate

    Returns:
        Summary dict with all evaluations
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    cfg = JUDGE_MODELS.get(model_key)
    if not cfg:
        raise ValueError(f"Unknown model: {model_key}")

    is_thinking = cfg.get("thinking", False)

    # Load all case results
    case_files = sorted(results_path.glob("ncc_*.json"))
    if limit:
        case_files = case_files[:limit]

    print(f"\n{'='*60}")
    print("LLM-as-a-Judge Evaluation")
    print(f"{'='*60}")
    print(f"Results Dir: {results_dir}")
    print(f"Judge Model: {model_key} ({cfg['openrouter_id']})")
    print(f"Temperature: {cfg.get('temperature', 0.3)}")
    print(f"Top-P: {cfg.get('top_p', 0.95)}")
    print(f"Max Tokens: {cfg.get('max_tokens', 2048)}")
    print(f"Thinking Mode: {is_thinking}")
    print(f"Structured Output: {cfg.get('supports_json_schema', False)}")
    print(f"Cases: {len(case_files)}")
    print("-" * 60)

    evaluations: list[EvaluationResult] = []

    for i, case_file in enumerate(case_files, 1):
        with open(case_file, 'r', encoding='utf-8') as f:
            case_result = json.load(f)

        case_id = case_result.get("case_id", case_file.stem)
        print(f"[{i}/{len(case_files)}] {case_id}...", end=" ", flush=True)

        # Build prompt and call judge
        prompt = build_judge_prompt(case_result)
        response, inference_time = call_openrouter(prompt, model_key)

        eval_result = EvaluationResult(
            case_id=case_id,
            inference_time_seconds=inference_time
        )

        if response:
            evaluation = parse_judge_response(response, is_thinking)
            if evaluation:
                eval_result.evaluation = evaluation
                eval_result.raw_response = response
                print(f"✓ Score: {evaluation.overall_score:.2f} (Sem: {evaluation.therapy_semantic_score:.2f}, Clin: {evaluation.clinical_appropriateness_score:.2f})")
            else:
                eval_result.raw_response = response
                eval_result.error = "parse_failed"
                print("✗ Parse failed")
        else:
            eval_result.error = "api_error"
            print("✗ API error")

        evaluations.append(eval_result)

        # Rate limiting between calls
        time.sleep(0.5)

    # Calculate aggregate metrics
    valid_evals = [e for e in evaluations if e.evaluation is not None]

    if valid_evals:
        avg_semantic = sum(e.evaluation.therapy_semantic_score for e in valid_evals) / len(valid_evals)
        avg_clinical = sum(e.evaluation.clinical_appropriateness_score for e in valid_evals) / len(valid_evals)
        avg_reasoning = sum(e.evaluation.reasoning_quality for e in valid_evals) / len(valid_evals)
        avg_overall = sum(e.evaluation.overall_score for e in valid_evals) / len(valid_evals)

        semantic_match_count = sum(1 for e in valid_evals if e.evaluation.therapy_semantic_match)
        clinical_ok_count = sum(1 for e in valid_evals if e.evaluation.clinical_appropriateness)
    else:
        avg_semantic = avg_clinical = avg_reasoning = avg_overall = 0.0
        semantic_match_count = clinical_ok_count = 0

    summary = {
        "judge_model": cfg["openrouter_id"],
        "judge_config": {
            "temperature": cfg.get("temperature", 0.3),
            "top_p": cfg.get("top_p", 0.95),
            "max_tokens": cfg.get("max_tokens", 2048),
            "thinking_mode": is_thinking,
            "structured_output": cfg.get("supports_json_schema", False),
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        "source_results_dir": str(results_dir),
        "total_cases": len(case_files),
        "evaluated_cases": len(valid_evals),
        "failed_evaluations": len(case_files) - len(valid_evals),
        "metrics": {
            "therapy_semantic_match_rate": semantic_match_count / len(valid_evals) if valid_evals else 0,
            "therapy_semantic_match_count": semantic_match_count,
            "avg_therapy_semantic_score": round(avg_semantic, 4),
            "clinical_appropriateness_rate": clinical_ok_count / len(valid_evals) if valid_evals else 0,
            "clinical_appropriateness_count": clinical_ok_count,
            "avg_clinical_score": round(avg_clinical, 4),
            "avg_reasoning_quality": round(avg_reasoning, 4),
            "avg_overall_score": round(avg_overall, 4),
        },
        "evaluations": [e.model_dump() for e in evaluations],
    }

    # Save results
    judge_slug = model_key.replace("/", "_").replace(":", "_")
    out_file = results_path / f"judge_evaluation_{judge_slug}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Judge: {cfg['openrouter_id']}")
    print(f"Evaluated: {len(valid_evals)}/{len(case_files)} cases")
    print()
    print(f"Therapy Semantic Match: {summary['metrics']['therapy_semantic_match_rate']*100:.1f}% ({semantic_match_count}/{len(valid_evals)})")
    print(f"  Avg Score: {avg_semantic:.3f}")
    print()
    print(f"Clinical Appropriateness: {summary['metrics']['clinical_appropriateness_rate']*100:.1f}% ({clinical_ok_count}/{len(valid_evals)})")
    print(f"  Avg Score: {avg_clinical:.3f}")
    print()
    print(f"Reasoning Quality: {avg_reasoning:.3f}")
    print(f"Overall Score: {avg_overall:.3f}")
    print()
    print(f"Saved: {out_file}")

    return summary


def list_models():
    """Print available judge models."""
    print("\nAvailable Judge Models:")
    print("-" * 70)
    print(f"{'Key':<15} {'OpenRouter ID':<35} {'Thinking':<10} {'JSON Schema'}")
    print("-" * 70)
    for key, cfg in JUDGE_MODELS.items():
        thinking = "Yes" if cfg.get("thinking") else "No"
        json_schema = "Yes" if cfg.get("supports_json_schema") else "No"
        print(f"{key:<15} {cfg['openrouter_id']:<35} {thinking:<10} {json_schema}")


def main():
    parser = argparse.ArgumentParser(
        description="LLM-as-a-Judge evaluation for treatment predictions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate with default QwQ-32B judge
  python scripts/evaluate_treatment_llm_judge.py --results-dir results/modal_treatment/.../timestamp

  # Use GPT-4o with structured output
  python scripts/evaluate_treatment_llm_judge.py --results-dir ... --model gpt-4o

  # Test with limited cases
  python scripts/evaluate_treatment_llm_judge.py --results-dir ... --model qwen3-32b --limit 5

  # List available models
  python scripts/evaluate_treatment_llm_judge.py --list-models
        """
    )
    parser.add_argument("--results-dir", help="Path to results directory")
    parser.add_argument("--model", default="qwq-32b", help="Judge model key")
    parser.add_argument("--limit", type=int, help="Limit number of cases")
    parser.add_argument("--list-models", action="store_true", help="List available models")

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    if not args.results_dir:
        parser.error("--results-dir is required (or use --list-models)")

    evaluate_results(args.results_dir, args.model, args.limit)


if __name__ == "__main__":
    main()
