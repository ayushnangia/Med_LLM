import casesData from '@/data/cases.json';
import type { DataOutput, Case, ModelSummary } from './types';

// Type assertion for the imported data
const data = casesData as DataOutput;

// Get all cases
export function getAllCases(): Case[] {
  return data.cases;
}

// Get a single case by ID
export function getCaseById(caseId: string): Case | undefined {
  return data.cases.find(c => c.case_id === caseId);
}

// Get all model summaries
export function getModelSummaries(): ModelSummary[] {
  return data.models;
}

// Get model summary by ID
export function getModelSummary(modelId: string): ModelSummary | undefined {
  return data.models.find(m => m.model_id === modelId);
}

// Get summary stats
export function getSummary() {
  return data.summary;
}

// Get all unique model IDs
export function getModelIds(): string[] {
  return data.models.map(m => m.model_id);
}

// Calculate how many models got a case correct (by judge evaluation)
export function getCaseCorrectCount(caseItem: Case): number {
  return Object.values(caseItem.predictions).filter(
    p => p.judge_evaluation.is_correct
  ).length;
}

// Get cases filtered by metastatic status
export function getCasesByMetastatic(metastatic: boolean): Case[] {
  return data.cases.filter(c => c.ground_truth.metastatic === metastatic);
}

// Get overall stats across all models
export function getOverallStats() {
  const models = data.models;
  const n = models.length;

  if (n === 0) {
    return {
      avgJudgeAccuracy: 0,
      avgSemanticScore: 0,
      avgClinicalScore: 0,
      avgOverallScore: 0,
      bestModel: null,
      worstModel: null,
    };
  }

  const avgJudgeAccuracy = models.reduce((sum, m) => sum + m.judge_accuracy, 0) / n;
  const avgSemanticScore = models.reduce((sum, m) => sum + m.avg_semantic_score, 0) / n;
  const avgClinicalScore = models.reduce((sum, m) => sum + m.avg_clinical_score, 0) / n;
  const avgOverallScore = models.reduce((sum, m) => sum + m.avg_overall_score, 0) / n;

  // Models are already sorted by judge_accuracy descending
  const bestModel = models[0];
  const worstModel = models[models.length - 1];

  return {
    avgJudgeAccuracy,
    avgSemanticScore,
    avgClinicalScore,
    avgOverallScore,
    bestModel,
    worstModel,
  };
}

// Search cases by patient name or diagnosis
export function searchCases(query: string): Case[] {
  const lowerQuery = query.toLowerCase();
  return data.cases.filter(
    c =>
      c.patient.name.toLowerCase().includes(lowerQuery) ||
      c.diagnosis.diagnose_kurz.toLowerCase().includes(lowerQuery) ||
      c.case_id.toLowerCase().includes(lowerQuery)
  );
}
