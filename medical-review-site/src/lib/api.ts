// API client functions for server-side review storage

export interface DoctorReviewInput {
  case_id: string;
  model_id: string;
  reviewer_name: string;
  therapy_acceptable_ra: boolean | null;
  recommendation_exact_match: number | null;
  recommendation_patient_oriented: number | null;
  prediction_quality: number | null;
  timestamp?: string;
}

export interface DoctorReviewResponse extends DoctorReviewInput {
  id: string;
  timestamp: string;
}

export interface DoctorInfo {
  name: string;
  reviewCount: number;
}

// Save a review to the server
export async function saveReviewToServer(review: DoctorReviewInput): Promise<DoctorReviewResponse> {
  const response = await fetch('/api/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(review),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to save review');
  }

  const data = await response.json();
  return data.review;
}

// Save multiple reviews in a single request (batch-safe, no race condition)
export async function saveReviewsBatch(reviews: DoctorReviewInput[]): Promise<DoctorReviewResponse[]> {
  if (reviews.length === 0) return [];

  const response = await fetch('/api/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviews }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to save reviews');
  }

  const data = await response.json();
  return data.reviews;
}

// Get reviews from the server (with optional filters)
export async function getReviewsFromServer(filters?: {
  doctor?: string;
  caseId?: string;
  modelId?: string;
}): Promise<DoctorReviewResponse[]> {
  const params = new URLSearchParams();
  if (filters?.doctor) params.set('doctor', filters.doctor);
  if (filters?.caseId) params.set('case', filters.caseId);
  if (filters?.modelId) params.set('model', filters.modelId);

  const url = `/api/reviews${params.toString() ? `?${params}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch reviews');
  }

  const data = await response.json();
  return data.reviews;
}

// Get a single review by case, model, and doctor
export async function getReviewFromServer(
  caseId: string,
  modelId: string,
  reviewerName: string
): Promise<DoctorReviewResponse | null> {
  const reviews = await getReviewsFromServer({
    caseId,
    modelId,
    doctor: reviewerName,
  });
  return reviews.length > 0 ? reviews[0] : null;
}

// Get all registered doctors with their review counts
export async function getDoctorsFromServer(): Promise<DoctorInfo[]> {
  const response = await fetch('/api/doctors');

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch doctors');
  }

  const data = await response.json();
  return data.doctors;
}

// Register a new doctor
export async function registerDoctor(name: string): Promise<DoctorInfo> {
  const response = await fetch('/api/doctors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to register doctor');
  }

  const data = await response.json();
  return { name: data.doctor.name, reviewCount: 0 };
}

// Download reviews as CSV
export async function downloadReviewsFromServer(doctorName?: string): Promise<void> {
  const url = doctorName ? `/api/export?doctor=${encodeURIComponent(doctorName)}` : '/api/export';
  const response = await fetch(url);

  if (!response.ok) {
    if (response.status === 404) {
      alert('Keine Bewertungen zum Exportieren');
      return;
    }
    const error = await response.json();
    throw new Error(error.error || 'Failed to export reviews');
  }

  // Get the filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `arzt-bewertungen_${new Date().toISOString().split('T')[0]}.csv`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="(.+)"/);
    if (match) filename = match[1];
  }

  // Download the file
  const blob = await response.blob();
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Download judge reviews as CSV
export async function downloadJudgeReviewsFromServer(doctorName?: string): Promise<void> {
  const url = doctorName ? `/api/export/judge?doctor=${encodeURIComponent(doctorName)}` : '/api/export/judge';
  const response = await fetch(url);

  if (!response.ok) {
    if (response.status === 404) {
      alert('Keine Richter-Bewertungen zum Exportieren');
      return;
    }
    const error = await response.json();
    throw new Error(error.error || 'Failed to export judge reviews');
  }

  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `richter-bewertungen_${new Date().toISOString().split('T')[0]}.csv`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="(.+)"/);
    if (match) filename = match[1];
  }

  const blob = await response.blob();
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Get review count for a doctor
export async function getReviewCountForDoctor(doctorName: string): Promise<number> {
  const reviews = await getReviewsFromServer({ doctor: doctorName });
  return reviews.length;
}

// ==========================================
// Judge Reviews
// ==========================================

export interface JudgeReviewInput {
  case_id: string;
  model_id: string;
  reviewer_name: string;
  judge_correct: string;  // 'agree' | 'disagree' | 'partial'
  judge_reasoning_quality?: number | null;
  comment?: string | null;
  doctor_acceptable?: boolean | null;
  doctor_quality?: number | null;
  judge_is_correct?: boolean | null;
  judge_overall_score?: number | null;
}

export interface JudgeReviewResponse extends JudgeReviewInput {
  id: string;
  created_at: string;
}

export async function saveJudgeReviewsBatch(reviews: JudgeReviewInput[]): Promise<JudgeReviewResponse[]> {
  if (reviews.length === 0) return [];

  const response = await fetch('/api/judge-reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviews }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to save judge reviews');
  }

  const data = await response.json();
  return data.reviews;
}

export async function getJudgeReviewsFromServer(filters?: {
  doctor?: string;
  caseId?: string;
}): Promise<JudgeReviewResponse[]> {
  const params = new URLSearchParams();
  if (filters?.doctor) params.set('doctor', filters.doctor);
  if (filters?.caseId) params.set('case', filters.caseId);

  const url = `/api/judge-reviews${params.toString() ? `?${params}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch judge reviews');
  }

  const data = await response.json();
  return data.reviews;
}
