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
import { REQUIRED_MODEL_IDS, JUDGE_MODEL_IDS, DEFAULT_JUDGE_ID, getModelDisplayName, getJudgeDisplayName } from '@/lib/types';
import type { JudgeEvaluation } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import { JudgeReviewForm } from '@/components/JudgeReviewForm';
import type { JudgeReviewFormData, JudgeCorrectValue } from '@/components/JudgeReviewForm';
import type { Case } from '@/lib/types';
import type { Medication, ImagingFinding, SecondaryDiagnosis } from '@/lib/types';
import {
  ChevronLeft, ChevronRight, Home, User, Brain,
  Check, X, Save, Loader2, Scale, ArrowRight,
  Activity, Pill, Scan, Stethoscope, FileText,
} from 'lucide-react';

interface JudgeReviewClientProps {
  caseItem: Case;
  allReviewableCases: Case[];
  currentIndex: number;
}

// Per-model-per-judge form state
interface ModelFormState {
  judge_correct: JudgeCorrectValue | null;
  judge_reasoning_quality: number;
  comment: string;
  dirty: boolean;
}

// Composite key for form states and existing reviews
function formKey(modelId: string, judgeId: string) {
  return `${modelId}__${judgeId}`;
}

export function JudgeReviewClient({ caseItem, allReviewableCases, currentIndex }: JudgeReviewClientProps) {
  const { t, language } = useI18n();
  const [reviewerName, setReviewerNameState] = useState('');
  const [doctorReviews, setDoctorReviews] = useState<Map<string, DoctorReviewResponse>>(new Map());
  // Keyed by modelId__judgeId
  const [existingJudgeReviews, setExistingJudgeReviews] = useState<Map<string, JudgeReviewResponse>>(new Map());
  const [formStates, setFormStates] = useState<Map<string, ModelFormState>>(new Map());
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingAll, setSavingAll] = useState(false);
  const [allSaved, setAllSaved] = useState(false);
  const [selectedJudge, setSelectedJudge] = useState<string>(DEFAULT_JUDGE_ID);
  const initializedRef = useRef(false);

  const prevCase = currentIndex > 0 ? allReviewableCases[currentIndex - 1] : null;
  const nextCase = currentIndex < allReviewableCases.length - 1 ? allReviewableCases[currentIndex + 1] : null;

  // Available judges for this case (judges that have evaluations for at least one model)
  const availableJudges = useMemo(() => {
    const judges = new Set<string>();
    for (const pred of Object.values(caseItem.predictions)) {
      if (pred.judge_evaluations) {
        for (const judgeId of Object.keys(pred.judge_evaluations)) {
          judges.add(judgeId);
        }
      }
    }
    // Return in the order defined by JUDGE_MODEL_IDS, then any extras
    const ordered: string[] = [];
    for (const jid of JUDGE_MODEL_IDS) {
      if (judges.has(jid)) ordered.push(jid);
    }
    for (const jid of judges) {
      if (!ordered.includes(jid)) ordered.push(jid);
    }
    return ordered;
  }, [caseItem.predictions]);

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
        // Fetch doctor's blind reviews and ALL existing judge reviews (no judge_model filter)
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

        // Map existing judge reviews by modelId__judgeId
        const jrMap = new Map<string, JudgeReviewResponse>();
        for (const jr of judgeReviews) {
          const jModel = jr.judge_model || DEFAULT_JUDGE_ID;
          jrMap.set(formKey(jr.model_id, jModel), jr);
        }
        setExistingJudgeReviews(jrMap);

        // Initialize form states for ALL judge × model combos
        const states = new Map<string, ModelFormState>();
        for (const modelId of REQUIRED_MODEL_IDS) {
          if (!caseItem.predictions[modelId] || !drMap.has(modelId)) continue;
          const pred = caseItem.predictions[modelId];
          const judgeIds = pred.judge_evaluations ? Object.keys(pred.judge_evaluations) : [DEFAULT_JUDGE_ID];

          for (const judgeId of judgeIds) {
            const key = formKey(modelId, judgeId);
            const existing = jrMap.get(key);
            states.set(key, {
              judge_correct: (existing?.judge_correct as JudgeCorrectValue) ?? null,
              judge_reasoning_quality: existing?.judge_reasoning_quality ?? 5,
              comment: existing?.comment ?? '',
              dirty: false,
            });
          }
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
    const key = formKey(modelId, selectedJudge);
    setFormStates(prev => {
      const next = new Map(prev);
      next.set(key, {
        judge_correct: data.judge_correct,
        judge_reasoning_quality: data.judge_reasoning_quality,
        comment: data.comment,
        dirty: true,
      });
      return next;
    });
    setAllSaved(false);
  }, [selectedJudge]);

  const handleSaveAll = async () => {
    if (!reviewerName) return;

    const inputs = [];
    for (const modelId of reviewedModelIds) {
      const key = formKey(modelId, selectedJudge);
      const form = formStates.get(key);
      if (!form || !form.judge_correct) continue;

      const doctorReview = doctorReviews.get(modelId);
      const prediction = caseItem.predictions[modelId];
      const judge = prediction?.judge_evaluations?.[selectedJudge] ?? prediction?.judge_evaluation;

      inputs.push({
        case_id: caseItem.case_id,
        model_id: modelId,
        reviewer_name: reviewerName,
        judge_model: selectedJudge,
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
        const jModel = jr.judge_model || selectedJudge;
        jrMap.set(formKey(jr.model_id, jModel), jr);
      }
      setExistingJudgeReviews(jrMap);

      // Mark current judge's forms as not dirty
      setFormStates(prev => {
        const next = new Map(prev);
        for (const modelId of reviewedModelIds) {
          const key = formKey(modelId, selectedJudge);
          const v = next.get(key);
          if (v) next.set(key, { ...v, dirty: false });
        }
        return next;
      });

      // Check if there's another judge that needs review (using updated jrMap)
      let nextJudge: string | null = null;
      if (availableJudges.length > 1) {
        const currentIdx = availableJudges.indexOf(selectedJudge);
        for (let i = 1; i < availableJudges.length; i++) {
          const idx = (currentIdx + i) % availableJudges.length;
          const judgeId = availableJudges[idx];
          for (const modelId of reviewedModelIds) {
            if (!jrMap.has(formKey(modelId, judgeId))) {
              nextJudge = judgeId;
              break;
            }
          }
          if (nextJudge) break;
        }
      }

      if (nextJudge) {
        // Switch to next unsaved judge
        setSelectedJudge(nextJudge);
        setAllSaved(false);
      } else {
        // All judges done — show next case CTA (persistent, no timeout)
        setAllSaved(true);
      }
    } catch (error) {
      console.error('Failed to save judge reviews:', error);
    } finally {
      setSavingAll(false);
    }
  };

  // Count how many forms have been filled for the current judge
  const filledCount = useMemo(() => {
    let count = 0;
    for (const modelId of reviewedModelIds) {
      const form = formStates.get(formKey(modelId, selectedJudge));
      if (form?.judge_correct) count++;
    }
    return count;
  }, [formStates, selectedJudge, reviewedModelIds]);

  // Next unsaved judge (excluding current one, searched in order after current)
  const nextUnsavedJudge = useMemo(() => {
    if (availableJudges.length <= 1) return null;
    const currentIdx = availableJudges.indexOf(selectedJudge);
    for (let i = 1; i < availableJudges.length; i++) {
      const idx = (currentIdx + i) % availableJudges.length;
      const judgeId = availableJudges[idx];
      for (const modelId of reviewedModelIds) {
        const key = formKey(modelId, judgeId);
        const existing = existingJudgeReviews.get(key);
        const form = formStates.get(key);
        if (!existing || form?.dirty) return judgeId;
      }
    }
    return null;
  }, [availableJudges, selectedJudge, reviewedModelIds, existingJudgeReviews, formStates]);

  // Are ALL judges × ALL models fully saved?
  const allJudgesDone = useMemo(() => {
    if (availableJudges.length === 0 || reviewedModelIds.length === 0) return false;
    for (const judgeId of availableJudges) {
      for (const modelId of reviewedModelIds) {
        const key = formKey(modelId, judgeId);
        const existing = existingJudgeReviews.get(key);
        const form = formStates.get(key);
        if (!existing || form?.dirty) return false;
      }
    }
    return true;
  }, [availableJudges, reviewedModelIds, existingJudgeReviews, formStates]);

  // Get judge evaluation for a model
  const getJudge = useCallback((modelId: string): JudgeEvaluation | null => {
    const pred = caseItem.predictions[modelId];
    if (!pred) return null;
    return pred.judge_evaluations?.[selectedJudge] ?? (selectedJudge === DEFAULT_JUDGE_ID ? pred.judge_evaluation : null);
  }, [caseItem.predictions, selectedJudge]);

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

      {/* Patient + Clinical Context + Ground Truth */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Stethoscope className="h-4 w-4" />
            {t('clinical.patientOverview')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
            {caseItem.patient.karnofsky != null && (
              <Badge variant="secondary">{t('clinical.karnofsky')} {caseItem.patient.karnofsky}%</Badge>
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
                <span><span className="font-medium text-gray-600 dark:text-gray-400">{t('clinical.klarzellig')}:</span> {caseItem.diagnosis.klarzellig ? t('judgeReview.yes') : t('judgeReview.no')}</span>
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
              {/* Nebendiagnosen */}
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

              {/* Medikation */}
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
            <span className="font-semibold text-green-800 dark:text-green-200 text-sm">{t('judgeReview.groundTruth')}: </span>
            <span className="text-sm">{caseItem.ground_truth.therapy}</span>
          </div>
        </CardContent>
      </Card>

      {/* Judge Selector */}
      {availableJudges.length > 1 && (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-medium text-muted-foreground">{t('judgeReview.selectJudge')}:</span>
          <div className="flex gap-2">
            {availableJudges.map(judgeId => {
              const isSelected = judgeId === selectedJudge;
              // Count how many models have been rated for this judge
              let ratedCount = 0;
              for (const modelId of reviewedModelIds) {
                const existing = existingJudgeReviews.get(formKey(modelId, judgeId));
                if (existing) ratedCount++;
              }
              return (
                <Button
                  key={judgeId}
                  variant={isSelected ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => { setSelectedJudge(judgeId); setAllSaved(false); }}
                  className={isSelected ? 'bg-purple-600 hover:bg-purple-700' : ''}
                >
                  <Scale className="mr-1.5 h-3.5 w-3.5" />
                  {getJudgeDisplayName(judgeId)}
                  {ratedCount > 0 && (
                    <Badge variant="secondary" className="ml-2 text-xs px-1.5 py-0">
                      {ratedCount}/{reviewedModelIds.length}
                    </Badge>
                  )}
                </Button>
              );
            })}
          </div>
        </div>
      )}

      {/* Progress */}
      <div className="flex items-center justify-between">
        <Badge variant="secondary">
          {filledCount}/{reviewedModelIds.length} {language === 'de' ? 'bewertet' : 'rated'}
        </Badge>
      </div>

      {/* Model Cards: Side-by-side Doctor vs Judge */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {reviewedModelIds.map(modelId => {
          const judge = getJudge(modelId);
          const doctorReview = doctorReviews.get(modelId);
          const key = formKey(modelId, selectedJudge);
          const form = formStates.get(key);
          const existingJR = existingJudgeReviews.get(key);
          const isSaved = !!existingJR && !form?.dirty;

          if (!judge) return null;
          const prediction = caseItem.predictions[modelId];

          return (
            <Card
              key={`${modelId}__${selectedJudge}`}
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
                {/* Model's predicted therapy */}
                {prediction?.pred_therapy && (
                  <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2">
                    <span className="font-semibold text-blue-800 dark:text-blue-200 text-xs">{t('model.therapy')} </span>
                    <span className="text-xs">{prediction.pred_therapy}</span>
                  </div>
                )}

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

                {/* Judge's reasoning — expandable */}
                <details className="text-xs group">
                  <summary className="font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors list-none flex items-center gap-1">
                    <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
                    {t('judgeReview.judgeReasoning')}
                  </summary>
                  <div className="mt-2 space-y-2 pl-4 border-l-2 border-purple-200 dark:border-purple-800">
                    {judge.correctness_reason && (
                      <p className="text-muted-foreground">{judge.correctness_reason}</p>
                    )}
                    {judge.reasoning_critique && (
                      <p className="text-muted-foreground italic">{judge.reasoning_critique}</p>
                    )}
                    {!judge.correctness_reason && !judge.reasoning_critique && judge.judge_reasoning && (
                      <p className="text-muted-foreground">{judge.judge_reasoning}</p>
                    )}
                  </div>
                </details>

                {/* Model's reasoning — expandable */}
                {prediction?.pred_reasoning && (
                  <details className="text-xs group">
                    <summary className="font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors list-none flex items-center gap-1">
                      <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
                      {t('model.modelReasoning')}
                    </summary>
                    <div className="mt-2 pl-4 border-l-2 border-blue-200 dark:border-blue-800">
                      <p className="text-muted-foreground">{prediction.pred_reasoning}</p>
                    </div>
                  </details>
                )}

                {/* Judge Review Form */}
                <JudgeReviewForm
                  key={`${modelId}__${selectedJudge}`}
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

      {/* Save All + Next Judge / Next Case CTA */}
      <div className={`flex ${allJudgesDone ? 'justify-between' : 'justify-center'} items-center gap-3 flex-wrap pt-4 border-t`}>
        {!allJudgesDone && (
          <Button
            onClick={handleSaveAll}
            size="lg"
            disabled={savingAll || filledCount === 0}
            className={nextUnsavedJudge ? 'w-full max-w-md bg-purple-600 hover:bg-purple-700' : 'w-full max-w-md'}
          >
            {savingAll ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('judgeReview.saving')}
              </>
            ) : nextUnsavedJudge ? (
              <>
                <Save className="mr-2 h-4 w-4" />
                {t('judgeReview.saveNextJudge')}: {getJudgeDisplayName(nextUnsavedJudge)}
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                {t('judgeReview.saveAll')}
              </>
            )}
          </Button>
        )}
        {allJudgesDone && (
          <div className="flex items-center gap-3 w-full justify-between">
            <Badge variant="secondary" className="text-sm px-3 py-1.5 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
              <Check className="mr-1.5 h-4 w-4" />
              {t('judgeReview.allSaved')} ({availableJudges.length} {language === 'de' ? 'Richter' : 'judges'})
            </Badge>
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
