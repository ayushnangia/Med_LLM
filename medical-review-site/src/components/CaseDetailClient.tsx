'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { ModelSelector } from '@/components/ModelSelector';
import { ModelGrid } from '@/components/ModelGrid';
import { getReviewerName, getReviewsFromServer, setSelectedModels } from '@/lib/storage';
import { REQUIRED_MODEL_IDS } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import {
  ChevronLeft, ChevronRight, Home, User, Activity, ClipboardCheck, CheckCircle,
  Stethoscope, FileText, Pill, Scan,
} from 'lucide-react';
import type { Case, Medication, ImagingFinding, SecondaryDiagnosis } from '@/lib/types';
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

      {/* Patient + Clinical Context + Ground Truth (integrated card) */}
      <Card>
        <CardContent className="space-y-4 pt-4">
          {/* Row 1: Patient basics + badges */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className="font-semibold text-lg">{caseItem.patient.name}</span>
            {caseItem.patient.age != null && (
              <Badge variant="outline" className="font-normal">
                {caseItem.patient.age} {language === 'de' ? 'Jahre' : 'years'}
              </Badge>
            )}
            {caseItem.patient.ecog != null && (
              <Badge variant="secondary">ECOG {caseItem.patient.ecog}</Badge>
            )}
            {(caseItem.patient.karnofsky != null || caseItem.patient.karnofsky_from_labor) && (
              <Badge variant="secondary">
                {t('clinical.karnofsky')} {caseItem.patient.karnofsky ?? caseItem.patient.karnofsky_from_labor}%
              </Badge>
            )}
            <Badge variant={caseItem.ground_truth.metastatic ? 'destructive' : 'secondary'}>
              {caseItem.ground_truth.metastatic ? t('case.metastatic') : t('case.nonMetastatic')}
            </Badge>
            {caseItem.patient.comorbidity && caseItem.patient.comorbidity !== 'unknown' && (
              <Badge variant="outline">{t('clinical.comorbidity')}: {caseItem.patient.comorbidity}</Badge>
            )}
            {caseItem.patient.life_expectancy && caseItem.patient.life_expectancy !== 'unknown' && caseItem.patient.life_expectancy !== 'null' && (
              <Badge variant="outline">{t('clinical.lifeExpectancy')}: {caseItem.patient.life_expectancy}</Badge>
            )}
          </div>

          {/* Row 2: Diagnosis details */}
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg px-3 py-2 space-y-1">
            <div className="text-sm">
              <span className="font-semibold text-gray-700 dark:text-gray-300">{t('clinical.diagnosis')}: </span>
              <span>{caseItem.diagnosis.diagnose_kurz}</span>
            </div>
            {caseItem.diagnosis.stadium && (
              <div className="text-sm">
                <span className="font-semibold text-gray-700 dark:text-gray-300">{t('clinical.stadium')}: </span>
                <span>{caseItem.diagnosis.stadium}</span>
              </div>
            )}
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm mt-1">
              {caseItem.diagnosis.histologie_subtyp && (
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.histologie')}:</span> {caseItem.diagnosis.histologie_subtyp}</span>
              )}
              {caseItem.diagnosis.klarzellig != null && (
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.klarzellig')}:</span> {caseItem.diagnosis.klarzellig ? (language === 'de' ? 'Ja' : 'Yes') : (language === 'de' ? 'Nein' : 'No')}</span>
              )}
              {caseItem.diagnosis.tnm_cM && (
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.tnm')}:</span> {caseItem.diagnosis.tnm_cM}</span>
              )}
              {caseItem.diagnosis.tnm_string && (
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.tnm')}:</span> {caseItem.diagnosis.tnm_string}</span>
              )}
              {caseItem.diagnosis.grading && (
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.grading')}:</span> {caseItem.diagnosis.grading}</span>
              )}
              {caseItem.diagnosis.imdc_risiko && (
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.imdc')}:</span> {caseItem.diagnosis.imdc_risiko}</span>
              )}
            </div>
          </div>

          {/* Row 3: Anamnese */}
          {caseItem.clinical_context?.anamnese_freitext && (
            <div className="text-sm">
              <div className="flex items-center gap-1.5 font-semibold text-gray-700 dark:text-gray-300 mb-1">
                <FileText className="h-3.5 w-3.5" />
                {t('clinical.anamnese')}
              </div>
              <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{caseItem.clinical_context.anamnese_freitext}</p>
            </div>
          )}

          {/* Row 4: Nebendiagnosen + Medikation side by side */}
          {(caseItem.clinical_context?.nebendiagnosen?.length || caseItem.clinical_context?.medikation?.length) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {caseItem.clinical_context?.nebendiagnosen && caseItem.clinical_context.nebendiagnosen.length > 0 && (
                <div className="bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-800 rounded-lg px-3 py-2">
                  <div className="flex items-center gap-1.5 font-semibold text-orange-800 dark:text-orange-200 text-sm mb-1">
                    <Activity className="h-3.5 w-3.5" />
                    {t('clinical.nebendiagnosen')}
                  </div>
                  <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-0.5">
                    {caseItem.clinical_context.nebendiagnosen.map((nd: SecondaryDiagnosis, i: number) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-orange-400 mt-1">&#8226;</span>
                        <span>{typeof nd === 'string' ? nd : nd.diagnose}{typeof nd !== 'string' && nd.details ? ` (${nd.details})` : ''}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {caseItem.clinical_context?.medikation && caseItem.clinical_context.medikation.length > 0 && (
                <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2">
                  <div className="flex items-center gap-1.5 font-semibold text-blue-800 dark:text-blue-200 text-sm mb-1">
                    <Pill className="h-3.5 w-3.5" />
                    {t('clinical.medikation')}
                  </div>
                  <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-0.5">
                    {caseItem.clinical_context.medikation.map((med: Medication, i: number) => {
                      const name = med.wirkstoff_oder_klasse || med.wirkstoff || '';
                      const detail = med.details || med.hinweis || '';
                      const dose = med.dosierung || '';
                      return (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-blue-400 mt-1">&#8226;</span>
                          <span>
                            {name}
                            {dose ? ` ${dose}` : ''}
                            {detail ? ` (${detail})` : ''}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Row 5: Bildgebung (Imaging) */}
          {caseItem.clinical_context?.bildgebung && caseItem.clinical_context.bildgebung.length > 0 && (
            <div className="bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800 rounded-lg px-3 py-2">
              <div className="flex items-center gap-1.5 font-semibold text-purple-800 dark:text-purple-200 text-sm mb-1">
                <Scan className="h-3.5 w-3.5" />
                {t('clinical.bildgebung')}
              </div>
              <div className="space-y-2">
                {caseItem.clinical_context.bildgebung.map((img: ImagingFinding, i: number) => (
                  <div key={i} className="text-sm">
                    <div className="flex flex-wrap gap-2 items-center mb-0.5">
                      <Badge variant="outline" className="text-xs">{img.modalitaet}</Badge>
                      <span className="font-medium text-gray-700 dark:text-gray-300">{img.region}</span>
                      {img.datum && <span className="text-xs text-muted-foreground">{img.datum}</span>}
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{img.befund_kurz}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Row 6: Prior therapies */}
          {caseItem.clinical_context?.therapien_und_eingriffe && caseItem.clinical_context.therapien_und_eingriffe.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
              <div className="flex items-center gap-1.5 font-semibold text-amber-800 dark:text-amber-200 text-sm mb-1">
                {t('clinical.priorTherapies')}
              </div>
              <div className="space-y-1 text-sm">
                {caseItem.clinical_context.therapien_und_eingriffe.map((th, i) => (
                  <div key={i} className="flex flex-wrap gap-2 items-center">
                    {th.linie != null && <Badge variant="outline" className="text-xs">{th.linie}. Linie</Badge>}
                    <span className="font-medium">{th.typ}</span>
                    {(th.beschreibung || th.regime) && <span className="text-gray-600 dark:text-gray-400">{th.beschreibung || th.regime}</span>}
                    {th.status && <Badge variant="secondary" className="text-xs">{th.status}</Badge>}
                    {(th.datum || th.datum_start) && <span className="text-xs text-muted-foreground">{th.datum || th.datum_start}{th.datum_ende ? ` – ${th.datum_ende}` : ''}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ground Truth Therapy */}
          <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg px-3 py-2">
            <span className="font-semibold text-green-800 dark:text-green-200 text-sm">{t('case.groundTruth')}: </span>
            <span className="text-sm">{caseItem.ground_truth.therapy}</span>
          </div>
        </CardContent>
      </Card>

      {/* Model Selector */}
      <ModelSelector
        availableModels={availableModels}
        selectedModels={selectedModels}
        onChange={handleModelSelectionChange}
        reviewedModels={reviewedModels}
      />

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
