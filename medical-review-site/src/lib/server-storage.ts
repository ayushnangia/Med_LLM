// Server-side storage using Supabase (PostgreSQL)
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || '';

const supabase = createClient(supabaseUrl, supabaseKey);

export interface DoctorReview {
  id: string;
  case_id: string;
  model_id: string;
  reviewer_name: string;
  therapy_acceptable_ra: boolean | null;
  recommendation_exact_match: number | null;
  recommendation_patient_oriented: number | null;
  prediction_quality: number | null;
  timestamp: string;
}

// ==========================================
// Reviews
// ==========================================

export async function getReviews(filters?: {
  doctor?: string;
  caseId?: string;
  modelId?: string;
}): Promise<DoctorReview[]> {
  let query = supabase.from('reviews').select('*');

  if (filters?.doctor) query = query.eq('reviewer_name', filters.doctor);
  if (filters?.caseId) query = query.eq('case_id', filters.caseId);
  if (filters?.modelId) query = query.eq('model_id', filters.modelId);

  const { data, error } = await query;
  if (error) throw error;

  return (data || []).map(r => ({
    ...r,
    timestamp: r.created_at,
  }));
}

export async function upsertReview(input: {
  case_id: string;
  model_id: string;
  reviewer_name: string;
  therapy_acceptable_ra?: boolean | null;
  recommendation_exact_match?: number | null;
  recommendation_patient_oriented?: number | null;
  prediction_quality?: number | null;
}): Promise<DoctorReview> {
  const id = `${input.case_id}__${input.model_id}__${input.reviewer_name}`;

  const row = {
    id,
    case_id: input.case_id,
    model_id: input.model_id,
    reviewer_name: input.reviewer_name,
    therapy_acceptable_ra: input.therapy_acceptable_ra ?? null,
    recommendation_exact_match: input.recommendation_exact_match ?? null,
    recommendation_patient_oriented: input.recommendation_patient_oriented ?? null,
    prediction_quality: input.prediction_quality ?? null,
  };

  const { data, error } = await supabase
    .from('reviews')
    .upsert(row, { onConflict: 'id' })
    .select()
    .single();

  if (error) throw error;

  // Ensure doctor exists
  await supabase
    .from('doctors')
    .upsert({ name: input.reviewer_name }, { onConflict: 'name' });

  return { ...data, timestamp: data.created_at };
}

export async function upsertReviewsBatch(inputs: Array<{
  case_id: string;
  model_id: string;
  reviewer_name: string;
  therapy_acceptable_ra?: boolean | null;
  recommendation_exact_match?: number | null;
  recommendation_patient_oriented?: number | null;
  prediction_quality?: number | null;
}>): Promise<DoctorReview[]> {
  const rows = inputs.map(input => ({
    id: `${input.case_id}__${input.model_id}__${input.reviewer_name}`,
    case_id: input.case_id,
    model_id: input.model_id,
    reviewer_name: input.reviewer_name,
    therapy_acceptable_ra: input.therapy_acceptable_ra ?? null,
    recommendation_exact_match: input.recommendation_exact_match ?? null,
    recommendation_patient_oriented: input.recommendation_patient_oriented ?? null,
    prediction_quality: input.prediction_quality ?? null,
  }));

  const { data, error } = await supabase
    .from('reviews')
    .upsert(rows, { onConflict: 'id' })
    .select();

  if (error) throw error;

  // Ensure all doctors exist
  const uniqueDoctors = [...new Set(inputs.map(i => i.reviewer_name))];
  await supabase
    .from('doctors')
    .upsert(uniqueDoctors.map(name => ({ name })), { onConflict: 'name' });

  return (data || []).map(r => ({ ...r, timestamp: r.created_at }));
}

// ==========================================
// Doctors
// ==========================================

export async function getDoctors(): Promise<Array<{ name: string; reviewCount: number }>> {
  const { data: doctors, error: dErr } = await supabase
    .from('doctors')
    .select('name');

  if (dErr) throw dErr;

  // Count reviews per doctor
  const { data: reviews, error: rErr } = await supabase
    .from('reviews')
    .select('reviewer_name');

  if (rErr) throw rErr;

  const counts: Record<string, number> = {};
  (reviews || []).forEach(r => {
    counts[r.reviewer_name] = (counts[r.reviewer_name] || 0) + 1;
  });

  return (doctors || []).map(d => ({
    name: d.name,
    reviewCount: counts[d.name] || 0,
  }));
}

