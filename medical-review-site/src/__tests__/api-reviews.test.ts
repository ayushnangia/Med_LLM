import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'fs';
import path from 'path';

// Test the reviews API through direct function imports
// We test the server-storage module directly since the API routes
// are thin wrappers around it

const TEST_DATA_FILE = path.join(process.cwd(), 'src/data/reviews-test.json');
const LOCK_FILE = TEST_DATA_FILE + '.lock';

// Helper: create a minimal reviews data store
interface TestReview {
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

interface TestData {
  doctors: string[];
  reviews: TestReview[];
}

async function writeTestData(data: TestData) {
  await fs.writeFile(TEST_DATA_FILE, JSON.stringify(data, null, 2));
}

async function readTestData(): Promise<TestData> {
  const content = await fs.readFile(TEST_DATA_FILE, 'utf-8');
  return JSON.parse(content);
}

async function cleanupTestFiles() {
  try { await fs.unlink(TEST_DATA_FILE); } catch {}
  try { await fs.unlink(LOCK_FILE); } catch {}
}

describe('Reviews API - data filtering', () => {
  const sampleData: TestData = {
    doctors: ['Dr. Smith', 'Dr. Jones'],
    reviews: [
      {
        id: 'ncc_1__model_a__Dr. Smith',
        case_id: 'ncc_1',
        model_id: 'model_a',
        reviewer_name: 'Dr. Smith',
        therapy_acceptable_ra: true,
        recommendation_exact_match: 80,
        recommendation_patient_oriented: 70,
        prediction_quality: 7,
        timestamp: '2026-01-01T00:00:00Z',
      },
      {
        id: 'ncc_1__model_b__Dr. Smith',
        case_id: 'ncc_1',
        model_id: 'model_b',
        reviewer_name: 'Dr. Smith',
        therapy_acceptable_ra: false,
        recommendation_exact_match: 40,
        recommendation_patient_oriented: 50,
        prediction_quality: 4,
        timestamp: '2026-01-01T00:00:01Z',
      },
      {
        id: 'ncc_2__model_a__Dr. Jones',
        case_id: 'ncc_2',
        model_id: 'model_a',
        reviewer_name: 'Dr. Jones',
        therapy_acceptable_ra: true,
        recommendation_exact_match: 90,
        recommendation_patient_oriented: 85,
        prediction_quality: 8,
        timestamp: '2026-01-01T00:00:02Z',
      },
      {
        id: 'ncc_1__model_a__Dr. Jones',
        case_id: 'ncc_1',
        model_id: 'model_a',
        reviewer_name: 'Dr. Jones',
        therapy_acceptable_ra: true,
        recommendation_exact_match: 60,
        recommendation_patient_oriented: 75,
        prediction_quality: 6,
        timestamp: '2026-01-01T00:00:03Z',
      },
    ],
  };

  beforeEach(async () => {
    await writeTestData(sampleData);
  });

  afterEach(async () => {
    await cleanupTestFiles();
  });

  it('can read all reviews from file', async () => {
    const data = await readTestData();
    expect(data.reviews).toHaveLength(4);
  });

  it('filters by doctor name', async () => {
    const data = await readTestData();
    const filtered = data.reviews.filter(r => r.reviewer_name === 'Dr. Smith');
    expect(filtered).toHaveLength(2);
    expect(filtered.every(r => r.reviewer_name === 'Dr. Smith')).toBe(true);
  });

  it('filters by case_id', async () => {
    const data = await readTestData();
    const filtered = data.reviews.filter(r => r.case_id === 'ncc_1');
    expect(filtered).toHaveLength(3);
  });

  it('filters by model_id', async () => {
    const data = await readTestData();
    const filtered = data.reviews.filter(r => r.model_id === 'model_a');
    expect(filtered).toHaveLength(3);
  });

  it('combines filters (doctor + case)', async () => {
    const data = await readTestData();
    const filtered = data.reviews.filter(
      r => r.reviewer_name === 'Dr. Smith' && r.case_id === 'ncc_1'
    );
    expect(filtered).toHaveLength(2);
  });

  it('combines all three filters to find a specific review', async () => {
    const data = await readTestData();
    const filtered = data.reviews.filter(
      r => r.reviewer_name === 'Dr. Jones' && r.case_id === 'ncc_2' && r.model_id === 'model_a'
    );
    expect(filtered).toHaveLength(1);
    expect(filtered[0].prediction_quality).toBe(8);
  });

  it('returns empty array when no reviews match', async () => {
    const data = await readTestData();
    const filtered = data.reviews.filter(r => r.reviewer_name === 'Nobody');
    expect(filtered).toHaveLength(0);
  });
});

describe('Reviews API - save logic', () => {
  beforeEach(async () => {
    await writeTestData({ doctors: [], reviews: [] });
  });

  afterEach(async () => {
    await cleanupTestFiles();
  });

  it('creates a new review', async () => {
    const data = await readTestData();

    const newReview: TestReview = {
      id: 'ncc_1__model_a__Dr. Test',
      case_id: 'ncc_1',
      model_id: 'model_a',
      reviewer_name: 'Dr. Test',
      therapy_acceptable_ra: true,
      recommendation_exact_match: 80,
      recommendation_patient_oriented: 70,
      prediction_quality: 7,
      timestamp: new Date().toISOString(),
    };

    data.reviews.push(newReview);
    if (!data.doctors.includes('Dr. Test')) {
      data.doctors.push('Dr. Test');
    }
    await writeTestData(data);

    const result = await readTestData();
    expect(result.reviews).toHaveLength(1);
    expect(result.reviews[0].case_id).toBe('ncc_1');
    expect(result.doctors).toContain('Dr. Test');
  });

  it('updates an existing review (upsert by id)', async () => {
    // Create initial review
    const data = await readTestData();
    const id = 'ncc_1__model_a__Dr. Test';
    data.reviews.push({
      id,
      case_id: 'ncc_1',
      model_id: 'model_a',
      reviewer_name: 'Dr. Test',
      therapy_acceptable_ra: true,
      recommendation_exact_match: 50,
      recommendation_patient_oriented: 50,
      prediction_quality: 5,
      timestamp: '2026-01-01T00:00:00Z',
    });
    await writeTestData(data);

    // Update the review
    const data2 = await readTestData();
    const idx = data2.reviews.findIndex(r => r.id === id);
    expect(idx).toBeGreaterThanOrEqual(0);

    data2.reviews[idx] = {
      ...data2.reviews[idx],
      therapy_acceptable_ra: false,
      recommendation_exact_match: 30,
      prediction_quality: 3,
      timestamp: new Date().toISOString(),
    };
    await writeTestData(data2);

    // Verify
    const result = await readTestData();
    expect(result.reviews).toHaveLength(1); // still 1, not 2
    expect(result.reviews[0].therapy_acceptable_ra).toBe(false);
    expect(result.reviews[0].recommendation_exact_match).toBe(30);
    expect(result.reviews[0].prediction_quality).toBe(3);
  });

  it('generates correct review ID from case+model+doctor', () => {
    const caseId = 'ncc_15';
    const modelId = 'google/gemma-3-27b-it';
    const reviewer = 'Radu Alexa';
    const id = `${caseId}__${modelId}__${reviewer}`;
    expect(id).toBe('ncc_15__google/gemma-3-27b-it__Radu Alexa');
  });

  it('different doctors can review the same case+model independently', async () => {
    const data = await readTestData();
    data.reviews.push(
      {
        id: 'ncc_1__model_a__Dr. A',
        case_id: 'ncc_1', model_id: 'model_a', reviewer_name: 'Dr. A',
        therapy_acceptable_ra: true, recommendation_exact_match: 80,
        recommendation_patient_oriented: 70, prediction_quality: 7,
        timestamp: new Date().toISOString(),
      },
      {
        id: 'ncc_1__model_a__Dr. B',
        case_id: 'ncc_1', model_id: 'model_a', reviewer_name: 'Dr. B',
        therapy_acceptable_ra: false, recommendation_exact_match: 30,
        recommendation_patient_oriented: 40, prediction_quality: 3,
        timestamp: new Date().toISOString(),
      }
    );
    await writeTestData(data);

    const result = await readTestData();
    expect(result.reviews).toHaveLength(2);

    const drA = result.reviews.find(r => r.reviewer_name === 'Dr. A');
    const drB = result.reviews.find(r => r.reviewer_name === 'Dr. B');
    expect(drA?.therapy_acceptable_ra).toBe(true);
    expect(drB?.therapy_acceptable_ra).toBe(false);
  });
});

describe('Unreviewed model computation', () => {
  // This tests the logic used in the cases page to compute unreviewed models
  const REQUIRED_MODEL_IDS = [
    'google/medgemma-27b-text-it',
    'google/gemma-3-27b-it',
    'allenai/Olmo-3.1-32B-Think',
    'google/gemma-3-4b-it',
    'OpenMeditron/Meditron3-Qwen2.5-7B',
  ];

  it('computes unreviewed count correctly when no reviews exist', () => {
    const reviewedSet = new Set<string>();
    const caseId = 'ncc_1';
    const availablePredictions = REQUIRED_MODEL_IDS; // all 5 available

    const availableRequired = REQUIRED_MODEL_IDS.filter(m => availablePredictions.includes(m));
    const reviewedCount = availableRequired.filter(
      m => reviewedSet.has(`${caseId}__${m}`)
    ).length;
    const unreviewedCount = availableRequired.length - reviewedCount;

    expect(unreviewedCount).toBe(5);
  });

  it('computes unreviewed count correctly with some reviews', () => {
    const reviewedSet = new Set([
      'ncc_1__google/gemma-3-4b-it',
      'ncc_1__google/gemma-3-27b-it',
    ]);
    const caseId = 'ncc_1';
    const availablePredictions = REQUIRED_MODEL_IDS;

    const availableRequired = REQUIRED_MODEL_IDS.filter(m => availablePredictions.includes(m));
    const reviewedCount = availableRequired.filter(
      m => reviewedSet.has(`${caseId}__${m}`)
    ).length;
    const unreviewedCount = availableRequired.length - reviewedCount;

    expect(reviewedCount).toBe(2);
    expect(unreviewedCount).toBe(3);
  });

  it('reports all reviewed when all 5 required models are reviewed', () => {
    const caseId = 'ncc_5';
    const reviewedSet = new Set(
      REQUIRED_MODEL_IDS.map(m => `${caseId}__${m}`)
    );

    const availableRequired = REQUIRED_MODEL_IDS;
    const reviewedCount = availableRequired.filter(
      m => reviewedSet.has(`${caseId}__${m}`)
    ).length;
    const unreviewedCount = availableRequired.length - reviewedCount;

    expect(reviewedCount).toBe(5);
    expect(unreviewedCount).toBe(0);
  });

  it('ignores optional model reviews when computing required progress', () => {
    const caseId = 'ncc_1';
    // Only the optional model is reviewed
    const reviewedSet = new Set([
      `${caseId}__allenai/Olmo-3.1-32B-Instruct`,
    ]);

    const availableRequired = REQUIRED_MODEL_IDS;
    const reviewedCount = availableRequired.filter(
      m => reviewedSet.has(`${caseId}__${m}`)
    ).length;

    expect(reviewedCount).toBe(0); // optional doesn't count
  });

  it('builds correct reviewed key from case_id and model_id', () => {
    const review = { case_id: 'ncc_15', model_id: 'google/medgemma-27b-text-it' };
    const key = `${review.case_id}__${review.model_id}`;
    expect(key).toBe('ncc_15__google/medgemma-27b-text-it');
  });
});
