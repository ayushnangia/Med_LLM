#!/usr/bin/env python3
"""
Modal vLLM Judge Inference for LLM-as-a-Judge Evaluation

Generic batch inference with structured output (JSON schema) for judge evaluation.
Reuses vllm_image and MODEL_CONFIGS from modal_treatment_predict.py.

Usage:
    # Standalone test
    modal run scripts/modal_judge.py --results-dir results/modal_treatment/.../timestamp --model medgemma-27b --limit 3

    # Called programmatically from evaluate_treatment_llm_judge.py
"""

import modal
import json
import sys
from pathlib import Path
from typing import Optional

# Local import for vllm_image and MODEL_CONFIGS
sys.path.insert(0, str(Path(__file__).parent))
from modal_treatment_predict import vllm_image, MODEL_CONFIGS

# Add modal_treatment_predict to the image so it's importable inside the container
judge_image = vllm_image.add_local_python_source("modal_treatment_predict")

app = modal.App("ncc-judge-evaluation")


@app.function(
    image=judge_image,
    gpu="H100",
    timeout=1800,
    secrets=[modal.Secret.from_name("huggingface-secret-2")],
)
def run_judge_batch(model_key: str, prompts: list[str], json_schema: dict) -> list[dict]:
    """
    Generic batch vLLM inference with structured output for judge evaluation.

    Args:
        model_key: Key from MODEL_CONFIGS (e.g., "medgemma-27b")
        prompts: List of judge evaluation prompts
        json_schema: JSON schema dict for structured output

    Returns:
        List of {"text": str, "inference_time": float, "tokens_used": int}
    """
    import os
    import time
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    from modal_treatment_predict import MODEL_CONFIGS

    cfg = MODEL_CONFIGS[model_key]
    hf_id = cfg["hf_id"]

    # HuggingFace auth
    import torch
    from huggingface_hub import login

    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print(f"HF_TOKEN: {hf_token[:8]}...{hf_token[-4:]}")
        login(token=hf_token)
    else:
        raise RuntimeError("HF_TOKEN not found!")

    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)

    # Batch invariance for determinism
    is_multimodal = cfg.get("multimodal", False)
    if not is_multimodal:
        os.environ["VLLM_BATCH_INVARIANT"] = "1"

    print(f"Loading {hf_id} for judge evaluation...")
    llm = LLM(
        model=hf_id,
        trust_remote_code=True,
        dtype="bfloat16",
        seed=42,
        max_model_len=32768,
        enforce_eager=True,
        disable_log_stats=True,
    )
    print("Model loaded!")

    # Structured output params
    structured = StructuredOutputsParams(json=json_schema)
    params = SamplingParams(
        temperature=0.3,
        top_p=0.95,
        max_tokens=2048,
        seed=42,
        structured_outputs=structured,
    )

    print(f"Running judge inference on {len(prompts)} prompts (structured output)...")
    start = time.time()
    outputs = llm.generate(prompts, params)
    total_time = time.time() - start
    per_prompt = total_time / len(prompts) if prompts else 0

    results = []
    for output in outputs:
        text = output.outputs[0].text.strip()
        tokens = len(output.outputs[0].token_ids)
        results.append({
            "text": text,
            "inference_time": per_prompt,
            "tokens_used": tokens,
        })

    print(f"Judge inference complete: {len(results)} results in {total_time:.1f}s")
    return results


@app.local_entrypoint()
def main(
    results_dir: str,
    model: str = "medgemma-27b",
    limit: int = 0,
):
    """Standalone test entrypoint for Modal judge inference."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from evaluate_treatment_llm_judge import build_judge_prompt, parse_judge_response, JudgeEvaluation

    results_path = Path(results_dir)
    if not results_path.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    case_files = sorted(results_path.glob("ncc_*.json"))
    if limit > 0:
        case_files = case_files[:limit]

    print(f"Loading {len(case_files)} cases from {results_dir}")

    # Build prompts
    prompts = []
    case_ids = []
    for cf in case_files:
        with open(cf, 'r', encoding='utf-8') as f:
            case_result = json.load(f)
        prompts.append(build_judge_prompt(case_result))
        case_ids.append(case_result.get("case_id", cf.stem))

    # Run batch inference on Modal
    json_schema = JudgeEvaluation.model_json_schema()
    results = run_judge_batch.remote(model, prompts, json_schema)

    # Parse and display results
    print(f"\n{'='*60}")
    print(f"Judge Results ({model})")
    print(f"{'='*60}")

    for case_id, result in zip(case_ids, results):
        evaluation = parse_judge_response(result["text"])
        if evaluation:
            status = "CORRECT" if evaluation.is_correct else "INCORRECT"
            print(f"{case_id}: {status} | Score: {evaluation.overall_score:.2f} | {result['tokens_used']} tokens")
        else:
            print(f"{case_id}: PARSE FAILED | Raw: {result['text'][:100]}...")
