import * as fs from 'fs';
import * as path from 'path';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';

// CSV column mapping types
interface CSVRow {
  case_id: string;
  patient_name: string;
  age: string;
  ecog: string;
  karnofsky: string;
  comorbidity: string;
  diagnose_kurz: string;
  stadium: string;
  histologie_subtyp: string;
  klarzellig: string;
  tnm_cM: string;
  gt_metastatic: string;
  gt_therapy: string;
  pred_metastatic: string;
  pred_imdc_risk: string;
  pred_therapy: string;
  pred_category: string;
  pred_confidence: string;
  metastatic_correct: string;
  therapy_exact_match: string;
  therapy_acceptable: string;
  judge_is_correct: string;
  judge_correctness_reason: string;
  judge_semantic_match: string;
  judge_semantic_score: string;
  judge_clinical_appropriate: string;
  judge_clinical_score: string;
  judge_reasoning_quality: string;
  judge_reasoning_critique: string;
  judge_overall_score: string;
  judge_reasoning: string;
  judge_inference_time_s: string;
  pred_reasoning: string;
  model: string;
  timestamp: string;
  inference_time_s: string;
  success: string;
}

interface PatientInfo {
  name: string;
  age: number | null;
  ecog: number | null;
  karnofsky: number | null;
  comorbidity: string;
  life_expectancy?: string;
  karnofsky_from_labor?: number | null;
}

// Medication types (both v1.0 and v1.1 schemas)
interface Medication {
  wirkstoff_oder_klasse?: string;
  wirkstoff?: string;
  details?: string | null;
  hinweis?: string | null;
  dosierung?: string | null;
  schema?: string | null;
}

interface ImagingFinding {
  modalitaet: string;
  region: string;
  datum: string | null;
  befund_kurz: string;
}

interface TherapyProcedure {
  datum?: string | null;
  datum_start?: string | null;
  datum_ende?: string | null;
  typ: string;
  beschreibung?: string;
  regime?: string;
  intent?: string;
  linie?: number;
  status?: string;
  details?: string | null;
  klasse?: string[];
}

type SecondaryDiagnosis = string | { diagnose: string; details?: string };

interface ClinicalContext {
  anamnese_freitext?: string;
  fragestellung?: string | string[];
  nebendiagnosen?: SecondaryDiagnosis[];
  medikation?: Medication[];
  bildgebung?: ImagingFinding[];
  therapien_und_eingriffe?: TherapyProcedure[];
}

interface TNMStaging {
  T: string | null;
  T_sub?: string | null;
  N: string | null;
  M: string | null;
  stage_group?: string | null;
}

interface DiagnosisInfo {
  diagnose_kurz: string;
  stadium: string;
  histologie_subtyp: string;
  klarzellig: boolean | null;
  tnm_cM: string;
  tnm_clinical?: TNMStaging;
  tnm_pathological?: TNMStaging;
  tnm_string?: string;
  grading?: string | null;
  imdc_risiko?: string | null;
}

interface GroundTruth {
  metastatic: boolean;
  therapy: string;
}

