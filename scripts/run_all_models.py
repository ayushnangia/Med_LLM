#!/usr/bin/env python3
"""
Run classification with multiple models (Ollama and OpenRouter).

Usage:
    # Run all available models
    python scripts/run_all_models.py

    # Run only OpenRouter models
    python scripts/run_all_models.py --provider openrouter

    # Run only Ollama models
    python scripts/run_all_models.py --provider ollama

    # Run specific models
    python scripts/run_all_models.py --models "gemma3:4b,mistral:7b-instruct"

Output:
    results/
    ├── ollama/
    │   └── {model}/
    │       └── {timestamp}/
    └── openrouter/
        └── {model}/
            └── {timestamp}/
"""

import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "results"
FINDINGS_DIR = BASE_DIR / "findings"

# Models to test
OLLAMA_MODELS = [
    "gemma3:4b",
    "gemma3:12b",
    "llama3:8b",
    "mistral:7b-instruct",
    "qwen3:latest",
    "qwen3:4b",
]

OPENROUTER_MODELS = [
    "gemma3:27b",
    "gemma3:12b",
    "gemma3:4b",
    "qwen3:30b",
    "qwen3:8b",
    "qwen2.5:14b-instruct",
    "llama3:8b",
    "mistral:7b-instruct",
    "llama3.3:70b",
]


def get_available_ollama_models() -> List[str]:
    """Get list of locally installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = [line.split()[0] for line in lines if line.strip()]
            return models
        return []
    except:
        return []


def run_ollama_classification(model: str) -> Optional[Dict]:
    """Run classification using Ollama."""
    print(f"\n{'='*60}")
    print(f"Running Ollama: {model}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            ["python", "scripts/classify_cases.py", "--model", model],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=1800  # 30 min timeout
        )
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr[:500]}")

        return {"model": model, "provider": "ollama", "success": result.returncode == 0}
    except Exception as e:
        print(f"Error: {e}")
        return {"model": model, "provider": "ollama", "success": False, "error": str(e)}


def run_openrouter_classification(model: str) -> Optional[Dict]:
    """Run classification using OpenRouter."""
    print(f"\n{'='*60}")
    print(f"Running OpenRouter: {model}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            ["python", "scripts/classify_openrouter.py", "--model", model],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=1800
        )
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr[:500]}")

        return {"model": model, "provider": "openrouter", "success": result.returncode == 0}
    except Exception as e:
        print(f"Error: {e}")
        return {"model": model, "provider": "openrouter", "success": False, "error": str(e)}


def generate_comparison_report():
    """Generate comparison report from all results."""
    print(f"\n{'='*60}")
    print("Generating Comparison Report")
    print(f"{'='*60}")

    all_results = []

    # Collect Ollama results from findings
    for result_file in FINDINGS_DIR.glob("results_*.json"):
        if "openrouter" in result_file.name:
            continue
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                if 'summary' in data and 'metadata' in data:
                    all_results.append({
                        "provider": "ollama",
                        "model": data['metadata'].get('model', 'unknown'),
                        "accuracy": data['summary'].get('accuracy', 0),
                        "correct": data['summary'].get('correct', 0),
                        "total": data['metadata'].get('total_cases', 0),
                        "file": result_file.name
                    })
        except:
            pass

    # Collect OpenRouter results
    for result_file in FINDINGS_DIR.glob("results_openrouter_*.json"):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                if 'summary' in data and 'metadata' in data:
                    all_results.append({
                        "provider": "openrouter",
                        "model": data['metadata'].get('model', 'unknown'),
                        "accuracy": data['summary'].get('accuracy', 0),
                        "correct": data['summary'].get('correct', 0),
                        "total": data['metadata'].get('total_cases', 0),
                        "file": result_file.name
                    })
        except:
            pass

    # Sort by accuracy
    all_results.sort(key=lambda x: x['accuracy'], reverse=True)

    # Generate report
    report = ["# Model Comparison Report\n"]
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("## Results by Accuracy\n")
    report.append("| Rank | Provider | Model | Accuracy | Correct/Total |")
    report.append("|------|----------|-------|----------|---------------|")

    for i, r in enumerate(all_results, 1):
        report.append(f"| {i} | {r['provider']} | {r['model']} | {r['accuracy']:.2%} | {r['correct']}/{r['total']} |")

    report.append("")

    # Save report
    report_path = FINDINGS_DIR / "model_comparison.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"Report saved to: {report_path}")
    print('\n'.join(report))


def main():
    parser = argparse.ArgumentParser(description="Run classification with multiple models")
    parser.add_argument("--provider", choices=["ollama", "openrouter", "all"], default="all",
                        help="Which provider to use")
    parser.add_argument("--models", type=str, default=None,
                        help="Comma-separated list of specific models to run")
    parser.add_argument("--report-only", action="store_true",
                        help="Only generate comparison report from existing results")

    args = parser.parse_args()

    if args.report_only:
        generate_comparison_report()
        return

    run_results = []

    if args.models:
        models = [m.strip() for m in args.models.split(",")]
        # Determine provider based on model availability
        available_ollama = get_available_ollama_models()

        for model in models:
            if model in available_ollama:
                run_results.append(run_ollama_classification(model))
            else:
                run_results.append(run_openrouter_classification(model))
    else:
        # Run based on provider selection
        if args.provider in ["ollama", "all"]:
            available = get_available_ollama_models()
            print(f"Available Ollama models: {available}")

            for model in OLLAMA_MODELS:
                if model in available or any(model.split(':')[0] in m for m in available):
                    run_results.append(run_ollama_classification(model))

        if args.provider in ["openrouter", "all"]:
            import os
            if os.environ.get("OPENROUTER_API_KEY"):
                for model in OPENROUTER_MODELS:
                    run_results.append(run_openrouter_classification(model))
            else:
                print("Skipping OpenRouter: OPENROUTER_API_KEY not set")

    # Generate comparison report
    generate_comparison_report()

    # Summary
    print(f"\n{'='*60}")
    print("RUN SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in run_results if r and r.get('success'))
    print(f"Total runs: {len(run_results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(run_results) - successful}")


if __name__ == "__main__":
    main()
