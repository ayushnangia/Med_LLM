#!/usr/bin/env python3
"""
OpenRouter inference client for medical case classification.

Usage:
    from inference_openrouter import OpenRouterClassifier

    classifier = OpenRouterClassifier(model="google/gemma-3-27b-it")
    result = classifier.classify(case_json)

Environment:
    OPENROUTER_API_KEY - Your OpenRouter API key
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


class OpenRouterClassifier:
    """OpenRouter API wrapper for medical case classification."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Model mapping: short name -> OpenRouter model ID
    MODEL_REGISTRY = {
        # Gemma models
        "gemma3:27b": "google/gemma-3-27b-it",
        "gemma3:12b": "google/gemma-3-12b-it",
        "gemma3:4b": "google/gemma-3-4b-it",
        "gemma-3-27b": "google/gemma-3-27b-it",
        "gemma-3-12b": "google/gemma-3-12b-it",
        "gemma-3-4b": "google/gemma-3-4b-it",

        # Qwen3 models
        "qwen3:30b": "qwen/qwen3-30b-a3b",
        "qwen3:8b": "qwen/qwen3-8b",
        "qwen3:4b": "qwen/qwen3-4b",
        "qwen3-30b": "qwen/qwen3-30b-a3b",
        "qwen3-8b": "qwen/qwen3-8b",
        "qwen3-4b": "qwen/qwen3-4b",

        # Qwen2.5 models
        "qwen2.5:14b-instruct": "qwen/qwen-2.5-14b-instruct",
        "qwen2.5:72b-instruct": "qwen/qwen-2.5-72b-instruct",
        "qwen2.5-14b": "qwen/qwen-2.5-14b-instruct",

        # Llama models
        "llama3:8b": "meta-llama/llama-3-8b-instruct",
        "llama3:70b": "meta-llama/llama-3-70b-instruct",
        "llama3.1:8b": "meta-llama/llama-3.1-8b-instruct",
        "llama3.1:70b": "meta-llama/llama-3.1-70b-instruct",
        "llama3.3:70b": "meta-llama/llama-3.3-70b-instruct",

        # Mistral models
        "mistral:7b-instruct": "mistralai/mistral-7b-instruct",
        "mixtral:8x7b": "mistralai/mixtral-8x7b-instruct",
        "mixtral:8x22b": "mistralai/mixtral-8x22b-instruct",

        # GLM models
        "glm-4": "thudm/glm-4-9b",
        "glm4": "thudm/glm-4-9b",

        # Claude models (for comparison)
        "claude-3-haiku": "anthropic/claude-3-haiku",
        "claude-3-sonnet": "anthropic/claude-3-sonnet",
        "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",

        # GPT models (for comparison)
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gpt-4o": "openai/gpt-4o",
    }

    VALID_CLASSES = [
        "nierenzellkarzinom",
        "prostatakarzinom",
        "hodentumor",
        "peniskarzinom",
        "urothelkarzinom",
        "polymalignancy",
        "non_urological"
    ]

    CLASS_ALIASES = {
        # Kidney cancer
        "ncc": "nierenzellkarzinom",
        "nierenkrebs": "nierenzellkarzinom",
        "rcc": "nierenzellkarzinom",
        "kidney": "nierenzellkarzinom",
        "renal cell": "nierenzellkarzinom",
        "nierentumor": "nierenzellkarzinom",
        "nierenkarzinom": "nierenzellkarzinom",
        # Prostate cancer
        "pca": "prostatakarzinom",
        "prostatakrebs": "prostatakarzinom",
        "prostate": "prostatakarzinom",
        "prostata": "prostatakarzinom",
        # Testicular cancer
        "hoden": "hodentumor",
        "hodenkrebs": "hodentumor",
        "testicular": "hodentumor",
        "hodenkarzinom": "hodentumor",
        "seminom": "hodentumor",
        "seminoma": "hodentumor",
        "germ cell": "hodentumor",
        "keimzelltumor": "hodentumor",
        # Penile cancer
        "penis": "peniskarzinom",
        "peniskrebs": "peniskarzinom",
        "penile": "peniskarzinom",
        # Urothelial cancer
        "uca": "urothelkarzinom",
        "urothelial": "urothelkarzinom",
        "blasenkrebs": "urothelkarzinom",
        "bladder": "urothelkarzinom",
        "blasenkarzinom": "urothelkarzinom",
        "harnblase": "urothelkarzinom",
        # Polymalignancy
        "combi": "polymalignancy",
        "combined": "polymalignancy",
        "mehrfach": "polymalignancy",
        "multiple": "polymalignancy",
        "poly": "polymalignancy",
        # Non-urological
        "non_uro": "non_urological",
        "nicht-urologisch": "non_urological",
        "non-urological": "non_urological",
        "lymphom": "non_urological",
        "lymphoma": "non_urological",
    }

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 200,
        site_url: str = "https://github.com/med-llm",
        site_name: str = "Med_LLM Classification"
    ):
        """
        Initialize OpenRouter classifier.

        Args:
            model: Model name (short or full OpenRouter ID)
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            site_url: Your site URL (for OpenRouter ranking)
            site_name: Your app name (for OpenRouter ranking)
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # Resolve model name
        self.model_input = model
        self.model = self.MODEL_REGISTRY.get(model, model)

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.site_url = site_url
        self.site_name = site_name

        # Track usage
        self.total_tokens = 0
        self.total_cost = 0.0

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary."""
        return {
            "provider": "openrouter",
            "model_input": self.model_input,
            "model_id": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "site_url": self.site_url,
            "site_name": self.site_name
        }

    def build_prompt(self, case: dict) -> str:
        """Build classification prompt from case JSON."""
        # Extract patient info
        patient = case.get('patient', {})
        if not patient.get('nachname') and 'case_template' in case:
            patient = case.get('case_template', {}).get('patient', {})

        nachname = patient.get('nachname', 'Unbekannt')
        vorname = patient.get('vorname', '')
        alter = patient.get('alter_jahre', 'Unbekannt')

        # Extract entity info
        entities = case.get('entitaeten', [])
        if not entities and 'case_template' in case:
            entities = case.get('case_template', {}).get('entitaeten', [])

        diagnose = ""
        tnm = ""

        if entities:
            entity = entities[0]
            diagnose = entity.get('diagnose_kurz', '')

            klassifikation = entity.get('klassifikation', {})
            tnm_clin = klassifikation.get('tnm_clinical', {})
            if tnm_clin:
                t = tnm_clin.get('T', '')
                n = tnm_clin.get('N', '')
                m = tnm_clin.get('M', '')
                tnm = f"T:{t} N:{n} M:{m}"

        prompt = f"""Du bist ein medizinischer Experte für Onkologie. Analysiere den folgenden klinischen Fall und klassifiziere die Tumorentität.

FALL:
Patient: {nachname}, {vorname}, {alter} Jahre
Diagnose: {diagnose}
TNM-Staging: {tnm}

KLASSIFIZIERE in GENAU eine der folgenden Kategorien:
- nierenzellkarzinom (Nierenkrebs/RCC)
- prostatakarzinom (Prostatakrebs)
- hodentumor (Hodenkrebs)
- peniskarzinom (Peniskrebs)
- urothelkarzinom (Blasen-/Harnwegskrebs)
- polymalignancy (Mehrfachtumoren)
- non_urological (Nicht-urologisch)

Antworte NUR mit dem Kategorienamen, ohne Erklärung:"""

        return prompt

    def parse_response(self, response: str) -> str:
        """Parse model response to extract classification."""
        original = response
        response = response.lower().strip()

        # Handle models with <think> tags
        if '</think>' in response:
            parts = response.split('</think>')
            if len(parts) > 1:
                response = parts[-1].strip()

        # Remove common prefixes
        for prefix in ["die kategorie ist", "kategorie:", "antwort:", "classification:", "answer:"]:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()

        # Check for exact match first
        for cls in self.VALID_CLASSES:
            if cls in response:
                return cls

        # Check aliases
        for alias, cls in self.CLASS_ALIASES.items():
            if alias in response:
                return cls

        # If no match in post-think section, check entire response
        for cls in self.VALID_CLASSES:
            if cls in original.lower():
                return cls

        for alias, cls in self.CLASS_ALIASES.items():
            if alias in original.lower():
                return cls

        return "unknown"

    def classify(self, case: dict) -> dict:
        """Classify a single case using OpenRouter API."""
        prompt = self.build_prompt(case)
        start_time = time.time()

        try:
            response = requests.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                },
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            inference_time = time.time() - start_time

            # Extract response content
            raw_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Track usage
            usage = result.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            self.total_tokens += tokens_used

            classification = self.parse_response(raw_response)

            return {
                "classification": classification,
                "raw_response": raw_response,
                "inference_time": inference_time,
                "model": self.model,
                "tokens_used": tokens_used,
                "success": True
            }

        except requests.exceptions.RequestException as e:
            return {
                "classification": "error",
                "raw_response": str(e),
                "inference_time": time.time() - start_time,
                "model": self.model,
                "tokens_used": 0,
                "success": False
            }

    def check_connection(self) -> bool:
        """Check if OpenRouter API is accessible."""
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    @classmethod
    def list_available_models(cls) -> List[str]:
        """List all registered model shortcuts."""
        return list(cls.MODEL_REGISTRY.keys())


def get_openrouter_models(api_key: Optional[str] = None) -> List[Dict]:
    """Fetch list of available models from OpenRouter API."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return []

    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("data", [])
        return []
    except:
        return []


if __name__ == "__main__":
    # Test connection
    print("OpenRouter Classifier")
    print("=" * 40)

    print("\nRegistered model shortcuts:")
    for short, full in OpenRouterClassifier.MODEL_REGISTRY.items():
        print(f"  {short} -> {full}")

    # Check API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        print(f"\nAPI Key: {'*' * 20}{api_key[-4:]}")

        # Test connection
        try:
            classifier = OpenRouterClassifier(model="gemma3:4b")
            if classifier.check_connection():
                print("Connection: OK")
            else:
                print("Connection: FAILED")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\nNo API key found. Set OPENROUTER_API_KEY environment variable.")
