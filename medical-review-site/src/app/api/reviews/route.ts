import { NextRequest, NextResponse } from 'next/server';
import { getReviews, upsertReview, upsertReviewsBatch } from '@/lib/server-storage';

// GET /api/reviews - Get reviews (optional filters: ?doctor=name&case=id&model=id)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const reviews = await getReviews({
      doctor: searchParams.get('doctor') || undefined,
      caseId: searchParams.get('case') || undefined,
      modelId: searchParams.get('model') || undefined,
    });
    return NextResponse.json({ reviews });
  } catch (error) {
    console.error('Error reading reviews:', error);
    return NextResponse.json({ error: 'Failed to read reviews' }, { status: 500 });
  }
}

// POST /api/reviews - Save one or many reviews
// Body: single review object OR { reviews: [...] } for batch
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Batch save
    if (Array.isArray(body.reviews)) {
      for (const r of body.reviews) {
        if (!r.case_id || !r.model_id || !r.reviewer_name) {
          return NextResponse.json(
            { error: 'Missing required fields: case_id, model_id, reviewer_name' },
            { status: 400 }
          );
        }
      }
      const saved = await upsertReviewsBatch(body.reviews);
      return NextResponse.json({ reviews: saved, message: `${saved.length} reviews saved` });
    }

    // Single save
    const { case_id, model_id, reviewer_name } = body;
    if (!case_id || !model_id || !reviewer_name) {
      return NextResponse.json(
        { error: 'Missing required fields: case_id, model_id, reviewer_name' },
        { status: 400 }
      );
    }

    const review = await upsertReview(body);
    return NextResponse.json({ review, message: 'Review saved successfully' });
  } catch (error) {
    console.error('Error saving review:', error);
    return NextResponse.json({ error: 'Failed to save review' }, { status: 500 });
  }
}
