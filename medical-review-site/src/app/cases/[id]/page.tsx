import { notFound } from 'next/navigation';
import { CaseDetailClient } from '@/components/CaseDetailClient';
import { getCaseById, getAllCases } from '@/lib/data';

interface CaseDetailPageProps {
  params: Promise<{ id: string }>;
}

// Generate static params for all cases (required for static export)
export async function generateStaticParams() {
  const cases = getAllCases();
  return cases.map(c => ({ id: c.case_id }));
}

export default async function CaseDetailPage({ params }: CaseDetailPageProps) {
  const { id } = await params;
  const caseItem = getCaseById(id);

  if (!caseItem) {
    notFound();
  }

  const allCases = getAllCases();
  const currentIndex = allCases.findIndex(c => c.case_id === id);

  return (
    <CaseDetailClient
      key={caseItem.case_id}
      caseItem={caseItem}
      allCases={allCases}
      currentIndex={currentIndex}
    />
  );
}
