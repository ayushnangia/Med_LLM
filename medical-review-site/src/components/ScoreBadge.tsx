'use client';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface ScoreBadgeProps {
  score: number;
  label?: string;
  showBar?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function getScoreColor(score: number): string {
  if (score >= 0.7) return 'bg-green-500';
  if (score >= 0.4) return 'bg-amber-500';
  return 'bg-red-500';
}

function getScoreVariant(score: number): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (score >= 0.7) return 'default';
  if (score >= 0.4) return 'secondary';
  return 'destructive';
}

export function ScoreBadge({ score, label, showBar = false, size = 'md' }: ScoreBadgeProps) {
  const percentage = Math.round(score * 100);

  if (showBar) {
    return (
      <div className="space-y-1">
        {label && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{percentage}%</span>
          </div>
        )}
        <Progress
          value={percentage}
          className={cn(
            'h-2',
            size === 'sm' && 'h-1.5',
            size === 'lg' && 'h-3'
          )}
        />
      </div>
    );
  }

  return (
    <Badge
      variant={getScoreVariant(score)}
      className={cn(
        size === 'sm' && 'text-xs px-1.5 py-0',
        size === 'lg' && 'text-base px-3 py-1'
      )}
    >
      {label && <span className="mr-1">{label}:</span>}
      {percentage}%
    </Badge>
  );
}

interface CorrectBadgeProps {
  isCorrect: boolean;
  label?: string;
}

export function CorrectBadge({ isCorrect, label }: CorrectBadgeProps) {
  return (
    <Badge variant={isCorrect ? 'default' : 'destructive'}>
      {label && <span className="mr-1">{label}:</span>}
      {isCorrect ? 'Korrekt' : 'Inkorrekt'}
    </Badge>
  );
}

interface CountBadgeProps {
  correct: number;
  total: number;
}

export function CountBadge({ correct, total }: CountBadgeProps) {
  const ratio = correct / total;
  return (
    <Badge variant={ratio >= 0.5 ? 'default' : ratio > 0 ? 'secondary' : 'destructive'}>
      {correct}/{total} Modelle korrekt
    </Badge>
  );
}
