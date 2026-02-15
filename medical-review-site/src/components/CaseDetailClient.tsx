'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { ModelSelector } from '@/components/ModelSelector';
import { ModelGrid } from '@/components/ModelGrid';
import { ClinicalContextDisplay } from '@/components/ClinicalContext';
import { getReviewerName, getReviewsFromServer, setSelectedModels } from '@/lib/storage';
import { REQUIRED_MODEL_IDS } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import { ChevronLeft, ChevronRight, Home, User, Activity, ClipboardCheck, CheckCircle } from 'lucide-react';
import type { Case } from '@/lib/types';
import type { DoctorReviewResponse } from '@/lib/storage';

interface CaseDetailClientProps {
  caseItem: Case;
  allCases: Case[];
  currentIndex: number;
}

export function CaseDetailClient({ caseItem, allCases, currentIndex }: CaseDetailClientProps) {
  const { t, language } = useI18n();
  const [selectedModels, setSelectedModelsState] = useState<string[]>([]);
  const [reviewerName, setReviewerNameState] = useState('');
  const [reviewedModels, setReviewedModels] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);
  const initializedRef = useRef(false);

  const availableModels = useMemo(() => Object.keys(caseItem.predictions), [caseItem.predictions]);
  const prevCase = currentIndex > 0 ? allCases[currentIndex - 1] : null;
  const nextCase = currentIndex < allCases.length - 1 ? allCases[currentIndex + 1] : null;

  // Compute review progress for required models
  const requiredModelsInCase = useMemo(
    () => REQUIRED_MODEL_IDS.filter(m => availableModels.includes(m)),
    [availableModels]
  );
  const reviewedRequiredCount = useMemo(
    () => requiredModelsInCase.filter(m => reviewedModels.has(m)).length,
    [requiredModelsInCase, reviewedModels]
  );

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    setMounted(true);

    const name = getReviewerName();
    setReviewerNameState(name);

    // Fetch reviews and select all models by default
    const init = async () => {
      // Always show all models by default
      setSelectedModelsState(availableModels);
      setSelectedModels(availableModels);

      if (!name) return;

      try {
        const reviews = await getReviewsFromServer({
          caseId: caseItem.case_id,
          doctor: name,
        });
        const reviewedSet = new Set(reviews.map(r => r.model_id));
        setReviewedModels(reviewedSet);
      } catch (error) {
        console.error('Failed to load reviews:', error);
      }
    };

    init();
  }, []);

  // Update reviewedModels when a single review is saved
  const handleReviewSaved = useCallback((modelId: string) => {
    setReviewedModels(prev => {
      const next = new Set(prev);
      next.add(modelId);
      return next;
    });
  }, []);

  // Listen for save-all-done event to batch-update reviewedModels
  useEffect(() => {
    const handleSaveAllDone = (e: Event) => {
      const savedReviews = (e as CustomEvent).detail.reviews as DoctorReviewResponse[];
      setReviewedModels(prev => {
        const next = new Set(prev);
        for (const r of savedReviews) {
          next.add(r.model_id);
        }
        return next;
      });
    };

    window.addEventListener('save-all-done', handleSaveAllDone);
    return () => window.removeEventListener('save-all-done', handleSaveAllDone);
  }, []);

  const handleModelSelectionChange = (selected: string[]) => {
    setSelectedModelsState(selected);
  };

  if (!mounted) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted-foreground">{t('case.loadingCase')}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Compact Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <Home className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">{reviewerName || t('case.reviewer')}</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-2">
          {prevCase ? (
            <Link href={`/cases/${prevCase.case_id}`}>
              <Button variant="outline" size="sm">
                <ChevronLeft className="h-4 w-4 mr-1" />
                {t('case.back')}
              </Button>
            </Link>
          ) : (
            <Button variant="outline" size="sm" disabled>
              <ChevronLeft className="h-4 w-4 mr-1" />
              {t('case.back')}
            </Button>
          )}

          <Badge variant="secondary" className="px-3">
            {t('case.caseOf', { current: currentIndex + 1, total: allCases.length })}
          </Badge>

          {nextCase ? (
            <Link href={`/cases/${nextCase.case_id}`}>
              <Button variant="outline" size="sm">
                {t('case.next')}
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          ) : (
            <Button variant="outline" size="sm" disabled>
              {t('case.next')}
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </div>

      {/* Review Progress Banner */}
      {reviewerName && requiredModelsInCase.length > 0 && (
        reviewedRequiredCount >= requiredModelsInCase.length ? (
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200">
            <CheckCircle className="h-4 w-4" />
            <span>
              {t('case.reviewProgress', { done: reviewedRequiredCount, total: requiredModelsInCase.length })}
            </span>
            <div className="flex-1 max-w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 ml-2">
              <div
                className="h-1.5 rounded-full transition-all bg-green-500"
                style={{ width: '100%' }}
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200">
            <ClipboardCheck className="h-4 w-4" />
            <span>
              {t('case.reviewProgress', { done: reviewedRequiredCount, total: requiredModelsInCase.length })}
            </span>
            <div className="flex-1 max-w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 ml-2">
              <div
                className="h-1.5 rounded-full transition-all bg-amber-500"
                style={{ width: `${(reviewedRequiredCount / requiredModelsInCase.length) * 100}%` }}
              />
            </div>
          </div>
        )
      )}

      {/* Patient Info - Expanded */}
      <Card>
        <CardContent className="py-4">
          <div className="space-y-3">
            {/* Row 1: Patient basics */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <span className="font-semibold text-lg">{caseItem.patient.name}</span>
              {caseItem.patient.age && (
                <Badge variant="outline" className="font-normal">
                  {caseItem.patient.age} {language === 'de' ? 'Jahre' : 'years'}
                </Badge>
              )}
              {caseItem.patient.ecog !== null && (
                <Badge variant="secondary">ECOG: {caseItem.patient.ecog}</Badge>
              )}
              {(caseItem.patient.karnofsky !== null || caseItem.patient.karnofsky_from_labor) && (
                <Badge variant="secondary">
                  Karnofsky: {caseItem.patient.karnofsky ?? caseItem.patient.karnofsky_from_labor}%
                </Badge>
              )}
              {caseItem.patient.comorbidity && caseItem.patient.comorbidity !== 'unknown' && (
                <Badge variant={caseItem.patient.comorbidity === 'hoch' ? 'destructive' : 'outline'}>
                  {language === 'de' ? 'Komorbidität' : 'Comorbidity'}: {caseItem.patient.comorbidity}
                </Badge>
              )}
            </div>

            {/* Row 2: Diagnosis */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{caseItem.diagnosis.diagnose_kurz}</span>
              <Badge variant={caseItem.ground_truth.metastatic ? 'destructive' : 'secondary'}>
                {caseItem.ground_truth.metastatic ? t('case.metastatic') : t('case.nonMetastatic')}
              </Badge>
              {caseItem.diagnosis.histologie_subtyp && (
                <Badge variant="outline">{caseItem.diagnosis.histologie_subtyp}</Badge>
              )}
              {caseItem.diagnosis.klarzellig !== null && (
                <Badge variant={caseItem.diagnosis.klarzellig ? 'default' : 'secondary'}>
                  {caseItem.diagnosis.klarzellig
                    ? (language === 'de' ? 'Klarzellig' : 'Clear cell')
                    : (language === 'de' ? 'Nicht-klarzellig' : 'Non-clear cell')}
                </Badge>
              )}
              {caseItem.diagnosis.stadium && (
                <Badge variant="outline">{caseItem.diagnosis.stadium}</Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ground Truth - Green Box */}
      <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <h3 className="font-semibold text-green-800 dark:text-green-200 mb-2 text-sm">
          {t('case.groundTruth')}
        </h3>
        <p className="text-sm">{caseItem.ground_truth.therapy}</p>
      </div>

      {/* Clinical Context - Full medical information */}
      <ClinicalContextDisplay
        patient={caseItem.patient}
        diagnosis={caseItem.diagnosis}
        context={caseItem.clinical_context}
      />

      {/* Model Selector */}
      <ModelSelector
        availableModels={availableModels}
        selectedModels={selectedModels}
        onChange={handleModelSelectionChange}
        reviewedModels={reviewedModels}
      />

      {/* Reviewer Reference: Diagnose + Soll-Therapie */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span className="font-semibold">{language === 'de' ? 'Diagnose' : 'Diagnosis'}:</span>
          <span>{caseItem.diagnosis.diagnose_kurz}</span>
          <Badge variant={caseItem.ground_truth.metastatic ? 'destructive' : 'secondary'} className="text-xs">
            {caseItem.ground_truth.metastatic ? t('case.metastatic') : t('case.nonMetastatic')}
          </Badge>
          {caseItem.diagnosis.histologie_subtyp && (
            <span className="text-muted-foreground">{caseItem.diagnosis.histologie_subtyp}</span>
          )}
          {caseItem.diagnosis.stadium && (
            <span className="text-muted-foreground">{caseItem.diagnosis.stadium}</span>
          )}
        </div>
        <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg px-3 py-2">
          <span className="font-semibold text-green-800 dark:text-green-200 text-sm">{t('case.groundTruth')}: </span>
          <span className="text-sm">{caseItem.ground_truth.therapy}</span>
        </div>
      </div>

      {/* Model Grid */}
      <ModelGrid
        caseItem={caseItem}
        selectedModels={selectedModels}
        reviewedModels={reviewedModels}
        onReviewSaved={handleReviewSaved}
        allReviewsDone={reviewedRequiredCount >= requiredModelsInCase.length}
        nextCaseHref={nextCase ? `/cases/${nextCase.case_id}` : '/'}
        nextCaseLabel={nextCase ? nextCase.case_id : t('case.finished')}
      />

      {/* Bottom Navigation */}
      <div className="flex justify-between pt-4 border-t">
        {prevCase ? (
          <Link href={`/cases/${prevCase.case_id}`}>
            <Button variant="outline">
              <ChevronLeft className="mr-2 h-4 w-4" />
              {prevCase.case_id}
            </Button>
          </Link>
        ) : (
          <div />
        )}

        <Link href="/">
          <Button variant="ghost">
            <Home className="mr-2 h-4 w-4" />
            {t('case.home')}
          </Button>
        </Link>

        {nextCase ? (
          <Link href={`/cases/${nextCase.case_id}`}>
            <Button>
              {nextCase.case_id}
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        ) : (
          <Link href="/">
            <Button>
              {t('case.finished')}
              <Home className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
