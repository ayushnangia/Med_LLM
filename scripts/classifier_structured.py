#!/usr/bin/env python3
"""
Structured classifier using Pydantic models for input/output.

Features:
- Uses all available case data (anamnese, histologie, etc.)
- Returns structured JSON with reasoning + classification
- Saves full input/output for each case
- Works with both OpenRouter and Ollama

Usage:
    export OPENROUTER_API_KEY="your-key"
    python scripts/classifier_structured.py --model gemma3:27b
    python scripts/classifier_structured.py --model mistral:7b-instruct --provider ollama
"""

import os
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from models import (
        CaseInput, ClassificationOutput, ClassificationResult,
        CancerType, build_prompt, get_output_schema
    )
except ImportError:
    from scripts.models import (
        CaseInput, ClassificationOutput, ClassificationResult,
        CancerType, build_prompt, get_output_schema
    )


# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "converted_data" / "send_23_12_25"
RESULTS_DIR = BASE_DIR / "results"

# Ground truth mapping
FOLDER_TO_CLASS = {
    "ncc": "nierenzellkarzinom",
    "pca": "prostatakarzinom",
    "hoden_ca": "hodentumor",
    "penis_ca": "peniskarzinom",
    "uca": "urothelkarzinom",
    "combi": "polymalignancy",
    "non_uro": "non_urological"
}

# Model registry - short name -> OpenRouter model ID
OPENROUTER_MODELS = {
    # Gemma models
    "gemma3:27b": "google/gemma-3-27b-it",
    "gemma3:12b": "google/gemma-3-12b-it",
    "gemma3:4b": "google/gemma-3-4b-it",
    # Qwen models
    "qwen3:30b": "qwen/qwen3-30b-a3b",
    "qwen3:8b": "qwen/qwen3-8b",
    # Llama models
    "llama3:8b": "meta-llama/llama-3-8b-instruct",
    "llama3.3:70b": "meta-llama/llama-3.3-70b-instruct",
    # Mistral
    "mistral:7b-instruct": "mistralai/mistral-7b-instruct",
    # OpenAI
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-5.2": "openai/gpt-5.2",
    # Anthropic
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-opus-4.5": "anthropic/claude-opus-4.5",
    # DeepSeek
    "deepseek-r1": "deepseek/deepseek-r1",
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
    # Gemini reasoning models
    "gemini-3-flash": "google/gemini-3-flash-preview",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    # Free reasoning models
    "olmo-think:free": "allenai/olmo-3.1-32b-think:free",
    "mimo-flash:free": "xiaomi/mimo-v2-flash:free",
    "nemotron-nano:free": "nvidia/nemotron-3-nano-30b-a3b:free",
    # Other reasoning models
    "kimi-k2": "moonshotai/kimi-k2-thinking",
    "rnj-1": "essentialai/rnj-1-instruct",
}

# Models that support extended thinking/reasoning (OpenRouter reasoning API)
REASONING_MODELS = {
    # Google Gemini (best reasoning support)
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-pro-preview",
    "google/gemini-2.5-flash-preview-09-2025",
    "google/gemini-3-pro-preview",
    "google/gemini-3-flash-preview",
    # Qwen
    "qwen/qwen3-30b-a3b",
    "qwen/qwen3-235b-a22b",
    # DeepSeek
    "deepseek/deepseek-r1",
    "deepseek/deepseek-v3.2",
    # Anthropic
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-opus-4.5",
    # OpenAI
    "openai/gpt-5.2",
    # Free reasoning models
    "allenai/olmo-3.1-32b-think:free",
    "xiaomi/mimo-v2-flash:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    # Other reasoning models
    "moonshotai/kimi-k2-thinking",
}


