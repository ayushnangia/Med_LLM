// TypeScript interfaces for Medical Review Site

export interface PatientInfo {
  name: string;
  age: number | null;
  ecog: number | null;
  karnofsky: number | null;
  comorbidity: string;
  life_expectancy?: string;
  karnofsky_from_labor?: number | null;  // v1.0 schema stores Karnofsky in lab section
}

export interface Medication {
  wirkstoff_oder_klasse?: string;  // v1.1 schema
  wirkstoff?: string;               // v1.0 schema
  details?: string | null;
  hinweis?: string | null;          // v1.0 schema
  dosierung?: string | null;
  schema?: string | null;
}

export interface ImagingFinding {
  modalitaet: string;
  region: string;
  datum: string | null;
  befund_kurz: string;
}

export interface PathologyReport {
  datum: string | null;
  material: string;
  diagnose: string;
  details: Record<string, string> | null;
}

export interface TherapyProcedure {
  datum?: string | null;           // v1.1 schema
  datum_start?: string | null;     // v1.0 schema
  datum_ende?: string | null;
  typ: string;
  beschreibung?: string;           // v1.1 schema
  regime?: string;                 // v1.0 schema
  intent?: string;
  linie?: number;                  // Line number (1st, 2nd, etc.)
  status?: string;
  details?: string | null;
  klasse?: string[];
}

export interface TNMStaging {
  T: string | null;
  T_sub?: string | null;
  N: string | null;
  M: string | null;
  stage_group?: string | null;
}

// Secondary diagnosis can be either a simple string or an object with diagnose and details
export type SecondaryDiagnosis = string | { diagnose: string; details?: string };

export interface ClinicalContext {
  anamnese_freitext?: string;
  fragestellung?: string | string[];  // Can be single string or array of questions
  nebendiagnosen?: SecondaryDiagnosis[];
  medikation?: Medication[];
  bildgebung?: ImagingFinding[];
  pathologie?: PathologyReport[];
  therapien_und_eingriffe?: TherapyProcedure[];
}

export interface DiagnosisInfo {
  diagnose_kurz: string;
  stadium: string;
  histologie_subtyp: string;
  klarzellig: boolean | null;
  tnm_cM: string;
  tnm_clinical?: TNMStaging;
  tnm_pathological?: TNMStaging;
  tnm_string?: string;  // v1.0 schema uses single TNM string
  grading?: string | null;
  imdc_risiko?: string | null;
}

export interface GroundTruth {
  metastatic: boolean;
  therapy: string;
}

export interface JudgeEvaluation {
  is_correct: boolean;
  correctness_reason: string;
  semantic_match: boolean;
  semantic_score: number;
  clinical_appropriate: boolean;
  clinical_score: number;
  reasoning_quality: number;
  reasoning_critique: string;
  overall_score: number;
  judge_reasoning: string;
  inference_time_s: number;
}

export interface DoctorReview {
  therapy_acceptable_ra: boolean;
  recommendation_exact_match: number;
  recommendation_patient_oriented: number;
  prediction_quality: number;
}

export interface ModelPrediction {
  model_id: string;
  pred_metastatic: boolean;
  pred_imdc_risk: string;
  pred_therapy: string;
  pred_category: string;
  pred_confidence: number;
  pred_reasoning: string;
  metastatic_correct: boolean;
  therapy_exact_match: boolean;
  therapy_acceptable: boolean;
  judge_evaluation: JudgeEvaluation;            // default judge (GPT-5.2)
  judge_evaluations: Record<string, JudgeEvaluation>; // all judges keyed by judge model ID
  inference_time_s: number;
  doctor_review: DoctorReview | null;
}

export interface Case {
  case_id: string;
  patient: PatientInfo;
  diagnosis: DiagnosisInfo;
  clinical_context?: ClinicalContext;
  ground_truth: GroundTruth;
  predictions: Record<string, ModelPrediction>;
}

export interface ModelSummary {
  model_id: string;
  display_name: string;
  total_cases: number;
  metastatic_accuracy: number;
  therapy_exact_match_rate: number;
  judge_accuracy: number;
  avg_semantic_score: number;
  avg_clinical_score: number;
  avg_reasoning_quality: number;
  avg_overall_score: number;
}

export interface DataOutput {
  cases: Case[];
  models: ModelSummary[];
  summary: {
    total_cases: number;
    total_models: number;
    generated_at: string;
  };
}

// Helper type for score categories
export type ScoreLevel = 'high' | 'medium' | 'low';

export function getScoreLevel(score: number): ScoreLevel {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

// Default judge used on case detail page
export const DEFAULT_JUDGE_ID = 'openai/gpt-5.2';

// All available judge models
export const JUDGE_MODEL_IDS = [
  'openai/gpt-5.2',
  'google/medgemma-27b-text-it',
] as const;

export const JUDGE_DISPLAY_NAMES: Record<string, string> = {
  'openai/gpt-5.2': 'GPT-5.2',
  'google/medgemma-27b-text-it': 'MedGemma 27B',
};

export function getJudgeDisplayName(judgeId: string): string {
  return JUDGE_DISPLAY_NAMES[judgeId] || judgeId.split('/').pop()?.replace(/-/g, ' ') || judgeId;
}

// Required models that need full review coverage
export const REQUIRED_MODEL_IDS = [
  'google/medgemma-27b-text-it',
  'google/gemma-3-27b-it',
  'allenai/Olmo-3.1-32B-Think',
  'google/gemma-3-4b-it',
  'OpenMeditron/Meditron3-Qwen2.5-7B',
  'allenai/Olmo-3.1-32B-Instruct',
] as const;

// Optional models (partial coverage is fine)
export const OPTIONAL_MODEL_IDS = [] as const;

// Helper type for model display names
export const MODEL_DISPLAY_NAMES: Record<string, string> = {
  'google/gemma-3-27b-it': 'Gemma 3 27B',
  'google/gemma-3-4b-it': 'Gemma 3 4B',
  'google/medgemma-27b-text-it': 'MedGemma 27B',
  'OpenMeditron/Meditron3-Qwen2.5-7B': 'Meditron3 7B',
  'allenai/Olmo-3.1-32B-Instruct': 'OLMo 32B Instruct',
  'allenai/Olmo-3.1-32B-Think': 'OLMo 32B Think',
};

export function getModelDisplayName(modelId: string): string {
  return MODEL_DISPLAY_NAMES[modelId] || modelId.split('/').pop()?.replace(/-/g, ' ') || modelId;
}
