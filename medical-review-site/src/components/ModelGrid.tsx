'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { DoctorReviewForm } from './DoctorReviewForm';
import { saveReviewsBatch } from '@/lib/storage';
import { getModelDisplayName } from '@/lib/types';
import type { DoctorReviewInput, DoctorReviewResponse } from '@/lib/storage';
import { useI18n } from '@/lib/i18n';
import type { Case, ModelPrediction } from '@/lib/types';
import { Check, X, Brain, Save, CheckCircle, Loader2, Scale, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface ModelGridProps {
  caseItem: Case;
  selectedModels: string[];
  reviewedModels?: Set<string>;
  onReviewSaved?: (modelId: string) => void;
  allReviewsDone?: boolean;
  nextCaseHref?: string;
  nextCaseLabel?: string;
}

export function ModelGrid({ caseItem, selectedModels, reviewedModels, onReviewSaved, allReviewsDone, nextCaseHref, nextCaseLabel }: ModelGridProps) {
  const { t } = useI18n();
  const [allSaved, setAllSaved] = useState(false);

  const modelsToShow = selectedModels.filter(m => caseItem.predictions[m]);

  const [savingAll, setSavingAll] = useState(false);

  const handleSaveAll = async () => {
    // Phase 1: Collect all form data via event
    const detail: { reviews: DoctorReviewInput[] } = { reviews: [] };
    window.dispatchEvent(new CustomEvent('collect-reviews', { detail }));

    if (detail.reviews.length === 0) return;

    // Phase 2: Batch save — single read-modify-write on server
    setSavingAll(true);
    try {
      const savedReviews = await saveReviewsBatch(detail.reviews);

      // Phase 3: Notify forms their data was saved
      window.dispatchEvent(new CustomEvent('save-all-done', {
        detail: { reviews: savedReviews },
      }));

      setAllSaved(true);
      setTimeout(() => setAllSaved(false), 2000);
    } catch (error) {
      console.error('Batch save failed:', error);
    } finally {
      setSavingAll(false);
    }
  };

  if (modelsToShow.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {t('models.noneSelected')}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className={`flex ${allReviewsDone ? 'justify-between' : 'justify-end'} items-center gap-3 flex-wrap`}>
        <Button onClick={handleSaveAll} variant={allSaved ? 'outline' : allReviewsDone ? 'outline' : 'default'} disabled={savingAll}>
          {savingAll ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          {allSaved ? t('review.allSaved') : savingAll ? t('home.loading') : t('review.saveAll')}
        </Button>
        {allReviewsDone && (
          <div className="flex items-center gap-2">
            <Link href={`/judge-review/${caseItem.case_id}`}>
              <Button className="bg-purple-600 hover:bg-purple-700 text-white">
                <Scale className="mr-2 h-4 w-4" />
                {t('judgeReview.reviewJudge')}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href={nextCaseHref ?? '/'}>
              <Button variant="outline">
                {nextCaseLabel ?? t('case.nextCase')}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {modelsToShow.map(modelId => (
          <ModelCard
            key={modelId}
            modelId={modelId}
            prediction={caseItem.predictions[modelId]}
            caseId={caseItem.case_id}
            isReviewed={reviewedModels?.has(modelId) ?? false}
            onReviewSaved={onReviewSaved}
          />
        ))}
      </div>
    </div>
  );
}

interface ModelCardProps {
  modelId: string;
  prediction: ModelPrediction;
  caseId: string;
  isReviewed?: boolean;
  onReviewSaved?: (modelId: string) => void;
}

function ModelCard({ modelId, prediction, caseId, isReviewed, onReviewSaved }: ModelCardProps) {
  const { t } = useI18n();
  const judge = prediction.judge_evaluation;
  const isCorrect = judge.is_correct;

  return (
    <Card className={`${isCorrect ? 'border-green-300' : 'border-red-300'} ${isReviewed ? 'opacity-70' : ''}`}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Brain className="h-4 w-4" />
            {getModelDisplayName(modelId)}
          </div>
          <div className="flex items-center gap-1.5">
            {isReviewed && (
              <Badge variant="secondary" className="text-xs flex items-center gap-1">
                <CheckCircle className="h-3 w-3 text-green-600" />
                {t('models.reviewed')}
              </Badge>
            )}
            {isCorrect
              ? <Check className="h-4 w-4 text-green-600" />
              : <X className="h-4 w-4 text-red-600" />
            }
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Prediction Summary */}
        <div className="space-y-2">
          <div className="flex flex-wrap gap-1">
            <Badge
              variant={prediction.pred_metastatic ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {prediction.pred_metastatic ? 'Metast.' : 'Non-Met.'}
            </Badge>
            {prediction.metastatic_correct
              ? <Check className="h-3 w-3 text-green-600" />
              : <X className="h-3 w-3 text-red-600" />
            }
            <Badge variant="outline" className="text-xs">
              {Math.round(prediction.pred_confidence * 100)}%
            </Badge>
          </div>

          {/* Therapy Preview */}
          <div className="text-sm">
            <span className="text-muted-foreground">{t('model.therapy')} </span>
            <span>{prediction.pred_therapy}</span>
          </div>
        </div>

        {/* Judge Scores - Compact */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('model.overall')}</span>
            <span className="font-medium">{(judge.overall_score * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('model.clinical')}</span>
            <span className="font-medium">{(judge.clinical_score * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('model.semantic')}</span>
            <span className="font-medium">{(judge.semantic_score * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('model.reasoning')}</span>
            <span className="font-medium">{(judge.reasoning_quality * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Expandable Details */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="details" className="border-b-0">
            <AccordionTrigger className="text-xs py-2">{t('model.showDetails')}</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="font-medium">{t('model.reason')} </span>
                  <span className="text-muted-foreground">{judge.correctness_reason}</span>
                </div>
                {prediction.pred_reasoning && (
                  <div>
                    <span className="font-medium">{t('model.modelReasoning')} </span>
                    <span className="text-muted-foreground">
                      {prediction.pred_reasoning}
                    </span>
                  </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Doctor Review Form */}
        <DoctorReviewForm caseId={caseId} modelId={modelId} compact onSave={() => onReviewSaved?.(modelId)} />
      </CardContent>
    </Card>
  );
}
