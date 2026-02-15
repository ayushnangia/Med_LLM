import { notFound } from 'next/navigation';
import { JudgeReviewClient } from '@/components/JudgeReviewClient';
import { getCaseById, getAllCases } from '@/lib/data';

interface JudgeReviewPageProps {
  params: Promise<{ id: string }>;
}

// Generate static params for all cases
export async function generateStaticParams() {
  const cases = getAllCases();
  return cases.map(c => ({ id: c.case_id }));
}

export default async function JudgeReviewPage({ params }: JudgeReviewPageProps) {
  const { id } = await params;
  const caseItem = getCaseById(id);

  if (!caseItem) {
    notFound();
  }

  // All cases serve as the navigation list for judge review
  // (the component will filter to only those with completed blind reviews)
  const allCases = getAllCases();
  const currentIndex = allCases.findIndex(c => c.case_id === id);

  return (
    <JudgeReviewClient
      key={caseItem.case_id}
      caseItem={caseItem}
      allReviewableCases={allCases}
      currentIndex={currentIndex}
    />
  );
}
