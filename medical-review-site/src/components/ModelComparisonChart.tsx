'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ModelSummary } from '@/lib/types';
import { getModelDisplayName } from '@/lib/types';

interface ModelComparisonChartProps {
  models: ModelSummary[];
}

export function ModelComparisonBarChart({ models }: ModelComparisonChartProps) {
  const data = models.map(m => ({
    name: getModelDisplayName(m.model_id).split(' ').slice(0, 2).join(' '),
    'Richter-Genauigkeit': Math.round(m.judge_accuracy),
    'Semantik': Math.round(m.avg_semantic_score * 100),
    'Klinisch': Math.round(m.avg_clinical_score * 100),
    'Gesamt': Math.round(m.avg_overall_score * 100),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modellvergleich</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="Richter-Genauigkeit" fill="#2563eb" />
              <Bar dataKey="Gesamt" fill="#22c55e" />
              <Bar dataKey="Klinisch" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

export function ModelRadarChart({ models }: ModelComparisonChartProps) {
  // Find the best model to highlight
  const bestModel = models[0];

  const data = [
    {
      metric: 'Genauigkeit',
      [getModelDisplayName(bestModel.model_id)]: Math.round(bestModel.judge_accuracy),
      fullMark: 100,
    },
    {
      metric: 'Semantik',
      [getModelDisplayName(bestModel.model_id)]: Math.round(bestModel.avg_semantic_score * 100),
      fullMark: 100,
    },
    {
      metric: 'Klinisch',
      [getModelDisplayName(bestModel.model_id)]: Math.round(bestModel.avg_clinical_score * 100),
      fullMark: 100,
    },
    {
      metric: 'Begründung',
      [getModelDisplayName(bestModel.model_id)]: Math.round(bestModel.avg_reasoning_quality * 100),
      fullMark: 100,
    },
    {
      metric: 'Gesamt',
      [getModelDisplayName(bestModel.model_id)]: Math.round(bestModel.avg_overall_score * 100),
      fullMark: 100,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bestes Modell: {getModelDisplayName(bestModel.model_id)}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} />
              <Radar
                name={getModelDisplayName(bestModel.model_id)}
                dataKey={getModelDisplayName(bestModel.model_id)}
                stroke="#2563eb"
                fill="#2563eb"
                fillOpacity={0.5}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
