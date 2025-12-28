#!/usr/bin/env python3
"""
Modal vLLM Classification - Single Container

Usage:
    modal run scripts/modal_classify.py --model medgemma-4b
    modal run scripts/modal_classify.py --list-models
"""

import modal
import json
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

app = modal.App("med-llm")

# =============================================================================
# PYDANTIC MODELS (matching scripts/models.py)
# =============================================================================

class CancerType(str, Enum):
    nierenzellkarzinom = "nierenzellkarzinom"
    prostatakarzinom = "prostatakarzinom"
    hodentumor = "hodentumor"
    peniskarzinom = "peniskarzinom"
    urothelkarzinom = "urothelkarzinom"
    polymalignancy = "polymalignancy"
    non_urological = "non_urological"

class TNMStaging(BaseModel):
    T: Optional[str] = None
    N: Optional[str] = None
    M: Optional[str] = None
    stage_group: Optional[str] = None

class PatientInfo(BaseModel):
    alter_jahre: Optional[int] = None
    geschlecht: Optional[str] = None
    ecog: Optional[int] = None
    komorbiditaet: Optional[str] = None

class CaseInput(BaseModel):
    case_id: str
    patient: PatientInfo = Field(default_factory=PatientInfo)
    anamnese: Optional[str] = None
    diagnose_kurz: Optional[str] = None
    alle_diagnosen: Optional[List[str]] = None
    stadium: Optional[str] = None
    tnm_clinical: Optional[TNMStaging] = None
    tnm_pathological: Optional[TNMStaging] = None
    histologie: Optional[str] = None
    metastatic: Optional[bool] = None
    nebendiagnosen: Optional[List[str]] = None
    ground_truth: Optional[str] = None

class ClassificationOutput(BaseModel):
    """Structured output matching OpenRouter format."""
    reasoning: str = Field(..., description="Step-by-step explanation in German")
    classification: CancerType = Field(..., description="Cancer type classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    key_indicators: List[str] = Field(..., description="Key clinical indicators")

class ClassificationResult(BaseModel):
    """Complete result matching OpenRouter format."""
    case_id: str
    timestamp: str
    provider: str = "modal"
    model: str
    input_case: CaseInput
    prompt_text: str
    output: Optional[ClassificationOutput] = None
    raw_response: str = ""
    ground_truth: Optional[str] = None
    is_correct: Optional[bool] = None
    inference_time_seconds: float = 0.0
    tokens_used: int = 0
    reasoning_tokens: int = 0
    success: bool = True
    error_message: Optional[str] = None


# =============================================================================
# MODELS
# =============================================================================

MODELS = {
    # Gemma 3 models are multimodal (Gemma3ForConditionalGeneration) - no batch invariance support
    "gemma-3-27b": {"hf_id": "google/gemma-3-27b-it", "category": "open_source", "multimodal": True},
    "gemma-3-4b": {"hf_id": "google/gemma-3-4b-it", "category": "open_source", "multimodal": True},
    # Text-only models - batch invariance supported
    "olmo-3.1-32b-instruct": {"hf_id": "allenai/Olmo-3.1-32B-Instruct", "category": "open_source", "temperature": 0.6, "top_p": 0.95},
    "olmo-3.1-32b-think": {"hf_id": "allenai/Olmo-3.1-32B-Think", "category": "open_source", "temperature": 0.6, "top_p": 0.95, "thinking": True},
    # Nemotron: Mamba hybrid doesn't fit on single H100, and doesn't support TP
    # "nemotron-3-nano-30b": {"hf_id": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16", "category": "open_source", "temperature": 1.0, "top_p": 1.0, "thinking": True, "hybrid": True},
    # MedGemma - 27b is text-only, 4b is multimodal
    "medgemma-27b": {"hf_id": "google/medgemma-27b-text-it", "category": "medical", "gated": True},
    "medgemma-4b": {"hf_id": "google/medgemma-4b-it", "category": "medical", "gated": True, "multimodal": True},
    "meditron3-7b": {"hf_id": "OpenMeditron/Meditron3-Qwen2.5-7B", "category": "medical"},
}

CLASSES = ["nierenzellkarzinom", "prostatakarzinom", "hodentumor", "peniskarzinom", "urothelkarzinom", "polymalignancy", "non_urological"]
FOLDER_TO_CLASS = {"ncc": "nierenzellkarzinom", "pca": "prostatakarzinom", "hoden_ca": "hodentumor", "penis_ca": "peniskarzinom", "uca": "urothelkarzinom", "combi": "polymalignancy", "non_uro": "non_urological"}
ALIASES = {"ncc": "nierenzellkarzinom", "rcc": "nierenzellkarzinom", "kidney": "nierenzellkarzinom", "pca": "prostatakarzinom", "prostate": "prostatakarzinom", "hoden": "hodentumor", "testicular": "hodentumor", "penis": "peniskarzinom", "uca": "urothelkarzinom", "bladder": "urothelkarzinom", "combi": "polymalignancy", "non_uro": "non_urological", "lymphom": "non_urological"}

# Image - batch invariance settings applied dynamically per model
vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5.0", "transformers>=4.46.0", "accelerate>=0.34.0", "huggingface_hub>=0.26.0")
    .run_commands("pip install vllm --pre --extra-index-url https://wheels.vllm.ai/nightly")
    .run_commands("pip install flashinfer-python -i https://flashinfer.ai/whl/cu124/torch2.6/")
    .pip_install("torch-c-dlpack-ext")
    .env({
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        "PYTHONHASHSEED": "42",
    })
)