export async function registerDoctor(name: string): Promise<{ name: string; existing: boolean }> {
  const { data, error } = await supabase
    .from('doctors')
    .upsert({ name }, { onConflict: 'name' })
    .select()
    .single();

  if (error) throw error;
  return { name: data.name, existing: false };
}

// ==========================================
// Judge Reviews
// ==========================================

export interface JudgeReviewRow {
  id: string;
  case_id: string;
  model_id: string;
  reviewer_name: string;
  judge_model: string;
  judge_correct: string;
  judge_reasoning_quality: number | null;
  comment: string | null;
  doctor_acceptable: boolean | null;
  doctor_quality: number | null;
  judge_is_correct: boolean | null;
  judge_overall_score: number | null;
  created_at: string;
}

export async function getJudgeReviews(filters?: {
  doctor?: string;
  caseId?: string;
  modelId?: string;
  judgeModel?: string;
}): Promise<JudgeReviewRow[]> {
  let query = supabase.from('judge_reviews').select('*');

  if (filters?.doctor) query = query.eq('reviewer_name', filters.doctor);
  if (filters?.caseId) query = query.eq('case_id', filters.caseId);
  if (filters?.modelId) query = query.eq('model_id', filters.modelId);
  if (filters?.judgeModel) query = query.eq('judge_model', filters.judgeModel);

  const { data, error } = await query;
  if (error) throw error;

  return (data || []) as JudgeReviewRow[];
}

export async function upsertJudgeReview(input: {
  case_id: string;
  model_id: string;
  reviewer_name: string;
  judge_model: string;
  judge_correct: string;
  judge_reasoning_quality?: number | null;
  comment?: string | null;
  doctor_acceptable?: boolean | null;
  doctor_quality?: number | null;
  judge_is_correct?: boolean | null;
  judge_overall_score?: number | null;
}): Promise<JudgeReviewRow> {
  const id = `${input.case_id}__${input.model_id}__${input.reviewer_name}__${input.judge_model}`;

  const row = {
    id,
    case_id: input.case_id,
    model_id: input.model_id,
    reviewer_name: input.reviewer_name,
    judge_model: input.judge_model,
    judge_correct: input.judge_correct,
    judge_reasoning_quality: input.judge_reasoning_quality ?? null,
    comment: input.comment ?? null,
    doctor_acceptable: input.doctor_acceptable ?? null,
    doctor_quality: input.doctor_quality ?? null,
    judge_is_correct: input.judge_is_correct ?? null,
    judge_overall_score: input.judge_overall_score ?? null,
  };

  const { data, error } = await supabase
    .from('judge_reviews')
    .upsert(row, { onConflict: 'id' })
    .select()
    .single();

  if (error) throw error;
  return data as JudgeReviewRow;
}

export async function upsertJudgeReviewsBatch(inputs: Array<{
  case_id: string;
  model_id: string;
  reviewer_name: string;
  judge_model: string;
  judge_correct: string;
  judge_reasoning_quality?: number | null;
  comment?: string | null;
  doctor_acceptable?: boolean | null;
  doctor_quality?: number | null;
  judge_is_correct?: boolean | null;
  judge_overall_score?: number | null;
}>): Promise<JudgeReviewRow[]> {
  const rows = inputs.map(input => ({
    id: `${input.case_id}__${input.model_id}__${input.reviewer_name}__${input.judge_model}`,
    case_id: input.case_id,
    model_id: input.model_id,
    reviewer_name: input.reviewer_name,
    judge_model: input.judge_model,
    judge_correct: input.judge_correct,
    judge_reasoning_quality: input.judge_reasoning_quality ?? null,
    comment: input.comment ?? null,
    doctor_acceptable: input.doctor_acceptable ?? null,
    doctor_quality: input.doctor_quality ?? null,
    judge_is_correct: input.judge_is_correct ?? null,
    judge_overall_score: input.judge_overall_score ?? null,
  }));

  const { data, error } = await supabase
    .from('judge_reviews')
    .upsert(rows, { onConflict: 'id' })
    .select();

  if (error) throw error;
  return (data || []) as JudgeReviewRow[];
}
