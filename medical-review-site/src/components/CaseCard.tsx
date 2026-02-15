'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CountBadge } from './ScoreBadge';
import { useI18n } from '@/lib/i18n';
import type { Case } from '@/lib/types';
import { getCaseCorrectCount } from '@/lib/data';
import { CheckCircle, Scale } from 'lucide-react';

interface CaseCardProps {
  caseItem: Case;
  reviewedRequiredCount?: number;
  totalRequiredCount?: number;
}

export function CaseCard({ caseItem, reviewedRequiredCount, totalRequiredCount }: CaseCardProps) {
  const { t } = useI18n();
  const router = useRouter();
  const correctCount = getCaseCorrectCount(caseItem);
  const totalModels = Object.keys(caseItem.predictions).length;

  const hasProgressInfo = reviewedRequiredCount !== undefined && totalRequiredCount !== undefined;
  const allRequiredDone = hasProgressInfo && reviewedRequiredCount >= totalRequiredCount;

  return (
    <Link href={`/cases/${caseItem.case_id}`}>
      <Card className={`hover:border-primary transition-colors cursor-pointer h-full ${allRequiredDone ? 'opacity-60' : ''}`}>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{caseItem.case_id}</CardTitle>
              {allRequiredDone && (
                <CheckCircle className="h-4 w-4 text-green-600" />
              )}
            </div>
            <div className="flex items-center gap-1">
              {hasProgressInfo && (
                <Badge
                  variant={allRequiredDone ? 'secondary' : 'outline'}
                  className={`text-xs ${!allRequiredDone ? 'border-amber-400 text-amber-700 dark:text-amber-400' : ''}`}
                >
                  {allRequiredDone
                    ? t('cases.allReviewed')
                    : t('cases.reviewedOf', { done: reviewedRequiredCount, total: totalRequiredCount })}
                </Badge>
              )}
              <CountBadge correct={correctCount} total={totalModels} />
            </div>
          </div>
          <p className="text-sm text-muted-foreground">{caseItem.patient.name}</p>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Patient Info */}
          <div className="flex flex-wrap gap-2 text-sm">
            {caseItem.patient.age && (
              <Badge variant="outline">{caseItem.patient.age} Jahre</Badge>
            )}
            {caseItem.patient.ecog !== null && (
              <Badge variant="outline">ECOG {caseItem.patient.ecog}</Badge>
            )}
            {caseItem.patient.karnofsky !== null && (
              <Badge variant="outline">Karnofsky {caseItem.patient.karnofsky}%</Badge>
            )}
          </div>

          {/* Diagnosis */}
          <div className="space-y-1">
            <p className="text-sm font-medium line-clamp-2">
              {caseItem.diagnosis.diagnose_kurz}
            </p>
            <div className="flex flex-wrap gap-2">
              <Badge variant={caseItem.ground_truth.metastatic ? 'destructive' : 'secondary'}>
                {caseItem.ground_truth.metastatic ? t('cases.metastatic') : t('cases.nonMetastatic')}
              </Badge>
              {caseItem.diagnosis.stadium && (
                <Badge variant="outline" className="text-xs">
                  {caseItem.diagnosis.stadium.length > 30
                    ? caseItem.diagnosis.stadium.substring(0, 30) + '...'
                    : caseItem.diagnosis.stadium}
                </Badge>
              )}
            </div>
          </div>

          {/* Ground Truth Therapy Preview */}
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">{t('cases.recommendedTherapy')}</p>
            <p className="text-sm line-clamp-2">{caseItem.ground_truth.therapy}</p>
          </div>

          {/* Progress bar for required models */}
          {hasProgressInfo && totalRequiredCount > 0 && (
            <div className="pt-1">
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all ${allRequiredDone ? 'bg-green-500' : 'bg-amber-500'}`}
                  style={{ width: `${(reviewedRequiredCount / totalRequiredCount) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Judge Review CTA bar for completed cases */}
          {allRequiredDone && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                router.push(`/judge-review/${caseItem.case_id}`);
              }}
              className="w-full flex items-center justify-center gap-2 mt-2 px-3 py-2 rounded-md bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 dark:bg-purple-700 dark:hover:bg-purple-800 transition-colors"
            >
              <Scale className="h-4 w-4" />
              {t('cases.reviewJudge')}
              <span aria-hidden="true">&rarr;</span>
            </button>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
