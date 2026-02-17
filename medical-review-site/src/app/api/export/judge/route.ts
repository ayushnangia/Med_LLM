import { NextRequest, NextResponse } from 'next/server';
import { getJudgeReviews } from '@/lib/server-storage';

// GET /api/export/judge - Export judge reviews as CSV (optional ?doctor=name filter)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const doctor = searchParams.get('doctor') || undefined;

    const reviews = await getJudgeReviews(doctor ? { doctor } : undefined);

    if (reviews.length === 0) {
      return NextResponse.json({ error: 'No judge reviews to export' }, { status: 404 });
    }

    const headers = [
      'case_id', 'model_id', 'reviewer_name', 'judge_model', 'judge_correct',
      'judge_reasoning_quality', 'comment',
      'doctor_acceptable', 'doctor_quality',
      'judge_is_correct', 'judge_overall_score',
      'created_at',
    ];

    const rows = reviews.map(r => [
      r.case_id,
      r.model_id,
      r.reviewer_name,
      r.judge_model ?? 'openai/gpt-5.2',
      r.judge_correct ?? '',
      r.judge_reasoning_quality?.toString() ?? '',
      r.comment ?? '',
      r.doctor_acceptable === null ? '' : r.doctor_acceptable ? 'Ja' : 'Nein',
      r.doctor_quality?.toString() ?? '',
      r.judge_is_correct === null ? '' : r.judge_is_correct ? 'Ja' : 'Nein',
      r.judge_overall_score?.toString() ?? '',
      r.created_at,
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n');

    const filename = doctor
      ? `richter-bewertungen_${doctor}_${new Date().toISOString().split('T')[0]}.csv`
      : `richter-bewertungen_alle_${new Date().toISOString().split('T')[0]}.csv`;

    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Error exporting judge reviews:', error);
    return NextResponse.json({ error: 'Failed to export judge reviews' }, { status: 500 });
  }
}