def extract_case_input(case_id: str, case: dict, ground_truth: str) -> CaseInput:
    """Extract structured input from raw case JSON."""
    patient_data = case.get('patient', {})
    if not patient_data.get('alter_jahre') and 'case_template' in case:
        patient_data = case.get('case_template', {}).get('patient', {})

    entities = case.get('entitaeten', [])
    if not entities and 'case_template' in case:
        entities = case.get('case_template', {}).get('entitaeten', [])

    entity = entities[0] if entities else {}
    klassifikation = entity.get('klassifikation', {})
    quick_access = entity.get('quick_access', {})

    # Extract ALL diagnoses for polymalignancy detection
    alle_diagnosen = []
    for ent in entities:
        diag = ent.get('diagnose_kurz')
        if diag:
            alle_diagnosen.append(diag)

    # Extract TNM
    tnm_clin = klassifikation.get('tnm_clinical', {})
    tnm_path = klassifikation.get('tnm_pathological', {})

    return CaseInput(
        case_id=case_id,
        patient=PatientInfo(
            alter_jahre=patient_data.get('alter_jahre'),
            geschlecht=patient_data.get('geschlecht'),
            ecog=patient_data.get('performance_status', {}).get('ecog') if isinstance(patient_data.get('performance_status'), dict) else None,
            komorbiditaet=patient_data.get('komorbiditaet_level')
        ),
        anamnese=case.get('anamnese_freitext'),
        diagnose_kurz=entity.get('diagnose_kurz'),
        alle_diagnosen=alle_diagnosen if len(alle_diagnosen) > 1 else None,
        stadium=entity.get('stadium_oder_risikoklasse'),
        tnm_clinical=TNMStaging(
            T=tnm_clin.get('T'),
            N=tnm_clin.get('N'),
            M=tnm_clin.get('M'),
            stage_group=tnm_clin.get('stage_group')
        ) if tnm_clin else None,
        tnm_pathological=TNMStaging(
            T=tnm_path.get('T'),
            N=tnm_path.get('N'),
            M=tnm_path.get('M'),
            stage_group=tnm_path.get('stage_group')
        ) if tnm_path else None,
        histologie=klassifikation.get('histologie') or entity.get('histologie'),
        metastatic=quick_access.get('metastatic'),
        nebendiagnosen=case.get('nebendiagnosen'),
        ground_truth=ground_truth
    )