interface JudgeEvaluation {
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

interface DoctorReview {
  therapy_acceptable_ra: boolean;
  recommendation_exact_match: number;
  recommendation_patient_oriented: number;
  prediction_quality: number;
}

interface ModelPrediction {
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
  judge_evaluation: JudgeEvaluation;
  judge_evaluations: Record<string, JudgeEvaluation>;
  inference_time_s: number;
  doctor_review: DoctorReview | null;
}

interface Case {
  case_id: string;
  patient: PatientInfo;
  diagnosis: DiagnosisInfo;
  clinical_context?: ClinicalContext;
  ground_truth: GroundTruth;
  predictions: Record<string, ModelPrediction>;
}

interface ModelSummary {
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

interface DataOutput {
  cases: Case[];
  models: ModelSummary[];
  summary: {
    total_cases: number;
    total_models: number;
    generated_at: string;
  };
}

function parseBoolean(val: string): boolean {
  const lower = val?.toLowerCase?.() ?? '';
  return lower === 'true' || lower === '1' || lower === 'yes';
}

function parseNumber(val: string): number | null {
  if (!val || val === '' || val === 'unknown' || val === 'null') return null;
  const num = parseFloat(val);
  return isNaN(num) ? null : num;
}

function getModelDisplayName(modelId: string): string {
  const mapping: Record<string, string> = {
    'google/gemma-3-27b-it': 'Gemma 3 27B',
    'google/gemma-3-4b-it': 'Gemma 3 4B',
    'google/medgemma-27b-text-it': 'MedGemma 27B',
    'meditron3-qwen2.5-7b': 'Meditron3 7B',
    'allenai/olmo-3.1-32b-instruct': 'OLMo 32B Instruct',
    'allenai/olmo-3.1-32b-think': 'OLMo 32B Think',
  };
  return mapping[modelId] || modelId.split('/').pop()?.replace(/-/g, ' ') || modelId;
}

// Valid case ID pattern - must start with ncc_, pca_, uca_, etc.
function isValidCaseId(caseId: string): boolean {
  return /^(ncc|pca|uca|hoden_ca|penis_ca|combi|non_uro)_\d+$/i.test(caseId);
}

// Load doctor reviews from Excel file for OLMo 32B Instruct
function loadDoctorReviews(xlsxPath: string): Map<string, DoctorReview> {
  const reviews = new Map<string, DoctorReview>();

  if (!fs.existsSync(xlsxPath)) {
    console.log(`  Doctor review file not found: ${xlsxPath}`);
    return reviews;
  }

  const workbook = XLSX.read(fs.readFileSync(xlsxPath), { type: 'buffer' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const data = XLSX.utils.sheet_to_json(worksheet) as Record<string, unknown>[];

  for (const row of data) {
    const caseId = row['case_id'] as string;
    if (caseId && isValidCaseId(caseId)) {
      // Column names with special characters from the Excel file
      const therapyAcceptableRA = row['therapy acceptable_RA'];
      const recommendationExactMatch = row['therapy_recommandation_exact_match'];
      const recommendationPatientOriented = row['therapy_recommandation_patient_oriented?'];
      const predictionQuality = row['prediction_quality'];

      reviews.set(caseId, {
        therapy_acceptable_ra: Number(therapyAcceptableRA) === 1,
        recommendation_exact_match: typeof recommendationExactMatch === 'number' ? recommendationExactMatch : 0,
        recommendation_patient_oriented: typeof recommendationPatientOriented === 'number' ? recommendationPatientOriented : 0,
        prediction_quality: typeof predictionQuality === 'number' ? predictionQuality : 0,
      });
    }
  }

  console.log(`  Loaded ${reviews.size} doctor reviews from Excel`);
  return reviews;
}

function processCSVFile(filePath: string): Map<string, { row: CSVRow; model: string }> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const result = Papa.parse<CSVRow>(content, { header: true, skipEmptyLines: true });

  const caseMap = new Map<string, { row: CSVRow; model: string }>();

  for (const row of result.data) {
    // Only include rows with valid case IDs (skip summary rows)
    if (row.case_id && isValidCaseId(row.case_id)) {
      caseMap.set(row.case_id, { row, model: row.model });
    }
  }

  return caseMap;
}

function rowToPrediction(row: CSVRow, doctorReview: DoctorReview | null = null): ModelPrediction {
  const csvJudge: JudgeEvaluation = {
    is_correct: parseBoolean(row.judge_is_correct),
    correctness_reason: row.judge_correctness_reason || '',
    semantic_match: parseBoolean(row.judge_semantic_match),
    semantic_score: parseNumber(row.judge_semantic_score) || 0,
    clinical_appropriate: parseBoolean(row.judge_clinical_appropriate),
    clinical_score: parseNumber(row.judge_clinical_score) || 0,
    reasoning_quality: parseNumber(row.judge_reasoning_quality) || 0,
    reasoning_critique: row.judge_reasoning_critique || '',
    overall_score: parseNumber(row.judge_overall_score) || 0,
    judge_reasoning: row.judge_reasoning || '',
    inference_time_s: parseNumber(row.judge_inference_time_s) || 0,
  };
  return {
    model_id: row.model,
    pred_metastatic: parseBoolean(row.pred_metastatic),
    pred_imdc_risk: row.pred_imdc_risk || '',
    pred_therapy: row.pred_therapy || '',
    pred_category: row.pred_category || '',
    pred_confidence: parseNumber(row.pred_confidence) || 0,
    pred_reasoning: row.pred_reasoning || '',
    metastatic_correct: parseBoolean(row.metastatic_correct),
    therapy_exact_match: parseBoolean(row.therapy_exact_match),
    therapy_acceptable: parseBoolean(row.therapy_acceptable),
    judge_evaluation: csvJudge,
    judge_evaluations: { 'openai/gpt-5.2': csvJudge },  // CSV data is GPT-5.2; more judges added later
    inference_time_s: parseNumber(row.inference_time_s) || 0,
    doctor_review: doctorReview,
  };
}

function rowToCase(row: CSVRow): Omit<Case, 'predictions'> {
  return {
    case_id: row.case_id,
    patient: {
      name: row.patient_name,
      age: parseNumber(row.age),
      ecog: parseNumber(row.ecog),
      karnofsky: parseNumber(row.karnofsky),
      comorbidity: row.comorbidity || 'unknown',
    },
    diagnosis: {
      diagnose_kurz: row.diagnose_kurz || '',
      stadium: row.stadium || '',
      histologie_subtyp: row.histologie_subtyp || '',
      klarzellig: row.klarzellig ? parseBoolean(row.klarzellig) : null,
      tnm_cM: row.tnm_cM || '',
    },
    ground_truth: {
      metastatic: parseBoolean(row.gt_metastatic),
      therapy: row.gt_therapy || '',
    },
  };
}

function calculateModelSummary(modelId: string, predictions: ModelPrediction[]): ModelSummary {
  const n = predictions.length;
  if (n === 0) {
    return {
      model_id: modelId,
      display_name: getModelDisplayName(modelId),
      total_cases: 0,
      metastatic_accuracy: 0,
      therapy_exact_match_rate: 0,
      judge_accuracy: 0,
      avg_semantic_score: 0,
      avg_clinical_score: 0,
      avg_reasoning_quality: 0,
      avg_overall_score: 0,
    };
  }

  const metastaticCorrect = predictions.filter(p => p.metastatic_correct).length;
  const therapyExact = predictions.filter(p => p.therapy_exact_match).length;
  const judgeCorrect = predictions.filter(p => p.judge_evaluation.is_correct).length;

  const avgSemantic = predictions.reduce((sum, p) => sum + p.judge_evaluation.semantic_score, 0) / n;
  const avgClinical = predictions.reduce((sum, p) => sum + p.judge_evaluation.clinical_score, 0) / n;
  const avgReasoning = predictions.reduce((sum, p) => sum + p.judge_evaluation.reasoning_quality, 0) / n;
  const avgOverall = predictions.reduce((sum, p) => sum + p.judge_evaluation.overall_score, 0) / n;

  return {
    model_id: modelId,
    display_name: getModelDisplayName(modelId),
    total_cases: n,
    metastatic_accuracy: (metastaticCorrect / n) * 100,
    therapy_exact_match_rate: (therapyExact / n) * 100,
    judge_accuracy: (judgeCorrect / n) * 100,
    avg_semantic_score: avgSemantic,
    avg_clinical_score: avgClinical,
    avg_reasoning_quality: avgReasoning,
    avg_overall_score: avgOverall,
  };
}

// Map from model directory name → model ID used in predictions
const MODEL_DIR_TO_ID: Record<string, string> = {
  'google_gemma-3-27b-it': 'google/gemma-3-27b-it',
  'google_gemma-3-4b-it': 'google/gemma-3-4b-it',
  'google_medgemma-27b-text-it': 'google/medgemma-27b-text-it',
  'openmeditron_meditron3-qwen2.5-7b': 'OpenMeditron/Meditron3-Qwen2.5-7B',
  'allenai_olmo-3.1-32b-instruct': 'allenai/Olmo-3.1-32B-Instruct',
  'allenai_olmo-3.1-32b-think': 'allenai/Olmo-3.1-32B-Think',
};

interface JudgeJsonEvaluation {
  is_correct: boolean;
  correctness_reason: string;
  therapy_semantic_match: boolean;
  therapy_semantic_score: number;
  clinical_appropriateness: boolean;
  clinical_appropriateness_score: number;
  reasoning_quality: number;
  reasoning_critique: string;
  overall_score: number;
  judge_reasoning: string;
}

interface JudgeJsonFile {
  judge_model: string;
  evaluations: Array<{ case_id: string; evaluation: JudgeJsonEvaluation }>;
}

// Per-case JSON structure from results/modal_treatment/{model}/{run}/ncc_XX.json
interface CaseJsonFile {
  case_id: string;
  model: string;
  input_case: {
    case_id: string;
    patient_name: string;
    age: number | null;
    ecog: number | null;
    karnofsky: number | null;
    comorbidity: string;
    life_expectancy: string;
    diagnose_kurz: string;
    stadium: string;
    histologie_subtyp?: string;
    histologie_klarzellig?: boolean;
    klarzellig?: boolean;
    tnm_cM?: string;
    tnm_clinical?: TNMStaging | null;
    tnm_pathological?: TNMStaging | null;
    grading?: string | null;
    imdc_risiko?: string | null;
    // Clinical context fields
    anamnese?: string;
    fragestellung?: string | string[];
    nebendiagnosen?: SecondaryDiagnosis[];
    medikation?: Medication[];
    bildgebung?: ImagingFinding[];
    prior_therapies?: TherapyProcedure[];
    therapien_und_eingriffe?: TherapyProcedure[];
    ici_durchfuehrbar?: boolean | null;
  };
  prediction: {
    is_metastatic: boolean;
    metastatic_reasoning: string;
    imdc_risk: string;
    imdc_reasoning: string;
    treatment_reasoning: string;
    recommended_therapy: string;
    therapy_category: string;
    recommendation_strength: string;
    confidence: number;
  };
  ground_truth_metastatic: boolean;
  ground_truth_therapy: string;
  metastatic_correct: boolean;
  therapy_exact_match: boolean;
  therapy_clinically_acceptable: boolean;
  inference_time_seconds: number;
  success: boolean;
}

// Load cases from per-case JSON files in results directory
// Returns: modelId → caseId → { case info, prediction }
function loadCasesFromResults(resultsDir: string): Map<string, Map<string, { caseInfo: Omit<Case, 'predictions'>; prediction: ModelPrediction }>> {
  const result = new Map<string, Map<string, { caseInfo: Omit<Case, 'predictions'>; prediction: ModelPrediction }>>();

  if (!fs.existsSync(resultsDir)) return result;

  const modelDirs = fs.readdirSync(resultsDir).filter(d =>
    fs.statSync(path.join(resultsDir, d)).isDirectory()
  );

  for (const modelDir of modelDirs) {
    const modelId = MODEL_DIR_TO_ID[modelDir.toLowerCase()];
    if (!modelId) continue;

    const modelPath = path.join(resultsDir, modelDir);
    const runDirs = fs.readdirSync(modelPath)
      .filter(d => fs.statSync(path.join(modelPath, d)).isDirectory())
      .sort(); // chronological — later runs overwrite

    for (const runDir of runDirs) {
      const runPath = path.join(modelPath, runDir);
      const caseFiles = fs.readdirSync(runPath).filter(f => /^ncc_\d+\.json$/.test(f));

      for (const caseFile of caseFiles) {
        try {
          const data: CaseJsonFile = JSON.parse(fs.readFileSync(path.join(runPath, caseFile), 'utf-8'));
          if (!data.success) continue;

          const caseId = data.case_id;
          const ic = data.input_case;
          const pred = data.prediction;

          // Build clinical context from input_case
          const clinicalContext: ClinicalContext = {};
          if (ic.anamnese) clinicalContext.anamnese_freitext = ic.anamnese;
          if (ic.fragestellung) clinicalContext.fragestellung = ic.fragestellung;
          if (ic.nebendiagnosen && ic.nebendiagnosen.length > 0) clinicalContext.nebendiagnosen = ic.nebendiagnosen;
          if (ic.medikation && ic.medikation.length > 0) clinicalContext.medikation = ic.medikation;
          if (ic.bildgebung && ic.bildgebung.length > 0) {
            clinicalContext.bildgebung = ic.bildgebung.map((b) => ({
              modalitaet: b.modalitaet || '',
              region: b.region || '',
              datum: b.datum || null,
              befund_kurz: b.befund_kurz || '',
            }));
          }
          const therapies = ic.prior_therapies || ic.therapien_und_eingriffe;
          if (therapies && therapies.length > 0) clinicalContext.therapien_und_eingriffe = therapies;

          const caseInfo: Omit<Case, 'predictions'> = {
            case_id: caseId,
            patient: {
              name: ic.patient_name || '',
              age: ic.age,
              ecog: ic.ecog,
              karnofsky: ic.karnofsky,
              comorbidity: ic.comorbidity || 'unknown',
              life_expectancy: ic.life_expectancy || undefined,
            },
            diagnosis: {
              diagnose_kurz: ic.diagnose_kurz || '',
              stadium: ic.stadium || '',
              histologie_subtyp: ic.histologie_subtyp || '',
              klarzellig: ic.histologie_klarzellig ?? ic.klarzellig ?? null,
              tnm_cM: ic.tnm_cM || '',
              tnm_clinical: ic.tnm_clinical || undefined,
              tnm_pathological: ic.tnm_pathological || undefined,
              grading: ic.grading || undefined,
              imdc_risiko: ic.imdc_risiko || undefined,
            },
            clinical_context: Object.keys(clinicalContext).length > 0 ? clinicalContext : undefined,
            ground_truth: {
              metastatic: data.ground_truth_metastatic,
              therapy: data.ground_truth_therapy || '',
            },
          };

          // Build a placeholder judge evaluation (will be filled by loadJudgeEvaluations)
          const emptyJudge: JudgeEvaluation = {
            is_correct: false,
            correctness_reason: '',
            semantic_match: false,
            semantic_score: 0,
            clinical_appropriate: false,
            clinical_score: 0,
            reasoning_quality: 0,
            reasoning_critique: '',
            overall_score: 0,
            judge_reasoning: '',
            inference_time_s: 0,
          };

          const prediction: ModelPrediction = {
            model_id: modelId,
            pred_metastatic: pred.is_metastatic,
            pred_imdc_risk: pred.imdc_risk || '',
            pred_therapy: pred.recommended_therapy || '',
            pred_category: pred.therapy_category || '',
            pred_confidence: pred.confidence || 0,
            pred_reasoning: pred.treatment_reasoning || '',
            metastatic_correct: data.metastatic_correct,
            therapy_exact_match: data.therapy_exact_match,
            therapy_acceptable: data.therapy_clinically_acceptable,
            judge_evaluation: emptyJudge,
            judge_evaluations: {},
            inference_time_s: data.inference_time_seconds || 0,
            doctor_review: null,
          };

          if (!result.has(modelId)) result.set(modelId, new Map());
          result.get(modelId)!.set(caseId, { caseInfo, prediction });
        } catch (e) {
          // skip invalid files
        }
      }
    }
  }

  let totalCases = 0;
  const caseIdSet = new Set<string>();
  for (const [, caseMap] of result) {
    for (const [caseId] of caseMap) {
      caseIdSet.add(caseId);
      totalCases++;
    }
  }
  console.log(`  Loaded ${totalCases} predictions from JSON files (${caseIdSet.size} unique cases, ${result.size} models)`);

  return result;
}

// Load clinical context for cases that don't have it (e.g. CSV-sourced cases 1-35)
// Reads from any JSON result file for the case
function loadClinicalContextFromResults(resultsDir: string): Map<string, { clinical_context?: ClinicalContext; patient_extras?: Partial<PatientInfo>; diagnosis_extras?: Partial<DiagnosisInfo> }> {
  const result = new Map<string, { clinical_context?: ClinicalContext; patient_extras?: Partial<PatientInfo>; diagnosis_extras?: Partial<DiagnosisInfo> }>();

  if (!fs.existsSync(resultsDir)) return result;

  const modelDirs = fs.readdirSync(resultsDir).filter(d =>
    fs.statSync(path.join(resultsDir, d)).isDirectory()
  );

  // Just need one model's data per case — pick the first model dir
  for (const modelDir of modelDirs) {
    const modelPath = path.join(resultsDir, modelDir);
    const runDirs = fs.readdirSync(modelPath)
      .filter(d => fs.statSync(path.join(modelPath, d)).isDirectory())
      .sort();

    for (const runDir of runDirs) {
      const runPath = path.join(modelPath, runDir);
      const caseFiles = fs.readdirSync(runPath).filter(f => /^ncc_\d+\.json$/.test(f));

      for (const caseFile of caseFiles) {
        const caseId = caseFile.replace('.json', '');
        if (result.has(caseId)) continue; // already have context for this case

        try {
          const data: CaseJsonFile = JSON.parse(fs.readFileSync(path.join(runPath, caseFile), 'utf-8'));
          const ic = data.input_case;

          const clinicalContext: ClinicalContext = {};
          if (ic.anamnese) clinicalContext.anamnese_freitext = ic.anamnese;
          if (ic.fragestellung) clinicalContext.fragestellung = ic.fragestellung;
          if (ic.nebendiagnosen && ic.nebendiagnosen.length > 0) clinicalContext.nebendiagnosen = ic.nebendiagnosen;
          if (ic.medikation && ic.medikation.length > 0) clinicalContext.medikation = ic.medikation;
          if (ic.bildgebung && ic.bildgebung.length > 0) {
            clinicalContext.bildgebung = ic.bildgebung.map((b) => ({
              modalitaet: b.modalitaet || '',
              region: b.region || '',
              datum: b.datum || null,
              befund_kurz: b.befund_kurz || '',
            }));
          }
          const therapies = ic.prior_therapies || ic.therapien_und_eingriffe;
          if (therapies && therapies.length > 0) clinicalContext.therapien_und_eingriffe = therapies;

          const patientExtras: Partial<PatientInfo> = {};
          if (ic.karnofsky != null) patientExtras.karnofsky = ic.karnofsky;
          if (ic.life_expectancy) patientExtras.life_expectancy = ic.life_expectancy;

          const diagnosisExtras: Partial<DiagnosisInfo> = {};
          if (ic.tnm_clinical) diagnosisExtras.tnm_clinical = ic.tnm_clinical;
          if (ic.tnm_pathological) diagnosisExtras.tnm_pathological = ic.tnm_pathological;
          if (ic.grading) diagnosisExtras.grading = ic.grading;
          if (ic.imdc_risiko) diagnosisExtras.imdc_risiko = ic.imdc_risiko;

          result.set(caseId, {
            clinical_context: Object.keys(clinicalContext).length > 0 ? clinicalContext : undefined,
            patient_extras: Object.keys(patientExtras).length > 0 ? patientExtras : undefined,
            diagnosis_extras: Object.keys(diagnosisExtras).length > 0 ? diagnosisExtras : undefined,
          });
        } catch {
          // skip
        }
      }
    }
  }

  console.log(`  Loaded clinical context for ${result.size} cases from JSON files`);
  return result;
}

function loadJudgeEvaluations(resultsDir: string): Map<string, Map<string, Map<string, JudgeEvaluation>>> {
  // Returns: modelId → caseId → judgeModelId → JudgeEvaluation
  const result = new Map<string, Map<string, Map<string, JudgeEvaluation>>>();

  if (!fs.existsSync(resultsDir)) {
    console.log(`  Results dir not found: ${resultsDir}`);
    return result;
  }

  const modelDirs = fs.readdirSync(resultsDir).filter(d =>
    fs.statSync(path.join(resultsDir, d)).isDirectory()
  );

  for (const modelDir of modelDirs) {
    const modelId = MODEL_DIR_TO_ID[modelDir.toLowerCase()];
    if (!modelId) continue;

    const modelPath = path.join(resultsDir, modelDir);
    const runDirs = fs.readdirSync(modelPath).filter(d =>
      fs.statSync(path.join(modelPath, d)).isDirectory()
    );

    for (const runDir of runDirs) {
      const runPath = path.join(modelPath, runDir);
      const judgeFiles = fs.readdirSync(runPath).filter(f => f.startsWith('judge_evaluation_') && f.endsWith('.json'));

      for (const judgeFile of judgeFiles) {
        try {
          const data: JudgeJsonFile = JSON.parse(fs.readFileSync(path.join(runPath, judgeFile), 'utf-8'));
          const judgeModelId = data.judge_model;

          for (const item of data.evaluations) {
            const caseId = item.case_id;
            const ev = item.evaluation;

            if (!result.has(modelId)) result.set(modelId, new Map());
            if (!result.get(modelId)!.has(caseId)) result.get(modelId)!.set(caseId, new Map());

            // Later run overwrites earlier run for same judge+model+case
            result.get(modelId)!.get(caseId)!.set(judgeModelId, {
              is_correct: ev.is_correct,
              correctness_reason: ev.correctness_reason || '',
              semantic_match: ev.therapy_semantic_match,
              semantic_score: ev.therapy_semantic_score || 0,
              clinical_appropriate: ev.clinical_appropriateness,
              clinical_score: ev.clinical_appropriateness_score || 0,
              reasoning_quality: ev.reasoning_quality || 0,
              reasoning_critique: ev.reasoning_critique || '',
              overall_score: ev.overall_score || 0,
              judge_reasoning: ev.judge_reasoning || '',
              inference_time_s: 0,
            });
          }
        } catch (e) {
          console.warn(`  Warning: failed to parse ${judgeFile}: ${e}`);
        }
      }
    }
  }

  // Log stats
  let totalEvals = 0;
  const judges = new Set<string>();
  for (const [, caseMap] of result) {
    for (const [, judgeMap] of caseMap) {
      for (const [judgeId] of judgeMap) {
        totalEvals++;
        judges.add(judgeId);
      }
    }
  }
  console.log(`  Loaded ${totalEvals} judge evaluations from ${judges.size} judges: ${Array.from(judges).join(', ')}`);

  return result;
}

async function main() {
  const csvDir = path.resolve(__dirname, '../../to_be_reviewed_results');
  const outputPath = path.resolve(__dirname, '../src/data/cases.json');
  const doctorReviewXlsx = path.resolve(__dirname, '../../allenai_olmo-3.1-32b-instruct_treatment_09-01-26.xlsx');
  const resultsDir = path.resolve(__dirname, '../../results/modal_treatment');

  // Find all CSV files (excluding summary)
  const csvFiles = fs.readdirSync(csvDir)
    .filter(f => f.endsWith('.csv') && !f.includes('summary'))
    .map(f => path.join(csvDir, f));

  console.log(`Found ${csvFiles.length} CSV files:`);
  csvFiles.forEach(f => console.log(`  - ${path.basename(f)}`));

  // Load doctor reviews for OLMo 32B Instruct
  console.log('\nLoading doctor reviews...');
  const doctorReviews = loadDoctorReviews(doctorReviewXlsx);

  // Collect all data from CSVs
  const allModelData = new Map<string, Map<string, { row: CSVRow; model: string }>>();

  for (const csvFile of csvFiles) {
    const caseMap = processCSVFile(csvFile);
    const modelId = caseMap.values().next().value?.model || '';
    if (modelId) {
      allModelData.set(modelId, caseMap);
      console.log(`Processed ${modelId}: ${caseMap.size} cases`);
    }
  }

  // Load cases from per-case JSON result files (covers cases 36-69+)
  console.log('\nLoading cases from result JSON files...');
  const jsonCases = loadCasesFromResults(resultsDir);

  // Load clinical context from JSON files (for ALL cases, including CSV-sourced)
  console.log('\nLoading clinical context from JSON files...');
  const clinicalContextMap = loadClinicalContextFromResults(resultsDir);

  // Load judge evaluations from results JSON files
  console.log('\nLoading judge evaluations from results...');
  const judgeEvals = loadJudgeEvaluations(resultsDir);

  // Build unified case list — merge CSV + JSON sources
  const caseIds = new Set<string>();
  for (const caseMap of allModelData.values()) {
    for (const caseId of caseMap.keys()) {
      caseIds.add(caseId);
    }
  }
  // Also add case IDs from JSON result files
  for (const [, caseMap] of jsonCases) {
    for (const caseId of caseMap.keys()) {
      caseIds.add(caseId);
    }
  }

  // Sort case IDs naturally (ncc_1, ncc_2, ... ncc_69)
  const sortedCaseIds = Array.from(caseIds).sort((a, b) => {
    const numA = parseInt(a.split('_')[1]) || 0;
    const numB = parseInt(b.split('_')[1]) || 0;
    return numA - numB;
  });

  const cases: Case[] = [];
  const modelPredictions = new Map<string, ModelPrediction[]>();

  for (const caseId of sortedCaseIds) {
    let baseCase: Omit<Case, 'predictions'> | null = null;
    const predictions: Record<string, ModelPrediction> = {};

    // First: load from CSVs (cases 1-35)
    for (const [modelId, caseMap] of allModelData.entries()) {
      const data = caseMap.get(caseId);
      if (data) {
        if (!baseCase) {
          baseCase = rowToCase(data.row);
        }
        const isOlmoInstruct = modelId.toLowerCase().includes('olmo') && modelId.toLowerCase().includes('instruct') && !modelId.toLowerCase().includes('think');
        const doctorReview = isOlmoInstruct ? (doctorReviews.get(caseId) || null) : null;
        const prediction = rowToPrediction(data.row, doctorReview);
        predictions[modelId] = prediction;

        if (!modelPredictions.has(modelId)) {
          modelPredictions.set(modelId, []);
        }
        modelPredictions.get(modelId)!.push(prediction);
      }
    }

    // Second: load from JSON result files (cases 36-69, or any not in CSVs)
    for (const [modelId, caseMap] of jsonCases) {
      if (predictions[modelId]) continue; // CSV already has this model+case
      const jsonData = caseMap.get(caseId);
      if (jsonData) {
        if (!baseCase) {
          baseCase = jsonData.caseInfo;
        }
        predictions[modelId] = jsonData.prediction;

        if (!modelPredictions.has(modelId)) {
          modelPredictions.set(modelId, []);
        }
        modelPredictions.get(modelId)!.push(jsonData.prediction);
      }
    }

    if (baseCase) {
      // Merge clinical context from JSON files (fills in data for CSV-sourced cases)
      const ctxData = clinicalContextMap.get(caseId);
      if (ctxData) {
        if (!baseCase.clinical_context && ctxData.clinical_context) {
          baseCase.clinical_context = ctxData.clinical_context;
        }
        if (ctxData.patient_extras) {
          if (baseCase.patient.karnofsky == null && ctxData.patient_extras.karnofsky != null) {
            baseCase.patient.karnofsky = ctxData.patient_extras.karnofsky;
          }
          if (!baseCase.patient.life_expectancy && ctxData.patient_extras.life_expectancy) {
            baseCase.patient.life_expectancy = ctxData.patient_extras.life_expectancy;
          }
        }
        if (ctxData.diagnosis_extras) {
          if (!baseCase.diagnosis.tnm_clinical && ctxData.diagnosis_extras.tnm_clinical) {
            baseCase.diagnosis.tnm_clinical = ctxData.diagnosis_extras.tnm_clinical;
          }
          if (!baseCase.diagnosis.tnm_pathological && ctxData.diagnosis_extras.tnm_pathological) {
            baseCase.diagnosis.tnm_pathological = ctxData.diagnosis_extras.tnm_pathological;
          }
          if (!baseCase.diagnosis.grading && ctxData.diagnosis_extras.grading) {
            baseCase.diagnosis.grading = ctxData.diagnosis_extras.grading;
          }
          if (!baseCase.diagnosis.imdc_risiko && ctxData.diagnosis_extras.imdc_risiko) {
            baseCase.diagnosis.imdc_risiko = ctxData.diagnosis_extras.imdc_risiko;
          }
        }
      }

      // Merge judge evaluations from JSON files into predictions
      for (const [modelId, prediction] of Object.entries(predictions)) {
        const modelJudges = judgeEvals.get(modelId);
        if (modelJudges) {
          const caseJudges = modelJudges.get(caseId);
          if (caseJudges) {
            for (const [judgeId, judgeEval] of caseJudges) {
              prediction.judge_evaluations[judgeId] = judgeEval;
              // Set the default judge_evaluation to GPT-5.2 if available
              if (judgeId === 'openai/gpt-5.2') {
                prediction.judge_evaluation = judgeEval;
              }
            }
          }
        }
      }

      cases.push({
        ...baseCase,
        predictions,
      });
    }
  }

  // Calculate model summaries
  const modelSummaries: ModelSummary[] = [];
  for (const [modelId, predictions] of modelPredictions.entries()) {
    modelSummaries.push(calculateModelSummary(modelId, predictions));
  }

  // Sort by judge accuracy (descending)
  modelSummaries.sort((a, b) => b.judge_accuracy - a.judge_accuracy);

  const output: DataOutput = {
    cases,
    models: modelSummaries,
    summary: {
      total_cases: cases.length,
      total_models: modelSummaries.length,
      generated_at: new Date().toISOString(),
    },
  };

  // Ensure output directory exists
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));

  console.log(`\nGenerated ${outputPath}`);
  console.log(`  - ${cases.length} cases`);
  console.log(`  - ${modelSummaries.length} models`);
}

main().catch(console.error);
