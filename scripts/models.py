#!/usr/bin/env python3
"""
Pydantic models for structured input/output in medical case classification.

This module defines:
- CaseInput: Structured input from case JSON
- ClassificationOutput: Structured response with explanation + answer
- ClassificationResult: Full result including metadata
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# ENUMS
# =============================================================================

class CancerType(str, Enum):
    """Valid cancer type classifications."""
    nierenzellkarzinom = "nierenzellkarzinom"
    prostatakarzinom = "prostatakarzinom"
    hodentumor = "hodentumor"
    peniskarzinom = "peniskarzinom"
    urothelkarzinom = "urothelkarzinom"
    polymalignancy = "polymalignancy"
    non_urological = "non_urological"


class CancerTypeDE(str, Enum):
    """German display names for cancer types."""
    nierenzellkarzinom = "Nierenzellkarzinom (Nierenkrebs)"
    prostatakarzinom = "Prostatakarzinom (Prostatakrebs)"
    hodentumor = "Hodentumor (Hodenkrebs)"
    peniskarzinom = "Peniskarzinom (Peniskrebs)"
    urothelkarzinom = "Urothelkarzinom (Blasenkrebs)"
    polymalignancy = "Polymalignität (Mehrfachtumoren)"
    non_urological = "Nicht-urologisch"


# =============================================================================
# INPUT MODELS
# =============================================================================

class TNMStaging(BaseModel):
    """TNM staging information."""
    T: Optional[str] = Field(None, description="Tumor stage")
    N: Optional[str] = Field(None, description="Node stage")
    M: Optional[str] = Field(None, description="Metastasis stage")
    stage_group: Optional[str] = Field(None, description="Overall stage group")

    def to_string(self) -> str:
        """Convert to readable string."""
        parts = []
        if self.T: parts.append(f"T:{self.T}")
        if self.N: parts.append(f"N:{self.N}")
        if self.M: parts.append(f"M:{self.M}")
        return " ".join(parts) if parts else "Unbekannt"


class PatientInfo(BaseModel):
    """Patient demographic information."""
    alter_jahre: Optional[int] = Field(None, description="Age in years")
    geschlecht: Optional[str] = Field(None, description="Gender")
    ecog: Optional[int] = Field(None, description="ECOG performance status")
    komorbiditaet: Optional[str] = Field(None, description="Comorbidity level")


class CaseInput(BaseModel):
    """
    Structured input extracted from case JSON.
    Contains all relevant information for classification.
    """
    case_id: str = Field(..., description="Unique case identifier")

    # Patient info
    patient: PatientInfo = Field(default_factory=PatientInfo)

    # Clinical information
    anamnese: Optional[str] = Field(None, description="Medical history/anamnesis")
    diagnose_kurz: Optional[str] = Field(None, description="Short diagnosis")
    alle_diagnosen: Optional[List[str]] = Field(None, description="All diagnoses (for polymalignancy)")
    stadium: Optional[str] = Field(None, description="Stage or risk class")

    # Staging
    tnm_clinical: Optional[TNMStaging] = Field(None, description="Clinical TNM")
    tnm_pathological: Optional[TNMStaging] = Field(None, description="Pathological TNM")

    # Additional info
    histologie: Optional[str] = Field(None, description="Histology type")
    metastatic: Optional[bool] = Field(None, description="Whether metastatic")
    nebendiagnosen: Optional[List[str]] = Field(None, description="Secondary diagnoses")

    # Ground truth (for evaluation only, not sent to model)
    ground_truth: Optional[CancerType] = Field(None, description="Actual classification")

    @classmethod
    def from_case_json(cls, case_id: str, case: dict, ground_truth: str = None) -> "CaseInput":
        """Extract structured input from raw case JSON."""
        # Handle nested structure
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

        return cls(
            case_id=case_id,
            patient=PatientInfo(
                alter_jahre=patient_data.get('alter_jahre'),
                geschlecht=patient_data.get('geschlecht'),
                ecog=patient_data.get('performance_status', {}).get('ecog'),
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
            ground_truth=CancerType(ground_truth) if ground_truth else None
        )

    def to_prompt_text(self) -> str:
        """Convert to text for LLM prompt."""
        lines = []

        # Patient
        if self.patient.alter_jahre:
            lines.append(f"Patient: {self.patient.alter_jahre} Jahre")
        if self.patient.ecog is not None:
            lines.append(f"ECOG: {self.patient.ecog}")

        # Anamnesis (most important!)
        if self.anamnese:
            lines.append(f"Anamnese: {self.anamnese}")

        # Diagnosis - show ALL diagnoses if multiple
        if self.alle_diagnosen:
            for i, diag in enumerate(self.alle_diagnosen, 1):
                lines.append(f"Diagnose {i}: {diag}")
        elif self.diagnose_kurz:
            lines.append(f"Diagnose: {self.diagnose_kurz}")

        # Stage
        if self.stadium:
            lines.append(f"Stadium: {self.stadium}")

        # TNM
        if self.tnm_clinical:
            lines.append(f"TNM (klinisch): {self.tnm_clinical.to_string()}")
        if self.tnm_pathological:
            lines.append(f"TNM (pathologisch): {self.tnm_pathological.to_string()}")

        # Histology
        if self.histologie:
            lines.append(f"Histologie: {self.histologie}")

        # Metastatic status
        if self.metastatic is not None:
            lines.append(f"Metastasiert: {'Ja' if self.metastatic else 'Nein'}")

        # Secondary diagnoses
        if self.nebendiagnosen:
            lines.append(f"Nebendiagnosen: {', '.join(self.nebendiagnosen[:5])}")

        return "\n".join(lines)


# =============================================================================
# OUTPUT MODELS
# =============================================================================

class ClassificationOutput(BaseModel):
    """
    Structured output from the LLM.
    Contains both reasoning and final answer.
    """
    reasoning: str = Field(
        ...,
        description="Step-by-step explanation of how the classification was determined"
    )
    classification: CancerType = Field(
        ...,
        description="The final cancer type classification"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    key_indicators: Optional[List[str]] = Field(
        None,
        description="Key clinical indicators that led to this classification"
    )


class ClassificationResult(BaseModel):
    """
    Complete result of a classification attempt.
    Includes input, output, and metadata.
    """
    # Identifiers
    case_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # Model info
    provider: str = Field(..., description="'ollama' or 'openrouter'")
    model: str = Field(..., description="Model identifier")

    # Input
    input_case: CaseInput
    prompt_text: str = Field(..., description="Actual prompt sent to model")

    # Output
    output: Optional[ClassificationOutput] = Field(None, description="Structured output")
    raw_response: str = Field("", description="Raw model response")

    # Evaluation
    ground_truth: Optional[CancerType] = None
    is_correct: Optional[bool] = None

    # Performance
    inference_time_seconds: float = 0.0
    tokens_used: int = 0
    reasoning_tokens: int = 0

    # Status
    success: bool = True
    error_message: Optional[str] = None

    def evaluate(self) -> bool:
        """Check if prediction matches ground truth."""
        if self.output and self.ground_truth:
            self.is_correct = self.output.classification == self.ground_truth
            return self.is_correct
        return False


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

CLASSIFICATION_PROMPT = """Du bist ein erfahrener medizinischer Onkologe. Klassifiziere den folgenden Fall.

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


