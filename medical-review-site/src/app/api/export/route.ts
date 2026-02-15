import { NextRequest, NextResponse } from 'next/server';
import { getReviews } from '@/lib/server-storage';

// GET /api/export - Export reviews as CSV (optional ?doctor=name filter)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const doctor = searchParams.get('doctor') || undefined;

    const reviews = await getReviews(doctor ? { doctor } : undefined);

    if (reviews.length === 0) {
      return NextResponse.json({ error: 'No reviews to export' }, { status: 404 });
    }

    const headers = [
      'case_id', 'model_id', 'reviewer_name', 'therapy_acceptable_ra',
      'recommendation_exact_match', 'recommendation_patient_oriented',
      'prediction_quality', 'timestamp',
    ];

    const rows = reviews.map(r => [
      r.case_id,
      r.model_id,
      r.reviewer_name,
      r.therapy_acceptable_ra === null ? '' : r.therapy_acceptable_ra ? 'Ja' : 'Nein',
      r.recommendation_exact_match === null ? '' : r.recommendation_exact_match.toString(),
      r.recommendation_patient_oriented === null ? '' : r.recommendation_patient_oriented.toString(),
      r.prediction_quality === null ? '' : r.prediction_quality.toString(),
      r.timestamp,
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n');

    const filename = doctor
      ? `arzt-bewertungen_${doctor}_${new Date().toISOString().split('T')[0]}.csv`
      : `arzt-bewertungen_alle_${new Date().toISOString().split('T')[0]}.csv`;

    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Error exporting reviews:', error);
    return NextResponse.json({ error: 'Failed to export reviews' }, { status: 500 });
  }
}
