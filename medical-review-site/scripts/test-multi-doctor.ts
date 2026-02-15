#!/usr/bin/env npx tsx
/**
 * Test script for multi-doctor review system
 *
 * Tests:
 * 1. Doctor registration
 * 2. Multiple doctors can have separate reviews for same case+model
 * 3. Concurrent access doesn't corrupt data
 * 4. Reviews are isolated per doctor
 * 5. Export filters work correctly
 *
 * Run with: npx tsx scripts/test-multi-doctor.ts
 * (requires the dev server to be running: npm run dev)
 */

const BASE_URL = 'http://localhost:3000';

interface Review {
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

interface Doctor {
  name: string;
  reviewCount: number;
}

async function registerDoctor(name: string): Promise<Doctor> {
  const res = await fetch(`${BASE_URL}/api/doctors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return { name: data.doctor.name, reviewCount: 0 };
}

async function getDoctors(): Promise<Doctor[]> {
  const res = await fetch(`${BASE_URL}/api/doctors`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return data.doctors;
}

async function saveReview(review: Omit<Review, 'id' | 'timestamp'>): Promise<Review> {
  const res = await fetch(`${BASE_URL}/api/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(review),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return data.review;
}

async function getReviews(filters?: { doctor?: string; caseId?: string; modelId?: string }): Promise<Review[]> {
  const params = new URLSearchParams();
  if (filters?.doctor) params.set('doctor', filters.doctor);
  if (filters?.caseId) params.set('case', filters.caseId);
  if (filters?.modelId) params.set('model', filters.modelId);

  const url = `${BASE_URL}/api/reviews${params.toString() ? `?${params}` : ''}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return data.reviews;
}

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

async function test1_DoctorRegistration(): Promise<void> {
  console.log('\n📋 Test 1: Doctor Registration');

  // Register new doctors
  const dr1 = await registerDoctor('Dr. Test Schmidt');
  const dr2 = await registerDoctor('Dr. Test Mueller');

  // Verify they're registered
  const doctors = await getDoctors();
  const dr1Found = doctors.find(d => d.name === 'Dr. Test Schmidt');
  const dr2Found = doctors.find(d => d.name === 'Dr. Test Mueller');

  assert(!!dr1Found, 'Dr. Test Schmidt should be registered');
  assert(!!dr2Found, 'Dr. Test Mueller should be registered');

  // Re-registering same doctor should work (idempotent)
  const dr1Again = await registerDoctor('Dr. Test Schmidt');
  assert(dr1Again.name === dr1.name, 'Re-registration should return same doctor');

  console.log('✅ Doctor registration works correctly');
}

async function test2_SeparateReviewsPerDoctor(): Promise<void> {
  console.log('\n📋 Test 2: Separate Reviews Per Doctor');

  const caseId = 'ncc_test_1';
  const modelId = 'test_model';

  // Dr. Schmidt saves a review
  const review1 = await saveReview({
    case_id: caseId,
    model_id: modelId,
    reviewer_name: 'Dr. Test Schmidt',
    therapy_acceptable_ra: true,
    recommendation_exact_match: 80,
    recommendation_patient_oriented: 90,
    prediction_quality: 8,
  });

  // Dr. Mueller saves a DIFFERENT review for the same case+model
  const review2 = await saveReview({
    case_id: caseId,
    model_id: modelId,
    reviewer_name: 'Dr. Test Mueller',
    therapy_acceptable_ra: false,
    recommendation_exact_match: 40,
    recommendation_patient_oriented: 50,
    prediction_quality: 4,
  });

  // Verify reviews have different IDs
  assert(review1.id !== review2.id, 'Reviews should have different IDs');
  assert(review1.id.includes('Dr. Test Schmidt'), 'Review 1 ID should include doctor name');
  assert(review2.id.includes('Dr. Test Mueller'), 'Review 2 ID should include doctor name');

  // Verify each doctor only sees their own review
  const schmidtReviews = await getReviews({ doctor: 'Dr. Test Schmidt', caseId });
  const muellerReviews = await getReviews({ doctor: 'Dr. Test Mueller', caseId });

  assert(schmidtReviews.length === 1, 'Dr. Schmidt should have 1 review');
  assert(muellerReviews.length === 1, 'Dr. Mueller should have 1 review');
  assert(schmidtReviews[0].therapy_acceptable_ra === true, 'Dr. Schmidt review should be acceptable=true');
  assert(muellerReviews[0].therapy_acceptable_ra === false, 'Dr. Mueller review should be acceptable=false');

  console.log('✅ Reviews are properly isolated per doctor');
}

async function test3_UpdateDoesNotOverwrite(): Promise<void> {
  console.log('\n📋 Test 3: Update Does Not Overwrite Other Doctors');

  const caseId = 'ncc_test_2';
  const modelId = 'test_model';

  // Dr. Schmidt saves initial review
  await saveReview({
    case_id: caseId,
    model_id: modelId,
    reviewer_name: 'Dr. Test Schmidt',
    therapy_acceptable_ra: true,
    recommendation_exact_match: 70,
    recommendation_patient_oriented: 70,
    prediction_quality: 7,
  });

  // Dr. Mueller saves review
  await saveReview({
    case_id: caseId,
    model_id: modelId,
    reviewer_name: 'Dr. Test Mueller',
    therapy_acceptable_ra: false,
    recommendation_exact_match: 30,
    recommendation_patient_oriented: 30,
    prediction_quality: 3,
  });

  // Dr. Schmidt updates their review
  await saveReview({
    case_id: caseId,
    model_id: modelId,
    reviewer_name: 'Dr. Test Schmidt',
    therapy_acceptable_ra: false, // Changed!
    recommendation_exact_match: 60,
    recommendation_patient_oriented: 60,
    prediction_quality: 6,
  });

  // Verify Dr. Mueller's review is unchanged
  const muellerReviews = await getReviews({ doctor: 'Dr. Test Mueller', caseId });
  assert(muellerReviews.length === 1, 'Dr. Mueller should still have 1 review');
  assert(muellerReviews[0].prediction_quality === 3, 'Dr. Mueller review should be unchanged');

  // Verify Dr. Schmidt's review is updated
  const schmidtReviews = await getReviews({ doctor: 'Dr. Test Schmidt', caseId });
  assert(schmidtReviews.length === 1, 'Dr. Schmidt should have 1 review (not 2)');
  assert(schmidtReviews[0].therapy_acceptable_ra === false, 'Dr. Schmidt review should be updated');
  assert(schmidtReviews[0].prediction_quality === 6, 'Dr. Schmidt review quality should be 6');

  console.log('✅ Updates only affect the updating doctor\'s review');
}

async function test4_ConcurrentAccess(): Promise<void> {
  console.log('\n📋 Test 4: Concurrent Access');

  const caseId = 'ncc_concurrent';

  // Simulate 10 concurrent saves from different doctors
  const doctors = ['Dr. A', 'Dr. B', 'Dr. C', 'Dr. D', 'Dr. E', 'Dr. F', 'Dr. G', 'Dr. H', 'Dr. I', 'Dr. J'];

  const promises = doctors.map((doctor, i) =>
    saveReview({
      case_id: caseId,
      model_id: 'model_concurrent',
      reviewer_name: doctor,
      therapy_acceptable_ra: i % 2 === 0,
      recommendation_exact_match: i * 10,
      recommendation_patient_oriented: i * 10,
      prediction_quality: i,
    })
  );

  await Promise.all(promises);

  // Verify all reviews were saved correctly
  const allReviews = await getReviews({ caseId });
  const concurrentReviews = allReviews.filter(r => r.model_id === 'model_concurrent');

  assert(concurrentReviews.length === 10, `Should have 10 concurrent reviews, got ${concurrentReviews.length}`);

  // Verify each doctor's review has correct values
  for (let i = 0; i < doctors.length; i++) {
    const review = concurrentReviews.find(r => r.reviewer_name === doctors[i]);
    assert(!!review, `Review for ${doctors[i]} should exist`);
    assert(review!.prediction_quality === i, `${doctors[i]} quality should be ${i}, got ${review!.prediction_quality}`);
  }

  console.log('✅ Concurrent access works correctly');
}

async function test5_ExportFiltering(): Promise<void> {
  console.log('\n📋 Test 5: Export Filtering');

  // Test export for specific doctor
  const schmidtRes = await fetch(`${BASE_URL}/api/export?doctor=Dr.%20Test%20Schmidt`);
  if (schmidtRes.status === 404) {
    console.log('⚠️  No reviews to export for Dr. Schmidt (expected if tests cleaned up)');
  } else {
    assert(schmidtRes.ok, 'Export should succeed');
    const csv = await schmidtRes.text();
    assert(csv.includes('Dr. Test Schmidt'), 'Export should include Dr. Schmidt reviews');
    assert(!csv.includes('Dr. Test Mueller'), 'Export should NOT include Dr. Mueller reviews');
    console.log('✅ Export filtering works correctly');
  }
}

async function runTests(): Promise<void> {
  console.log('🧪 Multi-Doctor Review System Tests');
  console.log('====================================');

  try {
    // Check if server is running
    const healthCheck = await fetch(`${BASE_URL}/api/doctors`).catch(() => null);
    if (!healthCheck) {
      console.error('❌ Server not running. Start with: npm run dev');
      process.exit(1);
    }

    await test1_DoctorRegistration();
    await test2_SeparateReviewsPerDoctor();
    await test3_UpdateDoesNotOverwrite();
    await test4_ConcurrentAccess();
    await test5_ExportFiltering();

    console.log('\n====================================');
    console.log('✅ All tests passed!');

  } catch (error) {
    console.error('\n====================================');
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

runTests();