def build_prompt(case_input: CaseInput) -> str:
    """Build the full prompt from a CaseInput."""
    return CLASSIFICATION_PROMPT.format(case_text=case_input.to_prompt_text())


# =============================================================================
# JSON SCHEMA FOR API
# =============================================================================

def get_output_schema() -> dict:
    """Get JSON schema for structured output (OpenRouter/OpenAI format)."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "classification_output",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Step-by-step explanation in German"
                    },
                    "classification": {
                        "type": "string",
                        "enum": [e.value for e in CancerType],
                        "description": "Cancer type classification"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score"
                    },
                    "key_indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key clinical indicators"
                    }
                },
                "required": ["reasoning", "classification"],
                "additionalProperties": False
            }
        }
    }


if __name__ == "__main__":
    # Test the models
    print("=== Cancer Types ===")
    for ct in CancerType:
        print(f"  {ct.value}")

    print("\n=== Output Schema ===")
    import json
    print(json.dumps(get_output_schema(), indent=2))

    print("\n=== Sample Prompt ===")
    sample = CaseInput(
        case_id="test_1",
        patient=PatientInfo(alter_jahre=65, ecog=0),
        anamnese="Met. pap. RCC. Z. n. Nephrektomie links 2014",
        diagnose_kurz="Metastasiertes papilläres RCC",
        stadium="metastasiert",
        metastatic=True
    )
    print(build_prompt(sample))