def build_prompt(case_input: CaseInput) -> str:
    """Build prompt from CaseInput."""
    lines = []
    if case_input.patient.alter_jahre:
        lines.append(f"Patient: {case_input.patient.alter_jahre} Jahre")
    if case_input.patient.ecog is not None:
        lines.append(f"ECOG: {case_input.patient.ecog}")
    if case_input.anamnese:
        lines.append(f"Anamnese: {case_input.anamnese}")
    if case_input.alle_diagnosen:
        for i, diag in enumerate(case_input.alle_diagnosen, 1):
            lines.append(f"Diagnose {i}: {diag}")
    elif case_input.diagnose_kurz:
        lines.append(f"Diagnose: {case_input.diagnose_kurz}")
    if case_input.stadium:
        lines.append(f"Stadium: {case_input.stadium}")
    if case_input.tnm_clinical:
        parts = []
        if case_input.tnm_clinical.T: parts.append(f"T:{case_input.tnm_clinical.T}")
        if case_input.tnm_clinical.N: parts.append(f"N:{case_input.tnm_clinical.N}")
        if case_input.tnm_clinical.M: parts.append(f"M:{case_input.tnm_clinical.M}")
        if parts:
            lines.append(f"TNM (klinisch): {' '.join(parts)}")
    if case_input.tnm_pathological:
        parts = []
        if case_input.tnm_pathological.T: parts.append(f"T:{case_input.tnm_pathological.T}")
        if case_input.tnm_pathological.N: parts.append(f"N:{case_input.tnm_pathological.N}")
        if case_input.tnm_pathological.M: parts.append(f"M:{case_input.tnm_pathological.M}")
        if parts:
            lines.append(f"TNM (pathologisch): {' '.join(parts)}")
    if case_input.histologie:
        lines.append(f"Histologie: {case_input.histologie}")
    if case_input.metastatic is not None:
        lines.append(f"Metastasiert: {'Ja' if case_input.metastatic else 'Nein'}")
    if case_input.nebendiagnosen:
        lines.append(f"Nebendiagnosen: {', '.join(case_input.nebendiagnosen[:5])}")

    case_text = "\n".join(lines)

    return f"""Du bist ein erfahrener medizinischer Onkologe. Klassifiziere den folgenden Fall.

FALL:
{case_text}

Klassifiziere in EINE Kategorie:
- nierenzellkarzinom
- prostatakarzinom
- hodentumor
- peniskarzinom
- urothelkarzinom
- polymalignancy
- non_urological

Antwort als JSON:
{{
    "reasoning": "Begründung",
    "classification": "kategorie",
    "confidence": 0.0-1.0,
    "key_indicators": ["..."]
}}"""


def parse_response(text: str) -> str:
    orig = text
    text = text.lower().strip()
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    for cls in CLASSES:
        if cls in text:
            return cls
    for alias, cls in ALIASES.items():
        if alias in text:
            return cls
    for cls in CLASSES:
        if cls in orig.lower():
            return cls
    return "unknown"


@app.function(
    image=vllm_image,
    gpu="H100",
    timeout=7200,
    retries=0,
    secrets=[modal.Secret.from_name("huggingface-secret-2")],
)
def run_classification(model_key: str, cases: list[dict], run_timestamp: str) -> dict:
    """Single H100 classification."""
    return _run_classification_impl(model_key, cases, run_timestamp, tensor_parallel=1)


@app.function(
    image=vllm_image,
    gpu="H100:2",
    timeout=7200,
    retries=0,
    secrets=[modal.Secret.from_name("huggingface-secret-2")],
)
def run_classification_tp2(model_key: str, cases: list[dict], run_timestamp: str) -> dict:
    """2x H100 with tensor parallelism for large models."""
    return _run_classification_impl(model_key, cases, run_timestamp, tensor_parallel=2)


