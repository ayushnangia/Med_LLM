'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  getReviewerName,
  getReviewsFromServer,
  saveJudgeReviewsBatch,
  getJudgeReviewsFromServer,
} from '@/lib/storage';
import type { DoctorReviewResponse, JudgeReviewResponse } from '@/lib/storage';
import { REQUIRED_MODEL_IDS, getModelDisplayName } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import { JudgeReviewForm } from '@/components/JudgeReviewForm';
import type { JudgeReviewFormData, JudgeCorrectValue } from '@/components/JudgeReviewForm';
import type { Case } from '@/lib/types';
import {
  ChevronLeft, ChevronRight, Home, User, Brain,
  Check, X, Save, Loader2, Scale, ArrowRight,
} from 'lucide-react';

interface JudgeReviewClientProps {
  caseItem: Case;
  allReviewableCases: Case[];
  currentIndex: number;
}

// Per-model form state
interface ModelFormState {
  judge_correct: JudgeCorrectValue | null;
  judge_reasoning_quality: number;
  comment: string;
  dirty: boolean;
}

export function JudgeReviewClient({ caseItem, allReviewableCases, currentIndex }: JudgeReviewClientProps) {
  const { t, language } = useI18n();
  const [reviewerName, setReviewerNameState] = useState('');
  const [doctorReviews, setDoctorReviews] = useState<Map<string, DoctorReviewResponse>>(new Map());
  const [existingJudgeReviews, setExistingJudgeReviews] = useState<Map<string, JudgeReviewResponse>>(new Map());
  const [formStates, setFormStates] = useState<Map<string, ModelFormState>>(new Map());
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingAll, setSavingAll] = useState(false);
  const [allSaved, setAllSaved] = useState(false);
  const initializedRef = useRef(false);

  const prevCase = currentIndex > 0 ? allReviewableCases[currentIndex - 1] : null;
  const nextCase = currentIndex < allReviewableCases.length - 1 ? allReviewableCases[currentIndex + 1] : null;

  // Models that have both a prediction and a doctor review
  const reviewedModelIds = useMemo(() => {
    return REQUIRED_MODEL_IDS.filter(
      m => caseItem.predictions[m] && doctorReviews.has(m)
    );
  }, [caseItem.predictions, doctorReviews]);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    setMounted(true);

    const name = getReviewerName();
    setReviewerNameState(name);

    const init = async () => {
      if (!name) {
        setLoading(false);
        return;
      }

      try {
        // Fetch doctor's blind reviews and existing judge reviews in parallel
        const [reviews, judgeReviews] = await Promise.all([
          getReviewsFromServer({ caseId: caseItem.case_id, doctor: name }),
          getJudgeReviewsFromServer({ caseId: caseItem.case_id, doctor: name }),
        ]);

        // Map doctor reviews by model_id
        const drMap = new Map<string, DoctorReviewResponse>();
        for (const r of reviews) {
          drMap.set(r.model_id, r);
        }
        setDoctorReviews(drMap);

        // Map existing judge reviews by model_id
        const jrMap = new Map<string, JudgeReviewResponse>();
        for (const jr of judgeReviews) {
          jrMap.set(jr.model_id, jr);
        }
        setExistingJudgeReviews(jrMap);

        // Initialize form states from existing judge reviews
        const states = new Map<string, ModelFormState>();
        for (const modelId of REQUIRED_MODEL_IDS) {
          if (!caseItem.predictions[modelId] || !drMap.has(modelId)) continue;
          const existing = jrMap.get(modelId);
          states.set(modelId, {
            judge_correct: (existing?.judge_correct as JudgeCorrectValue) ?? null,
            judge_reasoning_quality: existing?.judge_reasoning_quality ?? 5,
            comment: existing?.comment ?? '',
            dirty: false,
          });
        }
        setFormStates(states);
      } catch (error) {
        console.error('Failed to load reviews:', error);
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [caseItem.case_id]);

  const handleFormChange = useCallback((modelId: string, data: JudgeReviewFormData) => {
    setFormStates(prev => {
      const next = new Map(prev);
      next.set(modelId, {
        judge_correct: data.judge_correct,
        judge_reasoning_quality: data.judge_reasoning_quality,
        comment: data.comment,
        dirty: true,
      });
      return next;
    });
    setAllSaved(false);
  }, []);

  const handleSaveAll = async () => {
    if (!reviewerName) return;

    const inputs = [];
    for (const modelId of reviewedModelIds) {
      const form = formStates.get(modelId);
      if (!form || !form.judge_correct) continue;

      const doctorReview = doctorReviews.get(modelId);
      const prediction = caseItem.predictions[modelId];
      const judge = prediction?.judge_evaluation;

      inputs.push({
        case_id: caseItem.case_id,
        model_id: modelId,
        reviewer_name: reviewerName,
        judge_correct: form.judge_correct,
        judge_reasoning_quality: form.judge_reasoning_quality,
        comment: form.comment || null,
        // Snapshots
        doctor_acceptable: doctorReview?.therapy_acceptable_ra ?? null,
        doctor_quality: doctorReview?.prediction_quality ?? null,
        judge_is_correct: judge?.is_correct ?? null,
        judge_overall_score: judge?.overall_score ?? null,
      });
    }

    if (inputs.length === 0) return;

    setSavingAll(true);
    try {
      const saved = await saveJudgeReviewsBatch(inputs);

      // Update existing judge reviews map
      const jrMap = new Map(existingJudgeReviews);
      for (const jr of saved) {
        jrMap.set(jr.model_id, jr);
      }
      setExistingJudgeReviews(jrMap);

      // Mark all as not dirty
      setFormStates(prev => {
        const next = new Map(prev);
        for (const [k, v] of next) {
          next.set(k, { ...v, dirty: false });
        }
        return next;
      });

      setAllSaved(true);
      setTimeout(() => setAllSaved(false), 2000);
    } catch (error) {
      console.error('Failed to save judge reviews:', error);
    } finally {
      setSavingAll(false);
    }
  };

  // Count how many forms have been filled (judge_correct selected)
  const filledCount = useMemo(() => {
    let count = 0;
    for (const [, form] of formStates) {
      if (form.judge_correct) count++;
    }
    return count;
  }, [formStates]);

  if (!mounted || loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted-foreground">{t('case.loadingCase')}</div>
      </div>
    );
  }

  if (reviewedModelIds.length === 0) {
    return (
      <div className="space-y-4 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <Link href="/cases">
            <Button variant="ghost" size="sm">
              <ChevronLeft className="h-4 w-4 mr-1" />
              {t('judgeReview.backToCases')}
            </Button>
          </Link>
        </div>
        <div className="text-center py-12 text-muted-foreground">
          {t('judgeReview.noReviews')}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Link href="/cases">
            <Button variant="ghost" size="sm">
              <ChevronLeft className="h-4 w-4 mr-1" />
              {t('judgeReview.backToCases')}
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-purple-600" />
            <span className="font-semibold">{t('judgeReview.title')}: {caseItem.case_id}</span>
          </div>
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{reviewerName}</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-2">
          {prevCase ? (
            <Link href={`/judge-review/${prevCase.case_id}`}>
              <Button variant="outline" size="sm">
                <ChevronLeft className="h-4 w-4 mr-1" />
                {t('judgeReview.prev')}
              </Button>
            </Link>
          ) : (
            <Button variant="outline" size="sm" disabled>
              <ChevronLeft className="h-4 w-4 mr-1" />
              {t('judgeReview.prev')}
            </Button>
          )}

          <Badge variant="secondary" className="px-3">
            {t('judgeReview.caseOf', { current: currentIndex + 1, total: allReviewableCases.length })}
          </Badge>

          {nextCase ? (
            <Link href={`/judge-review/${nextCase.case_id}`}>
              <Button variant="outline" size="sm">
                {t('judgeReview.next')}
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          ) : (
            <Button variant="outline" size="sm" disabled>
              {t('judgeReview.next')}
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </div>

      {/* Patient + Ground Truth summary */}
      <Card>
        <CardContent className="py-4">
          <div className="space-y-3">
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
              <Badge variant={caseItem.ground_truth.metastatic ? 'destructive' : 'secondary'}>
                {caseItem.ground_truth.metastatic ? t('case.metastatic') : t('case.nonMetastatic')}
              </Badge>
            </div>
            <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg px-3 py-2">
              <span className="font-semibold text-green-800 dark:text-green-200 text-sm">{t('judgeReview.groundTruth')}: </span>
              <span className="text-sm">{caseItem.ground_truth.therapy}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress */}
      <div className="flex items-center justify-between">
        <Badge variant="secondary">
          {filledCount}/{reviewedModelIds.length} {language === 'de' ? 'bewertet' : 'rated'}
        </Badge>
      </div>

      {/* Model Cards: Side-by-side Doctor vs Judge */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {reviewedModelIds.map(modelId => {
          const prediction = caseItem.predictions[modelId];
          const judge = prediction.judge_evaluation;
          const doctorReview = doctorReviews.get(modelId);
          const form = formStates.get(modelId);
          const existingJR = existingJudgeReviews.get(modelId);
          const isSaved = !!existingJR && !form?.dirty;

          return (
            <Card
              key={modelId}
              className={`${judge.is_correct ? 'border-green-300' : 'border-red-300'}`}
            >
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    {getModelDisplayName(modelId)}
                  </div>
                  {judge.is_correct
                    ? <Check className="h-4 w-4 text-green-600" />
                    : <X className="h-4 w-4 text-red-600" />
                  }
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Two-column comparison */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Left: Doctor's Review */}
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wide">
                      {t('judgeReview.yourReview')}
                    </span>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.acceptable')}</span>
                        <span className="font-medium">
                          {doctorReview?.therapy_acceptable_ra === true
                            ? t('judgeReview.yes')
                            : doctorReview?.therapy_acceptable_ra === false
                              ? t('judgeReview.no')
                              : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.exactMatch')}</span>
                        <span className="font-medium">
                          {doctorReview?.recommendation_exact_match != null
                            ? `${doctorReview.recommendation_exact_match}%`
                            : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.patientOriented')}</span>
                        <span className="font-medium">
                          {doctorReview?.recommendation_patient_oriented != null
                            ? `${doctorReview.recommendation_patient_oriented}%`
                            : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.quality')}</span>
                        <span className="font-medium">
                          {doctorReview?.prediction_quality != null
                            ? `${doctorReview.prediction_quality}/9`
                            : '—'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Judge Evaluation */}
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">
                      {t('judgeReview.judgeEval')}
                    </span>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.correct')}</span>
                        <span className={`font-medium ${judge.is_correct ? 'text-green-600' : 'text-red-600'}`}>
                          {judge.is_correct ? t('judgeReview.yes') : t('judgeReview.no')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.overall')}</span>
                        <span className="font-medium">{(judge.overall_score * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.clinical')}</span>
                        <span className="font-medium">{(judge.clinical_score * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.semantic')}</span>
                        <span className="font-medium">{(judge.semantic_score * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">{t('judgeReview.reasoning')}</span>
                        <span className="font-medium">{(judge.reasoning_quality * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Judge's reasoning text */}
                <div className="text-xs space-y-1">
                  <span className="font-medium text-muted-foreground">{t('judgeReview.judgeReasoning')}</span>
                  <p className="text-muted-foreground line-clamp-4">
                    {judge.correctness_reason || judge.judge_reasoning}
                  </p>
                </div>

                {/* Judge Review Form */}
                <JudgeReviewForm
                  initialData={form ? {
                    judge_correct: form.judge_correct,
                    judge_reasoning_quality: form.judge_reasoning_quality,
                    comment: form.comment,
                  } : undefined}
                  saved={isSaved}
                  onChange={(data) => handleFormChange(modelId, data)}
                />
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Save All + Next Case CTA */}
      <div className={`flex ${allSaved ? 'justify-between' : 'justify-center'} items-center gap-3 flex-wrap pt-4 border-t`}>
        <Button
          onClick={handleSaveAll}
          variant={allSaved ? 'outline' : 'default'}
          size="lg"
          disabled={savingAll || filledCount === 0}
          className={allSaved ? '' : 'w-full max-w-md'}
        >
          {savingAll ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('judgeReview.saving')}
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              {allSaved ? t('judgeReview.allSaved') : t('judgeReview.saveAll')}
            </>
          )}
        </Button>
        {allSaved && (
          <div className="flex items-center gap-2">
            {nextCase ? (
              <Link href={`/cases/${nextCase.case_id}`}>
                <Button className="bg-purple-600 hover:bg-purple-700 text-white">
                  {t('case.nextCase')}: {nextCase.case_id}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            ) : (
              <Link href="/">
                <Button className="bg-purple-600 hover:bg-purple-700 text-white">
                  {t('case.finished')}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Bottom Navigation */}
      <div className="flex justify-between pt-2">
        <Link href={`/cases/${caseItem.case_id}`}>
          <Button variant="outline">
            <ChevronLeft className="mr-2 h-4 w-4" />
            {caseItem.case_id}
          </Button>
        </Link>

        <Link href="/cases">
          <Button variant="ghost">
            <Home className="mr-2 h-4 w-4" />
            {t('judgeReview.backToCases')}
          </Button>
        </Link>

        {nextCase ? (
          <Link href={`/cases/${nextCase.case_id}`}>
            <Button variant="outline">
              {nextCase.case_id}
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        ) : (
          <Link href="/">
            <Button variant="outline">
              {t('case.finished')}
              <Home className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
