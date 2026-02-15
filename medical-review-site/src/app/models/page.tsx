import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ModelComparisonBarChart } from '@/components/ModelComparisonChart';
import { getModelSummaries, getSummary } from '@/lib/data';
import { getModelDisplayName } from '@/lib/types';
import { Award, Target, Brain, Stethoscope, MessageSquare, Clock } from 'lucide-react';

export default function ModelsPage() {
  const models = getModelSummaries();
  const summary = getSummary();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Modellvergleich</h1>
        <p className="text-muted-foreground mt-2">
          Detaillierte Metriken für alle {summary.total_models} evaluierten LLMs
        </p>
      </div>

      {/* Overview Chart */}
      <ModelComparisonBarChart models={models} />

      {/* Model Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {models.map((model, idx) => (
          <Card
            key={model.model_id}
            className={
              idx === 0
                ? 'border-2 border-primary'
                : idx === 1
                ? 'border-2 border-secondary'
                : ''
            }
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">
                    {getModelDisplayName(model.model_id)}
                  </CardTitle>
                  <CardDescription className="text-xs font-mono mt-1">
                    {model.model_id}
                  </CardDescription>
                </div>
                {idx === 0 && (
                  <Badge variant="default" className="bg-yellow-500">
                    <Award className="h-3 w-3 mr-1" />
                    #1
                  </Badge>
                )}
                {idx === 1 && (
                  <Badge variant="secondary">
                    #2
                  </Badge>
                )}
                {idx === 2 && (
                  <Badge variant="outline">
                    #3
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Main Accuracy */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm flex items-center gap-1">
                    <Target className="h-4 w-4" />
                    Richter-Genauigkeit
                  </span>
                  <span className="font-bold">{model.judge_accuracy.toFixed(1)}%</span>
                </div>
                <Progress value={model.judge_accuracy} className="h-2" />
              </div>

              {/* Score Breakdown */}
              <div className="space-y-3 pt-2 border-t">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Brain className="h-3 w-3" />
                    Semantik
                  </span>
                  <span>{(model.avg_semantic_score * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Stethoscope className="h-3 w-3" />
                    Klinisch
                  </span>
                  <span>{(model.avg_clinical_score * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <MessageSquare className="h-3 w-3" />
                    Begründung
                  </span>
                  <span>{(model.avg_reasoning_quality * 100).toFixed(1)}%</span>
                </div>
              </div>

              {/* Overall Score */}
              <div className="pt-2 border-t">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Gesamt-Score</span>
                  <Badge
                    variant={
                      model.avg_overall_score >= 0.7
                        ? 'default'
                        : model.avg_overall_score >= 0.5
                        ? 'secondary'
                        : 'destructive'
                    }
                  >
                    {(model.avg_overall_score * 100).toFixed(1)}%
                  </Badge>
                </div>
              </div>

              {/* Match Rates */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t text-xs">
                <div className="text-center p-2 bg-muted rounded">
                  <div className="font-medium">{model.metastatic_accuracy.toFixed(0)}%</div>
                  <div className="text-muted-foreground">Met. korrekt</div>
                </div>
                <div className="text-center p-2 bg-muted rounded">
                  <div className="font-medium">{model.therapy_exact_match_rate.toFixed(0)}%</div>
                  <div className="text-muted-foreground">Exakt</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detailed Comparison Table */}
      <Card>
        <CardHeader>
          <CardTitle>Detaillierte Metriken</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2">Modell</th>
                  <th className="text-right py-3 px-2">Fälle</th>
                  <th className="text-right py-3 px-2">Genauigkeit</th>
                  <th className="text-right py-3 px-2">Met. Acc.</th>
                  <th className="text-right py-3 px-2">Exakt</th>
                  <th className="text-right py-3 px-2">Semantik</th>
                  <th className="text-right py-3 px-2">Klinisch</th>
                  <th className="text-right py-3 px-2">Begründung</th>
                  <th className="text-right py-3 px-2">Gesamt</th>
                </tr>
              </thead>
              <tbody>
                {models.map((model, idx) => (
                  <tr
                    key={model.model_id}
                    className={`border-b ${idx === 0 ? 'bg-primary/5' : ''}`}
                  >
                    <td className="py-3 px-2 font-medium">
                      {getModelDisplayName(model.model_id)}
                    </td>
                    <td className="py-3 px-2 text-right">{model.total_cases}</td>
                    <td className="py-3 px-2 text-right font-medium">
                      {model.judge_accuracy.toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-right">
                      {model.metastatic_accuracy.toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-right">
                      {model.therapy_exact_match_rate.toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-right">
                      {(model.avg_semantic_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-right">
                      {(model.avg_clinical_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-right">
                      {(model.avg_reasoning_quality * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-right font-bold">
                      {(model.avg_overall_score * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Metriken-Erklärung</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            <strong>Richter-Genauigkeit:</strong> Anteil der Fälle, bei denen GPT-5.2 die Vorhersage als korrekt bewertet hat.
          </p>
          <p>
            <strong>Met. Acc.:</strong> Genauigkeit bei der Erkennung des Metastasierungsstatus.
          </p>
          <p>
            <strong>Exakt:</strong> Anteil der Therapieempfehlungen, die exakt mit der Ground Truth übereinstimmen.
          </p>
          <p>
            <strong>Semantik:</strong> Semantische Übereinstimmung der Therapieempfehlung (0-100%).
          </p>
          <p>
            <strong>Klinisch:</strong> Klinische Angemessenheit der Empfehlung (0-100%).
          </p>
          <p>
            <strong>Begründung:</strong> Qualität der medizinischen Begründung (0-100%).
          </p>
          <p>
            <strong>Gesamt:</strong> Gewichteter Gesamtscore aus allen Metriken.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
