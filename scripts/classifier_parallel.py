#!/usr/bin/env python3
"""
Parallel classifier using async requests for high throughput.

Usage:
    python scripts/classifier_parallel.py --model gemini-3-flash --concurrency 10
    python scripts/classifier_parallel.py --models-file models_openrouter.txt --concurrency 10
"""

import os
import json
import asyncio
import aiohttp
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from models import (
        CaseInput, ClassificationOutput, ClassificationResult,
        CancerType, build_prompt
    )
except ImportError:
    from scripts.models import (
        CaseInput, ClassificationOutput, ClassificationResult,
        CancerType, build_prompt
    )

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "converted_data" / "send_23_12_25"
RESULTS_DIR = BASE_DIR / "results"

FOLDER_TO_CLASS = {
    "ncc": "nierenzellkarzinom",
    "pca": "prostatakarzinom",
    "hoden_ca": "hodentumor",
    "penis_ca": "peniskarzinom",
    "uca": "urothelkarzinom",
    "combi": "polymalignancy",
    "non_uro": "non_urological"
}

# Model registry
OPENROUTER_MODELS = {
    "gemma3:27b": "google/gemma-3-27b-it",
    "gemma3:4b": "google/gemma-3-4b-it",
    "qwen3:30b": "qwen/qwen3-30b-a3b",
    "llama3.3:70b": "meta-llama/llama-3.3-70b-instruct",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-5.2": "openai/gpt-5.2",
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-opus-4.5": "anthropic/claude-opus-4.5",
    "deepseek-r1": "deepseek/deepseek-r1",
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
    "gemini-3-flash": "google/gemini-3-flash-preview",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "olmo-think:free": "allenai/olmo-3.1-32b-think:free",
    "mimo-flash:free": "xiaomi/mimo-v2-flash:free",
    "nemotron-nano:free": "nvidia/nemotron-3-nano-30b-a3b:free",
    "kimi-k2": "moonshotai/kimi-k2-thinking",
}

REASONING_MODELS = {
    "google/gemini-2.5-flash", "google/gemini-2.5-pro", "google/gemini-3-flash-preview",
    "qwen/qwen3-30b-a3b", "deepseek/deepseek-r1", "deepseek/deepseek-v3.2",
    "anthropic/claude-3.5-sonnet", "anthropic/claude-opus-4.5", "openai/gpt-5.2",
    "allenai/olmo-3.1-32b-think:free", "xiaomi/mimo-v2-flash:free",
    "nvidia/nemotron-3-nano-30b-a3b:free", "moonshotai/kimi-k2-thinking",
}


