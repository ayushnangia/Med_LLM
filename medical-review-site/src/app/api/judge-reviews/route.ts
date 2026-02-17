import { NextRequest, NextResponse } from 'next/server';
import { getJudgeReviews, upsertJudgeReview, upsertJudgeReviewsBatch } from '@/lib/server-storage';

// GET /api/judge-reviews - Get judge reviews (optional filters: ?doctor=name&case=id)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const reviews = await getJudgeReviews({
      doctor: searchParams.get('doctor') || undefined,
      caseId: searchParams.get('case') || undefined,
      modelId: searchParams.get('model') || undefined,
      judgeModel: searchParams.get('judge_model') || undefined,
    });
    return NextResponse.json({ reviews });
  } catch (error) {
    console.error('Error reading judge reviews:', error);
    return NextResponse.json({ error: 'Failed to read judge reviews' }, { status: 500 });
  }
}

// POST /api/judge-reviews - Save one or many judge reviews
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Batch save
    if (Array.isArray(body.reviews)) {
      for (const r of body.reviews) {
        if (!r.case_id || !r.model_id || !r.reviewer_name || !r.judge_correct) {
          return NextResponse.json(
            { error: 'Missing required fields: case_id, model_id, reviewer_name, judge_correct' },
            { status: 400 }
          );
        }
      }
      const saved = await upsertJudgeReviewsBatch(body.reviews);
      return NextResponse.json({ reviews: saved, message: `${saved.length} judge reviews saved` });
    }

    // Single save
    const { case_id, model_id, reviewer_name, judge_correct } = body;
    if (!case_id || !model_id || !reviewer_name || !judge_correct) {
      return NextResponse.json(
        { error: 'Missing required fields: case_id, model_id, reviewer_name, judge_correct' },
        { status: 400 }
      );
    }

    const review = await upsertJudgeReview(body);
    return NextResponse.json({ review, message: 'Judge review saved successfully' });
  } catch (error) {
    console.error('Error saving judge review:', error);
    return NextResponse.json({ error: 'Failed to save judge review' }, { status: 500 });
  }
}
