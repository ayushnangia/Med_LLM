'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

export type JudgeCorrectValue = 'agree' | 'disagree' | 'partial';

export interface JudgeReviewFormData {
  judge_correct: JudgeCorrectValue | null;
  judge_reasoning_quality: number;
  comment: string;
}

interface JudgeReviewFormProps {
  initialData?: JudgeReviewFormData;
  saved?: boolean;
  onChange: (data: JudgeReviewFormData) => void;
}

export function JudgeReviewForm({ initialData, saved, onChange }: JudgeReviewFormProps) {
  const { t } = useI18n();
  const [judgeCorrect, setJudgeCorrect] = useState<JudgeCorrectValue | null>(
    initialData?.judge_correct ?? null
  );
  const [reasoningQuality, setReasoningQuality] = useState(
    initialData?.judge_reasoning_quality ?? 5
  );
  const [comment, setComment] = useState(initialData?.comment ?? '');

  const emitChange = (
    correct: JudgeCorrectValue | null,
    quality: number,
    text: string
  ) => {
    onChange({
      judge_correct: correct,
      judge_reasoning_quality: quality,
      comment: text,
    });
  };

  const handleCorrectChange = (value: JudgeCorrectValue) => {
    setJudgeCorrect(value);
    emitChange(value, reasoningQuality, comment);
  };

  const handleQualityChange = (value: number) => {
    setReasoningQuality(value);
    emitChange(judgeCorrect, value, comment);
  };

  const handleCommentChange = (value: string) => {
    setComment(value);
    emitChange(judgeCorrect, reasoningQuality, value);
  };

  return (
    <div className="space-y-3 pt-3 border-t border-dashed">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-purple-800 dark:text-purple-200">
          {t('judgeReview.agreeQuestion')}
        </span>
        {saved && (
          <span className="text-xs text-green-600 flex items-center gap-1">
            <Check className="h-3 w-3" /> {t('judgeReview.saved')}
          </span>
        )}
      </div>

      {/* Agree / Partial / Disagree */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant={judgeCorrect === 'agree' ? 'default' : 'outline'}
          onClick={() => handleCorrectChange('agree')}
          className="flex-1"
        >
          {t('judgeReview.agree')}
        </Button>
        <Button
          size="sm"
          variant={judgeCorrect === 'partial' ? 'secondary' : 'outline'}
          onClick={() => handleCorrectChange('partial')}
          className="flex-1"
        >
          {t('judgeReview.partial')}
        </Button>
        <Button
          size="sm"
          variant={judgeCorrect === 'disagree' ? 'destructive' : 'outline'}
          onClick={() => handleCorrectChange('disagree')}
          className="flex-1"
        >
          {t('judgeReview.disagree')}
        </Button>
      </div>

      {/* Reasoning Quality (0-9) */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">{t('judgeReview.reasoningQuality')}</label>
          <span className="text-sm font-medium tabular-nums">{reasoningQuality}/9</span>
        </div>
        <div className="flex gap-1">
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
            <button
              key={n}
              onClick={() => handleQualityChange(n)}
              className={cn(
                'flex-1 h-8 text-xs font-medium rounded transition-colors',
                reasoningQuality === n
                  ? 'bg-purple-600 text-white'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Comment */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium">{t('judgeReview.comment')}</label>
        <textarea
          value={comment}
          onChange={(e) => handleCommentChange(e.target.value)}
          placeholder={t('judgeReview.commentPlaceholder')}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
          rows={2}
        />
      </div>
    </div>
  );
}
