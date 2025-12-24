#!/usr/bin/env python3
"""
Ollama inference wrapper for medical case classification.

Usage:
    from inference_ollama import OllamaClassifier
    classifier = OllamaClassifier(model="qwen3:latest")
    result = classifier.classify(case_json)
"""

import requests
import json
import time
from typing import Optional


class OllamaClassifier:
    """Wrapper for Ollama API for medical case classification."""

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

    def __init__(self, model: str = "qwen3:latest", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"

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
        entity_type = ""

        if entities:
            entity = entities[0]
            diagnose = entity.get('diagnose_kurz', '')
            entity_type = entity.get('entitaet_typ', '')

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

        # Handle models with <think> tags - look after </think>
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

    def classify(self, case: dict, temperature: float = 0.1) -> dict:
        """Classify a single case."""
        prompt = self.build_prompt(case)

        start_time = time.time()

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 200  # Increased for models with <think> tags
                    }
                },
                timeout=180
            )
            response.raise_for_status()

            result = response.json()
            raw_response = result.get("response", "")
            inference_time = time.time() - start_time

            classification = self.parse_response(raw_response)

            return {
                "classification": classification,
                "raw_response": raw_response,
                "inference_time": inference_time,
                "model": self.model,
                "success": True
            }

        except Exception as e:
            return {
                "classification": "error",
                "raw_response": str(e),
                "inference_time": time.time() - start_time,
                "model": self.model,
                "success": False
            }

    def check_connection(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                return self.model in models or self.model.split(":")[0] in [m.split(":")[0] for m in models]
            return False
        except:
            return False


def get_available_models(base_url: str = "http://localhost:11434") -> list:
    """Get list of available Ollama models."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            return [m["name"] for m in response.json().get("models", [])]
        return []
    except:
        return []


if __name__ == "__main__":
    # Test connection
    print("Testing Ollama connection...")
    models = get_available_models()
    print(f"Available models: {models}")

    if models:
        classifier = OllamaClassifier(model=models[0])
        print(f"Using model: {classifier.model}")
        print(f"Connection OK: {classifier.check_connection()}")