class StructuredClassifier:
    """Classifier that returns structured output with reasoning."""

    def __init__(
        self,
        model: str,
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        temperature: float = 0.1
    ):
        self.provider = provider
        self.temperature = temperature
        self.model_input = model

        if provider == "openrouter":
            self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY required")
            self.model = OPENROUTER_MODELS.get(model, model)
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        else:  # ollama
            self.model = model
            self.base_url = "http://localhost:11434/api/generate"

        self.total_tokens = 0

    def classify(self, case_input: CaseInput) -> ClassificationResult:
        """Classify a case and return structured result."""
        prompt = build_prompt(case_input)
        start_time = time.time()

        result = ClassificationResult(
            case_id=case_input.case_id,
            provider=self.provider,
            model=self.model,
            input_case=case_input,
            prompt_text=prompt,
            ground_truth=case_input.ground_truth
        )

        try:
            if self.provider == "openrouter":
                response = self._call_openrouter(prompt)
            else:
                response = self._call_ollama(prompt)

            result.inference_time_seconds = time.time() - start_time
            result.raw_response = response.get("content", "")
            result.tokens_used = response.get("tokens", 0)
            result.reasoning_tokens = response.get("reasoning_tokens", 0)
            self.total_tokens += result.tokens_used

            # Parse structured output
            output = self._parse_response(result.raw_response)
            result.output = output
            result.success = True

            # Evaluate
            result.evaluate()

        except Exception as e:
            result.inference_time_seconds = time.time() - start_time
            result.success = False
            result.error_message = str(e)

        return result

    def _call_openrouter(self, prompt: str) -> Dict[str, Any]:
        """Call OpenRouter API."""
        # Build request payload
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 32000,
        }

        # Enable reasoning/thinking for supported models
        if self.model in REASONING_MODELS or ":thinking" in self.model:
            payload["reasoning"] = {
                "effort": "high"  # Can be "low", "medium", "high"
            }

        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=300  # Longer timeout for reasoning models
        )
        response.raise_for_status()
        data = response.json()

        # Extract content and reasoning if available
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "")

        # OpenRouter returns reasoning in multiple formats:
        # 1. "reasoning_details" array - detailed reasoning steps
        # 2. Direct "reasoning" field on message
        # 3. "reasoning_content" field for some models
        reasoning_details = message.get("reasoning_details", [])
        reasoning = message.get("reasoning", "") or message.get("reasoning_content", "")

        # If reasoning_details array exists, extract the reasoning text
        if reasoning_details:
            reasoning_parts = []
            for detail in reasoning_details:
                if isinstance(detail, dict):
                    reasoning_parts.append(detail.get("content", str(detail)))
                else:
                    reasoning_parts.append(str(detail))
            reasoning = "\n".join(reasoning_parts)

        # Extract reasoning tokens from usage if available
        # OpenRouter uses "reasoningTokens" (camelCase) in the usage object
        usage = data.get("usage", {})
        reasoning_tokens = usage.get("reasoningTokens", 0) or usage.get("reasoning_tokens", 0)

        # Combine reasoning with content if available
        if reasoning and reasoning not in content:
            content = f"<reasoning>\n{reasoning}\n</reasoning>\n\n{content}"

        return {
            "content": content,
            "tokens": usage.get("total_tokens", 0),
            "reasoning": reasoning,
            "reasoning_details": reasoning_details,  # Preserve for potential follow-up
            "reasoning_tokens": reasoning_tokens
        }

    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API."""
        response = requests.post(
            self.base_url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": 32000,
                    "num_ctx": 32000  # Context window
                }
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()

        return {
            "content": data.get("response", ""),
            "tokens": data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
        }

    def _parse_response(self, raw: str) -> Optional[ClassificationOutput]:
        """Parse raw response into structured output."""
        # Try to extract JSON from response
        raw = raw.strip()

        # Handle thinking tags
        if '</think>' in raw:
            raw = raw.split('</think>')[-1].strip()

        # Try to find JSON block
        json_start = raw.find('{')
        json_end = raw.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            try:
                json_str = raw[json_start:json_end]
                data = json.loads(json_str)

                # Normalize classification
                classification = data.get("classification", "").lower().strip()
                if classification not in [e.value for e in CancerType]:
                    classification = self._fuzzy_match_class(classification)

                return ClassificationOutput(
                    reasoning=data.get("reasoning", "No reasoning provided"),
                    classification=CancerType(classification),
                    confidence=data.get("confidence"),
                    key_indicators=data.get("key_indicators")
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: try to extract classification from text
        classification = self._extract_classification(raw)
        if classification:
            return ClassificationOutput(
                reasoning=raw[:500],  # Use raw response as reasoning
                classification=classification
            )

        return None

    def _extract_classification(self, text: str) -> Optional[CancerType]:
        """Extract classification from unstructured text."""
        text = text.lower()

        for cancer_type in CancerType:
            if cancer_type.value in text:
                return cancer_type

        # Aliases
        aliases = {
            "ncc": CancerType.nierenzellkarzinom,
            "rcc": CancerType.nierenzellkarzinom,
            "nierenkrebs": CancerType.nierenzellkarzinom,
            "pca": CancerType.prostatakarzinom,
            "prostata": CancerType.prostatakarzinom,
            "hoden": CancerType.hodentumor,
            "seminom": CancerType.hodentumor,
            "penis": CancerType.peniskarzinom,
            "blasen": CancerType.urothelkarzinom,
            "urothelial": CancerType.urothelkarzinom,
        }

        for alias, cancer_type in aliases.items():
            if alias in text:
                return cancer_type

        return None

    def _fuzzy_match_class(self, text: str) -> str:
        """Fuzzy match classification string to valid enum."""
        text = text.lower().strip()

        for cancer_type in CancerType:
            if cancer_type.value in text or text in cancer_type.value:
                return cancer_type.value

        return "non_urological"  # Default fallback


def load_all_cases() -> List[CaseInput]:
    """Load all cases as CaseInput objects."""
    all_cases = []

    for folder, ground_truth in FOLDER_TO_CLASS.items():
        folder_path = DATA_DIR / folder
        if not folder_path.exists():
            continue

        for json_file in folder_path.glob("*_cases_json.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for i, case in enumerate(data.get('cases', [])):
                case_id = f"{folder}_{i+1}"
                case_input = CaseInput.from_case_json(case_id, case, ground_truth)
                all_cases.append(case_input)

    return all_cases


def setup_run_directory(provider: str, model: str) -> Path:
    """Create timestamped run directory."""
    model_safe = model.replace("/", "_").replace(":", "_")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = RESULTS_DIR / provider / model_safe / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_classification(
    model: str,
    provider: str = "openrouter",
    temperature: float = 0.1,
    single_case: bool = False
):
    """Run structured classification on all cases."""

    # Initialize classifier
    try:
        classifier = StructuredClassifier(
            model=model,
            provider=provider,
            temperature=temperature
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        return None

    # Setup output directory
    run_dir = setup_run_directory(provider, classifier.model)
    print(f"Results directory: {run_dir}")

    # Load cases
    cases = load_all_cases()
    if single_case:
        cases = cases[:1]
    print(f"Loaded {len(cases)} cases")

    # Save config
    config = {
        "provider": provider,
        "model": classifier.model,
        "model_input": model,
        "temperature": temperature,
        "timestamp": datetime.now().isoformat(),
        "total_cases": len(cases)
    }
    with open(run_dir / "config.json", 'w') as f:
        json.dump(config, f, indent=2)

    # Run classification
    results: List[ClassificationResult] = []
    correct = 0
    errors = 0

    print(f"\nClassifying with {classifier.model}...")
    print("-" * 60)

    for i, case in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] {case.case_id}...", end=" ")

        result = classifier.classify(case)
        results.append(result)

        # Save individual result
        result_file = run_dir / f"{case.case_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(result.model_dump_json(indent=2))

        if not result.success:
            errors += 1
            print(f"ERROR: {result.error_message[:50]}")
        elif result.is_correct:
            correct += 1
            print(f"CORRECT ({result.inference_time_seconds:.1f}s)")
        else:
            pred = result.output.classification.value if result.output else "unknown"
            print(f"WRONG: {pred} (expected {case.ground_truth.value}) ({result.inference_time_seconds:.1f}s)")

    # Calculate summary
    total = len(cases)
    accuracy = correct / (total - errors) if (total - errors) > 0 else 0

    summary = {
        "model": classifier.model,
        "provider": provider,
        "timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "correct": correct,
        "incorrect": total - correct - errors,
        "errors": errors,
        "accuracy": accuracy,
        "total_tokens": classifier.total_tokens
    }

    # Save summary
    with open(run_dir / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    # Save all results
    all_results = {
        "metadata": config,
        "summary": summary,
        "results": [
            {
                "case_id": r.case_id,
                "ground_truth": r.ground_truth.value if r.ground_truth else None,
                "predicted": r.output.classification.value if r.output else None,
                "correct": r.is_correct,
                "reasoning": r.output.reasoning if r.output else None,
                "confidence": r.output.confidence if r.output else None,
                "key_indicators": r.output.key_indicators if r.output else None,
                "inference_time": r.inference_time_seconds,
                "tokens": r.tokens_used
            }
            for r in results
        ]
    }
    with open(run_dir / "all_results.json", 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Model: {classifier.model}")
    print(f"Provider: {provider}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Correct: {correct}/{total}")
    print(f"Errors: {errors}")
    print(f"Total tokens: {classifier.total_tokens}")
    print(f"\nResults saved to: {run_dir}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Structured medical case classification")
    parser.add_argument("--model", type=str, default="gemma3:27b",
                        help="Model to use")
    parser.add_argument("--provider", choices=["openrouter", "ollama"], default="openrouter",
                        help="Provider (openrouter or ollama)")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="Sampling temperature")
    parser.add_argument("--list-models", action="store_true",
                        help="List available models")
    parser.add_argument("--models-file", type=str, default=None,
                        help="Path to file with model IDs (one per line)")
    parser.add_argument("--single-case", action="store_true",
                        help="Run only first case (for testing)")

    args = parser.parse_args()

    if args.list_models:
        print("OpenRouter models:")
        for short, full in OPENROUTER_MODELS.items():
            print(f"  {short} -> {full}")
        return

    # Run from models file
    if args.models_file:
        models_path = Path(args.models_file)
        if not models_path.exists():
            print(f"ERROR: Models file not found: {args.models_file}")
            return

        models = [line.strip() for line in models_path.read_text().splitlines() if line.strip()]
        print(f"Running {len(models)} models from {args.models_file}")
        print("=" * 60)

        all_summaries = []
        for i, model in enumerate(models, 1):
            print(f"\n[{i}/{len(models)}] Model: {model}")
            print("-" * 40)
            try:
                summary = run_classification(
                    model=model,
                    provider=args.provider,
                    temperature=args.temperature,
                    single_case=args.single_case
                )
                if summary:
                    all_summaries.append(summary)
            except Exception as e:
                print(f"ERROR: {e}")
                all_summaries.append({"model": model, "error": str(e)})

        # Print final comparison
        print("\n" + "=" * 60)
        print("FINAL COMPARISON")
        print("=" * 60)
        all_summaries.sort(key=lambda x: x.get('accuracy', 0), reverse=True)
        for i, s in enumerate(all_summaries, 1):
            if 'error' in s:
                print(f"{i}. {s['model']}: ERROR - {s['error'][:50]}")
            else:
                print(f"{i}. {s['model']}: {s['accuracy']:.2%} ({s['correct']}/{s['total_cases']})")
        return

    run_classification(args.model, args.provider, args.temperature, args.single_case)


if __name__ == "__main__":
    main()
