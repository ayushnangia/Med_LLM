'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Check, X, AlertCircle } from 'lucide-react';
import type { ModelPrediction, GroundTruth } from '@/lib/types';

interface TherapyCompareProps {
  groundTruth: GroundTruth;
  prediction: ModelPrediction;
}

export function TherapyCompare({ groundTruth, prediction }: TherapyCompareProps) {
  return (
    <div className="grid md:grid-cols-2 gap-4">
      {/* Ground Truth */}
      <Card className="border-green-200 bg-green-50/50 dark:bg-green-950/20">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Check className="h-4 w-4 text-green-600" />
            Tumorboard-Empfehlung
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Badge variant={groundTruth.metastatic ? 'destructive' : 'secondary'}>
              {groundTruth.metastatic ? 'Metastasiert' : 'Nicht metastasiert'}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Therapie:</p>
            <p className="text-sm">{groundTruth.therapy}</p>
          </div>
        </CardContent>
      </Card>

      {/* Prediction */}
      <Card className={
        prediction.judge_evaluation.is_correct
          ? 'border-green-200 bg-green-50/50 dark:bg-green-950/20'
          : 'border-red-200 bg-red-50/50 dark:bg-red-950/20'
      }>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            {prediction.judge_evaluation.is_correct
              ? <Check className="h-4 w-4 text-green-600" />
              : <X className="h-4 w-4 text-red-600" />
            }
            Modell-Vorhersage
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant={prediction.pred_metastatic ? 'destructive' : 'secondary'}>
              {prediction.pred_metastatic ? 'Metastasiert' : 'Nicht metastasiert'}
            </Badge>
            {prediction.metastatic_correct
              ? <Check className="h-4 w-4 text-green-600" />
              : <X className="h-4 w-4 text-red-600" />
            }
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Therapie:</p>
            <p className="text-sm">{prediction.pred_therapy}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {prediction.pred_category && (
              <Badge variant="outline">{prediction.pred_category}</Badge>
            )}
            {prediction.pred_imdc_risk && prediction.pred_imdc_risk !== 'nicht_anwendbar' && (
              <Badge variant="outline">IMDC: {prediction.pred_imdc_risk}</Badge>
            )}
            <Badge variant="outline">
              Konfidenz: {Math.round(prediction.pred_confidence * 100)}%
            </Badge>
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            <Badge variant={prediction.therapy_exact_match ? 'default' : 'secondary'}>
              {prediction.therapy_exact_match ? 'Exakt' : 'Nicht exakt'}
            </Badge>
            <Badge variant={prediction.therapy_acceptable ? 'default' : 'secondary'}>
              {prediction.therapy_acceptable ? 'Akzeptabel' : 'Nicht akzeptabel'}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
