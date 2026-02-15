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
}

interface DiagnosisInfo {
  diagnose_kurz: string;
  stadium: string;
  histologie_subtyp: string;
  klarzellig: boolean | null;
  tnm_cM: string;
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
  inference_time_s: number;
  doctor_review: DoctorReview | null;
}

interface Case {
  case_id: string;
  patient: PatientInfo;
  diagnosis: DiagnosisInfo;
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
    judge_evaluation: {
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
    },
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

async function main() {
  const csvDir = path.resolve(__dirname, '../../to_be_reviewed_results');
  const outputPath = path.resolve(__dirname, '../src/data/cases.json');
  const doctorReviewXlsx = path.resolve(__dirname, '../../allenai_olmo-3.1-32b-instruct_treatment_09-01-26.xlsx');

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

  // Build unified case list
  const caseIds = new Set<string>();
  for (const caseMap of allModelData.values()) {
    for (const caseId of caseMap.keys()) {
      caseIds.add(caseId);
    }
  }

  // Sort case IDs naturally (ncc_1, ncc_2, ... ncc_35)
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

    for (const [modelId, caseMap] of allModelData.entries()) {
      const data = caseMap.get(caseId);
      if (data) {
        if (!baseCase) {
          baseCase = rowToCase(data.row);
        }
        // Pass doctor review only for OLMo 32B Instruct
        const isOlmoInstruct = modelId.toLowerCase().includes('olmo') && modelId.toLowerCase().includes('instruct') && !modelId.toLowerCase().includes('think');
        const doctorReview = isOlmoInstruct ? (doctorReviews.get(caseId) || null) : null;
        const prediction = rowToPrediction(data.row, doctorReview);
        predictions[modelId] = prediction;

        // Collect for model summary
        if (!modelPredictions.has(modelId)) {
          modelPredictions.set(modelId, []);
        }
        modelPredictions.get(modelId)!.push(prediction);
      }
    }

    if (baseCase) {
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
