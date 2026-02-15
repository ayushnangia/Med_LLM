'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import {
  saveReviewToServer,
  getReviewFromServer,
  getReviewerName,
  DoctorReviewInput,
  DoctorReviewResponse,
} from '@/lib/storage';
import { useI18n } from '@/lib/i18n';
import { Check, Save, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DoctorReviewFormProps {
  caseId: string;
  modelId: string;
  compact?: boolean;
  onSave?: (review: DoctorReviewInput) => void;
}

export function DoctorReviewForm({
  caseId,
  modelId,
  compact = false,
  onSave,
}: DoctorReviewFormProps) {
  const { t } = useI18n();
  const [existingReview, setExistingReview] = useState<DoctorReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Local state for user edits
  const [acceptable, setAcceptable] = useState<boolean | null>(null);
  const [exactMatch, setExactMatch] = useState(50);
  const [patientOriented, setPatientOriented] = useState(50);
  const [quality, setQuality] = useState(5);
  const [hasChanges, setHasChanges] = useState(false);

  const reviewerName = getReviewerName();

  // Load existing review from server
  const loadExistingReview = useCallback(async () => {
    if (!reviewerName) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const review = await getReviewFromServer(caseId, modelId, reviewerName);
      setExistingReview(review);

      // Initialize form values from existing review
      if (review) {
        setAcceptable(review.therapy_acceptable_ra);
        setExactMatch(review.recommendation_exact_match ?? 50);
        setPatientOriented(review.recommendation_patient_oriented ?? 50);
        setQuality(review.prediction_quality ?? 5);
      } else {
        // Reset to defaults
        setAcceptable(null);
        setExactMatch(50);
        setPatientOriented(50);
        setQuality(5);
      }
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to load review:', error);
    } finally {
      setLoading(false);
    }
  }, [caseId, modelId, reviewerName]);

  useEffect(() => {
    loadExistingReview();
  }, [loadExistingReview]);

  const updateField = (field: 'acceptable' | 'exactMatch' | 'patientOriented' | 'quality', value: boolean | number | null) => {
    switch (field) {
      case 'acceptable':
        setAcceptable(value as boolean | null);
        break;
      case 'exactMatch':
        setExactMatch(value as number);
        break;
      case 'patientOriented':
        setPatientOriented(value as number);
        break;
      case 'quality':
        setQuality(value as number);
        break;
    }
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!reviewerName) return;

    setSaving(true);
    try {
      const review: DoctorReviewInput = {
        case_id: caseId,
        model_id: modelId,
        reviewer_name: reviewerName,
        therapy_acceptable_ra: acceptable,
        recommendation_exact_match: exactMatch,
        recommendation_patient_oriented: patientOriented,
        prediction_quality: quality,
      };

      const savedReview = await saveReviewToServer(review);
      setExistingReview(savedReview);
      setHasChanges(false);
      onSave?.(review);
    } catch (error) {
      console.error('Failed to save review:', error);
    } finally {
      setSaving(false);
    }
  };

  // Phase 1: Respond to "collect" event by providing current review data
  useEffect(() => {
    const handleCollect = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (!reviewerName) return;
      // Always provide current form state — the parent decides whether to save
      detail.reviews.push({
        case_id: caseId,
        model_id: modelId,
        reviewer_name: reviewerName,
        therapy_acceptable_ra: acceptable,
        recommendation_exact_match: exactMatch,
        recommendation_patient_oriented: patientOriented,
        prediction_quality: quality,
      });
    };

    window.addEventListener('collect-reviews', handleCollect);
    return () => window.removeEventListener('collect-reviews', handleCollect);
  }, [reviewerName, acceptable, exactMatch, patientOriented, quality, caseId, modelId]);

  // Phase 2: Respond to "save-all-done" event to update local state
  useEffect(() => {
    const handleSaveDone = (e: Event) => {
      const savedReviews = (e as CustomEvent).detail.reviews as DoctorReviewResponse[];
      const mine = savedReviews.find(
        r => r.case_id === caseId && r.model_id === modelId
      );
      if (mine) {
        setExistingReview(mine);
        setHasChanges(false);
        onSave?.({
          case_id: mine.case_id,
          model_id: mine.model_id,
          reviewer_name: mine.reviewer_name,
          therapy_acceptable_ra: mine.therapy_acceptable_ra,
          recommendation_exact_match: mine.recommendation_exact_match,
          recommendation_patient_oriented: mine.recommendation_patient_oriented,
          prediction_quality: mine.prediction_quality,
        });
      }
    };

    window.addEventListener('save-all-done', handleSaveDone);
    return () => window.removeEventListener('save-all-done', handleSaveDone);
  }, [caseId, modelId, onSave]);

  const saved = existingReview !== null && !hasChanges;

  if (loading) {
    return (
      <div className={cn(
        'p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800',
        'flex items-center justify-center'
      )}>
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">{t('review.loading')}</span>
      </div>
    );
  }

  return (
    <div className={cn(
      'p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800',
      compact ? 'space-y-3' : 'space-y-4'
    )}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-blue-800 dark:text-blue-200">
          {t('review.yourReview')}
        </span>
        {saved && (
          <span className="text-xs text-green-600 flex items-center gap-1">
            <Check className="h-3 w-3" /> {t('review.saved')}
          </span>
        )}
      </div>

      {/* Acceptable Yes/No */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium">{t('review.acceptable')}</label>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={acceptable === true ? 'default' : 'outline'}
            onClick={() => updateField('acceptable', true)}
            className="flex-1"
          >
            {t('review.yes')}
          </Button>
          <Button
            size="sm"
            variant={acceptable === false ? 'destructive' : 'outline'}
            onClick={() => updateField('acceptable', false)}
            className="flex-1"
          >
            {t('review.no')}
          </Button>
        </div>
      </div>

      {/* Exact Match Slider */}
      <Slider
        label={t('review.exactMatch')}
        min={0}
        max={100}
        step={5}
        value={exactMatch}
        onChange={(e) => updateField('exactMatch', Number(e.target.value))}
      />

      {/* Patient-Oriented Slider */}
      <Slider
        label={t('review.patientOriented')}
        min={0}
        max={100}
        step={5}
        value={patientOriented}
        onChange={(e) => updateField('patientOriented', Number(e.target.value))}
      />

      {/* Quality Score */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">{t('review.quality')}</label>
          <span className="text-sm font-medium tabular-nums">{quality}/9</span>
        </div>
        <div className="flex gap-1">
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
            <button
              key={n}
              onClick={() => updateField('quality', n)}
              className={cn(
                'flex-1 h-8 text-xs font-medium rounded transition-colors',
                quality === n
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <Button
        onClick={handleSave}
        disabled={(!hasChanges && saved) || saving}
        className="w-full"
        size={compact ? 'sm' : 'default'}
      >
        {saving ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {t('home.loading')}
          </>
        ) : (
          <>
            <Save className="mr-2 h-4 w-4" />
            {saved && !hasChanges ? t('review.saved') : t('review.save')}
          </>
        )}
      </Button>
    </div>
  );
}