class ParallelClassifier:
    """High-throughput parallel classifier."""

    def __init__(self, model: str, api_key: str, temperature: float = 0.1, concurrency: int = 10):
        self.model = OPENROUTER_MODELS.get(model, model)
        self.api_key = api_key
        self.temperature = temperature
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.total_tokens = 0

    async def classify_case(self, session: aiohttp.ClientSession, case: CaseInput) -> ClassificationResult:
        """Classify a single case asynchronously."""
        prompt = build_prompt(case)
        start_time = asyncio.get_event_loop().time()

        result = ClassificationResult(
            case_id=case.case_id,
            provider="openrouter",
            model=self.model,
            input_case=case,
            prompt_text=prompt,
            ground_truth=case.ground_truth
        )

        async with self.semaphore:
            try:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": 32000,
                }
                if self.model in REASONING_MODELS:
                    payload["reasoning"] = {"effort": "high"}

                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                message = data.get("choices", [{}])[0].get("message", {})
                content = message.get("content", "")
                usage = data.get("usage", {})

                result.raw_response = content
                result.tokens_used = usage.get("total_tokens", 0)
                result.reasoning_tokens = usage.get("reasoningTokens", 0)
                self.total_tokens += result.tokens_used

                # Parse response
                result.output = self._parse_response(content)
                result.success = True
                result.evaluate()

            except Exception as e:
                result.success = False
                result.error_message = str(e)

            result.inference_time_seconds = asyncio.get_event_loop().time() - start_time
            return result

    def _parse_response(self, raw: str) -> Optional[ClassificationOutput]:
        """Parse response into structured output."""
        raw = raw.strip()
        if '</think>' in raw:
            raw = raw.split('</think>')[-1].strip()

        json_start = raw.find('{')
        json_end = raw.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            try:
                data = json.loads(raw[json_start:json_end])
                classification = data.get("classification", "").lower().strip()

                # Fuzzy match
                if classification not in [e.value for e in CancerType]:
                    for ct in CancerType:
                        if ct.value in classification or classification in ct.value:
                            classification = ct.value
                            break
                    else:
                        classification = "non_urological"

                return ClassificationOutput(
                    reasoning=data.get("reasoning", ""),
                    classification=CancerType(classification),
                    confidence=data.get("confidence"),
                    key_indicators=data.get("key_indicators")
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback extraction
        raw_lower = raw.lower()
        for ct in CancerType:
            if ct.value in raw_lower:
                return ClassificationOutput(reasoning=raw[:300], classification=ct)
        return None

    async def classify_all(self, cases: List[CaseInput]) -> List[ClassificationResult]:
        """Classify all cases in parallel."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.classify_case(session, case) for case in cases]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions
            processed = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    result = ClassificationResult(
                        case_id=cases[i].case_id,
                        provider="openrouter",
                        model=self.model,
                        input_case=cases[i],
                        prompt_text="",
                        success=False,
                        error_message=str(r)
                    )
                    processed.append(result)
                else:
                    processed.append(r)
            return processed


def load_all_cases() -> List[CaseInput]:
    """Load all cases."""
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


async def run_parallel_classification(
    model: str,
    temperature: float = 0.1,
    concurrency: int = 10,
    single_case: bool = False
) -> Dict:
    """Run parallel classification."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        return None

    classifier = ParallelClassifier(model, api_key, temperature, concurrency)

    # Setup output directory
    model_safe = classifier.model.replace("/", "_").replace(":", "_")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = RESULTS_DIR / "openrouter" / model_safe / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load cases
    cases = load_all_cases()
    if single_case:
        cases = cases[:1]

    print(f"Model: {classifier.model}")
    print(f"Concurrency: {concurrency}")
    print(f"Cases: {len(cases)}")
    print(f"Results: {run_dir}")
    print("-" * 60)

    # Run classification
    start_time = datetime.now()
    results = await classifier.classify_all(cases)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Process results
    correct = sum(1 for r in results if r.is_correct)
    errors = sum(1 for r in results if not r.success)
    total = len(cases)
    accuracy = correct / (total - errors) if (total - errors) > 0 else 0

    # Print results
    for r in results:
        if not r.success:
            status = "ERROR"
        elif r.is_correct:
            status = "✅"
        else:
            pred = r.output.classification.value if r.output else "?"
            status = f"❌ {pred}"
        print(f"  {r.case_id}: {status}")

    # Save results
    summary = {
        "model": classifier.model,
        "provider": "openrouter",
        "timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "correct": correct,
        "incorrect": total - correct - errors,
        "errors": errors,
        "accuracy": accuracy,
        "total_tokens": classifier.total_tokens,
        "elapsed_seconds": elapsed,
        "concurrency": concurrency
    }

    with open(run_dir / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    # Save individual results
    for r in results:
        with open(run_dir / f"{r.case_id}.json", 'w', encoding='utf-8') as f:
            f.write(r.model_dump_json(indent=2))

    print("=" * 60)
    print(f"RESULTS: {classifier.model}")
    print(f"Accuracy: {accuracy:.2%} ({correct}/{total})")
    print(f"Errors: {errors}")
    print(f"Tokens: {classifier.total_tokens}")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(cases):.2f}s/case)")
    print("=" * 60)

    return summary


async def run_multiple_models(models: List[str], concurrency: int, single_case: bool):
    """Run classification for multiple models."""
    all_summaries = []

    for i, model in enumerate(models, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(models)}] {model}")
        print("=" * 60)

        try:
            summary = await run_parallel_classification(model, concurrency=concurrency, single_case=single_case)
            if summary:
                all_summaries.append(summary)
        except Exception as e:
            print(f"ERROR: {e}")
            all_summaries.append({"model": model, "error": str(e)})

    # Final comparison
    print("\n" + "=" * 60)
    print("FINAL COMPARISON")
    print("=" * 60)
    all_summaries.sort(key=lambda x: x.get('accuracy', 0), reverse=True)
    for i, s in enumerate(all_summaries, 1):
        if 'error' in s:
            print(f"{i}. {s['model']}: ERROR")
        else:
            print(f"{i}. {s['model']}: {s['accuracy']:.2%} ({s['correct']}/{s['total_cases']}) - {s['elapsed_seconds']:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Parallel medical case classification")
    parser.add_argument("--model", type=str, default="gemini-3-flash")
    parser.add_argument("--models-file", type=str, default=None)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--single-case", action="store_true")
    parser.add_argument("--list-models", action="store_true")

    args = parser.parse_args()

    if args.list_models:
        print("Available models:")
        for short, full in OPENROUTER_MODELS.items():
            print(f"  {short} -> {full}")
        return

    if args.models_file:
        models_path = Path(args.models_file)
        if not models_path.exists():
            print(f"ERROR: {args.models_file} not found")
            return
        models = [l.strip() for l in models_path.read_text().splitlines() if l.strip()]
        asyncio.run(run_multiple_models(models, args.concurrency, args.single_case))
    else:
        asyncio.run(run_parallel_classification(
            args.model, args.temperature, args.concurrency, args.single_case
        ))


if __name__ == "__main__":
    main()
