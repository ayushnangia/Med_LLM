// Storage utility for doctor reviews
// Uses server API for reviews (multi-doctor support)
// Uses localStorage for session preferences (reviewer name, selected models)

// Re-export API functions for server-side storage
export {
  saveReviewToServer,
  saveReviewsBatch,
  getReviewsFromServer,
  getReviewFromServer,
  getDoctorsFromServer,
  registerDoctor,
  downloadReviewsFromServer,
  downloadJudgeReviewsFromServer,
  getReviewCountForDoctor,
  saveJudgeReviewsBatch,
  getJudgeReviewsFromServer,
} from './api';

export type {
  DoctorReviewInput,
  DoctorReviewResponse,
  DoctorInfo,
  JudgeReviewInput,
  JudgeReviewResponse,
} from './api';

const REVIEWER_KEY = 'medical-review-reviewer-name';
const SELECTED_MODELS_KEY = 'medical-review-selected-models';

// ============================================
// Session Preferences (localStorage)
// ============================================

// Reviewer name functions (stored locally for session preference)
export function getReviewerName(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(REVIEWER_KEY) || '';
}

export function setReviewerName(name: string): void {
  localStorage.setItem(REVIEWER_KEY, name);
}

// Selected models functions (stored locally for session preference)
export function getSelectedModels(): string[] {
  if (typeof window === 'undefined') return [];
  const stored = localStorage.getItem(SELECTED_MODELS_KEY);
  if (!stored) return [];
  try {
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

export function setSelectedModels(modelIds: string[]): void {
  localStorage.setItem(SELECTED_MODELS_KEY, JSON.stringify(modelIds));
}

export function toggleModelSelection(modelId: string): void {
  const selected = getSelectedModels();
  const index = selected.indexOf(modelId);
  if (index >= 0) {
    selected.splice(index, 1);
  } else {
    selected.push(modelId);
  }
  setSelectedModels(selected);
}

// ============================================
// Legacy localStorage functions (for migration)
// ============================================

const LEGACY_REVIEWS_KEY = 'medical-review-doctor-reviews';

export interface LegacyDoctorReview {
  case_id: string;
  model_id: string;
  reviewer_name: string;
  therapy_acceptable_ra: boolean | null;
  recommendation_exact_match: number | null;
  recommendation_patient_oriented: number | null;
  prediction_quality: number | null;
  timestamp: string;
}

// Get legacy reviews from localStorage (for migration)
export function getLegacyReviews(): LegacyDoctorReview[] {
  if (typeof window === 'undefined') return [];
  const stored = localStorage.getItem(LEGACY_REVIEWS_KEY);
  if (!stored) return [];
  try {
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

// Clear legacy reviews after migration
export function clearLegacyReviews(): void {
  localStorage.removeItem(LEGACY_REVIEWS_KEY);
}

// Check if there are legacy reviews to migrate
export function hasLegacyReviews(): boolean {
  return getLegacyReviews().length > 0;
}