def _run_classification_impl(model_key: str, cases: list[dict], run_timestamp: str, tensor_parallel: int = 1) -> dict:
    """Shared implementation for classification."""
    import os
    import time
    import torch
    from huggingface_hub import login
    from vllm import LLM, SamplingParams

    cfg = MODELS[model_key]

    # Enable batch invariance for compatible models (not multimodal or hybrid)
    if not cfg.get("multimodal") and not cfg.get("hybrid"):
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
        os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
        print("Batch invariance: ENABLED (FLASH_ATTN)")
    elif cfg.get("hybrid"):
        print("Batch invariance: DISABLED (hybrid Mamba+Attention model)")
    else:
        print("Batch invariance: DISABLED (multimodal model)")

    # Login
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print(f"HF_TOKEN: {hf_token[:8]}...{hf_token[-4:]}")
        login(token=hf_token)
    else:
        raise RuntimeError("HF_TOKEN not found!")

    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)

    print(f"Loading {cfg['hf_id']} (TP={tensor_parallel})...")

    # Reduce context for hybrid models (Mamba state uses extra memory)
    max_len = 16384 if cfg.get("hybrid") else 32768

    llm = LLM(
        model=cfg["hf_id"],
        dtype="bfloat16",
        max_model_len=max_len,
        trust_remote_code=True,
        seed=42,
        enforce_eager=True,
        tensor_parallel_size=tensor_parallel,
    )
    print("Model loaded!")

    # Extract case inputs and build prompts
    case_inputs = []
    prompts = []
    for c in cases:
        case_input = extract_case_input(c["case_id"], c["case_data"], c["ground_truth"])
        case_inputs.append(case_input)
        prompts.append(build_prompt(case_input))

    # Sampling params
    temp = cfg.get("temperature", 0.1)
    top_p = cfg.get("top_p", 1.0)
    # Need more tokens for reasoning output (reasoning + classification + confidence + key_indicators)
    max_tokens = 4096 if cfg.get("thinking") else 1024

    # For thinking models, disable structured output to allow free-form reasoning
    # For other models, use structured output for reliable JSON
    is_thinking = cfg.get("thinking", False)

    if is_thinking:
        # Thinking models: free-form generation, parse JSON manually
        params = SamplingParams(
            temperature=temp,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=42,
        )
        print(f"Running inference on {len(cases)} cases (free-form for thinking model)...")
    else:
        # Other models: use structured output for reliable JSON
        from vllm.sampling_params import StructuredOutputsParams
        json_schema = ClassificationOutput.model_json_schema()
        structured = StructuredOutputsParams(json=json_schema)
        params = SamplingParams(
            temperature=temp,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=42,
            structured_outputs=structured,
        )
        print(f"Running inference on {len(cases)} cases (structured output)...")
    start = time.time()
    outputs = llm.generate(prompts, params)
    total_time = time.time() - start

    # Parse results with Pydantic validation
    import re
    results = []
    for i, out in enumerate(outputs):
        text = out.outputs[0].text
        pred = "unknown"
        output_obj = None
        success = True
        error_msg = None

        try:
            # For thinking models, extract JSON from free-form output
            json_text = text
            if is_thinking:
                # Remove thinking tags if present
                if "</think>" in text:
                    json_text = text.split("</think>")[-1].strip()
                # Find JSON in the response
                json_match = re.search(r'\{[^{}]*"classification"[^{}]*\}', json_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)

            # Parse JSON and validate with Pydantic
            parsed = ClassificationOutput.model_validate_json(json_text)
            pred = parsed.classification.value
            output_obj = parsed
        except Exception as e:
            # Fallback to regex parsing if structured output fails
            print(f"Warning: Pydantic validation failed for case {i}, falling back to regex: {e}")
            pred = parse_response(text)
            error_msg = str(e)
            success = pred != "unknown"
            # For thinking models, try to extract reasoning from raw text
            if is_thinking and output_obj is None:
                try:
                    # Try to build a partial output object
                    output_obj = ClassificationOutput(
                        reasoning=text[:500] if len(text) > 500 else text,
                        classification=CancerType(pred) if pred in [c.value for c in CancerType] else CancerType.non_urological,
                        confidence=0.5,
                        key_indicators=[]
                    )
                except:
                    pass

        result = ClassificationResult(
            case_id=case_inputs[i].case_id,
            timestamp=run_timestamp,
            provider="modal",
            model=cfg["hf_id"],
            input_case=case_inputs[i],
            prompt_text=prompts[i],
            output=output_obj,
            raw_response=text,
            ground_truth=case_inputs[i].ground_truth,
            is_correct=pred == case_inputs[i].ground_truth,
            inference_time_seconds=total_time / len(cases),  # Average per case
            tokens_used=len(out.outputs[0].token_ids) if out.outputs else 0,
            reasoning_tokens=0,
            success=success,
            error_message=error_msg,
        )
        results.append(result)

    return {"results": [r.model_dump() for r in results], "time": total_time}


@app.local_entrypoint()
def main(model: str = "medgemma-4b", list_models: bool = False):
    if list_models:
        print("\nAvailable models:")
        for k, v in MODELS.items():
            print(f"  {k}: {v['hf_id']}")
        return

    if model not in MODELS:
        print(f"Unknown model: {model}\nAvailable: {list(MODELS.keys())}")
        return

    # Load cases
    base = Path(__file__).parent.parent
    data_dir = base / "converted_data" / "send_23_12_25"

    cases = []
    for folder, gt in FOLDER_TO_CLASS.items():
        folder_path = data_dir / folder
        if not folder_path.exists():
            continue
        for jf in folder_path.glob("*_cases_json.json"):
            with open(jf) as f:
                data = json.load(f)
            for i, c in enumerate(data.get("cases", [])):
                cases.append({"case_id": f"{folder}_{i+1}", "ground_truth": gt, "case_data": c})

    cfg = MODELS[model]
    use_tp2 = cfg.get("hybrid", False)

    # Generate timestamp for this run
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    print(f"\nModel: {model}")
    print(f"HuggingFace: {cfg['hf_id']}")
    print(f"Cases: {len(cases)}")
    print(f"GPU: {'2x H100 (TP=2)' if use_tp2 else 'H100'}")
    print(f"Timestamp: {run_timestamp}")
    print("-" * 50)

    # Run on Modal - use TP2 for hybrid models
    if use_tp2:
        result = run_classification_tp2.remote(model, cases, run_timestamp)
    else:
        result = run_classification.remote(model, cases, run_timestamp)

    # Results
    correct = sum(1 for r in result["results"] if r["is_correct"])
    total = len(result["results"])
    accuracy = correct / total if total else 0

    print(f"\nAccuracy: {accuracy:.2%} ({correct}/{total})")
    print(f"Time: {result['time']:.1f}s")

    # Save - format matching OpenRouter: results/modal/{model_slug}/{timestamp}/
    # Convert HF ID to lowercase slug (e.g., "google/medgemma-4b-it" -> "google_medgemma-4b-it")
    model_slug = cfg["hf_id"].lower().replace("/", "_").replace(":", "_")
    out_dir = base / "results" / "modal" / model_slug / run_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save individual case files
    for r in result["results"]:
        case_file = out_dir / f"{r['case_id']}.json"
        with open(case_file, 'w', encoding='utf-8') as f:
            json.dump(r, f, indent=2, ensure_ascii=False, default=str)

    # Save summary
    summary = {
        "model": cfg["hf_id"],
        "provider": "modal",
        "timestamp": run_timestamp,
        "total_cases": total,
        "correct": correct,
        "incorrect": total - correct,
        "errors": sum(1 for r in result["results"] if not r["success"]),
        "accuracy": accuracy,
        "total_time": result["time"],
        "batch_invariance": not cfg.get("multimodal") and not cfg.get("hybrid"),
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved: {out_dir}")
