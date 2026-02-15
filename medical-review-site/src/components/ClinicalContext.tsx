'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { useI18n } from '@/lib/i18n';
import type { ClinicalContext as ClinicalContextType, PatientInfo, DiagnosisInfo } from '@/lib/types';
import {
  FileText,
  Pill,
  Stethoscope,
  Microscope,
  ImageIcon,
  Scissors,
  AlertCircle,
  HelpCircle
} from 'lucide-react';

interface ClinicalContextProps {
  patient: PatientInfo;
  diagnosis: DiagnosisInfo;
  context?: ClinicalContextType;
}

export function ClinicalContextDisplay({ patient, diagnosis, context }: ClinicalContextProps) {
  const { t, language } = useI18n();

  if (!context) {
    return null;
  }

  const labels = language === 'de' ? {
    medicalHistory: 'Anamnese',
    clinicalQuestion: 'Fragestellung',
    secondaryDiagnoses: 'Nebendiagnosen',
    medications: 'Medikation',
    imaging: 'Bildgebung',
    pathology: 'Pathologie',
    priorTherapies: 'Vorherige Therapien',
    tnmStaging: 'TNM-Staging',
    clinical: 'Klinisch',
    pathological: 'Pathologisch',
    grading: 'Grading',
    imdcRisk: 'IMDC-Risiko',
    unknown: 'Unbekannt',
  } : {
    medicalHistory: 'Medical History',
    clinicalQuestion: 'Clinical Question',
    secondaryDiagnoses: 'Secondary Diagnoses',
    medications: 'Medications',
    imaging: 'Imaging',
    pathology: 'Pathology',
    priorTherapies: 'Prior Therapies',
    tnmStaging: 'TNM Staging',
    clinical: 'Clinical',
    pathological: 'Pathological',
    grading: 'Grading',
    imdcRisk: 'IMDC Risk',
    unknown: 'Unknown',
  };

  const formatTNM = (tnm: { T: string | null; N: string | null; M: string | null; stage_group?: string | null } | undefined) => {
    if (!tnm) return null;
    const parts = [];
    if (tnm.T && tnm.T !== 'unknown') parts.push(`T${tnm.T}`);
    if (tnm.N && tnm.N !== 'unknown') parts.push(`N${tnm.N}`);
    if (tnm.M && tnm.M !== 'unknown') parts.push(`M${tnm.M}`);
    if (parts.length === 0) return null;
    return parts.join(' ');
  };

  return (
    <Card className="border-blue-200 dark:border-blue-800">
      <CardContent className="space-y-4 pt-4">
        {/* Clinical Question - Important, show prominently */}
        {context.fragestellung && (
          <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <HelpCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-amber-800 dark:text-amber-200 text-sm">
                  {labels.clinicalQuestion}:
                </span>
                {Array.isArray(context.fragestellung) ? (
                  <ul className="text-sm mt-1 list-disc list-inside space-y-1">
                    {context.fragestellung.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm mt-1">{context.fragestellung}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Medical History - Most important */}
        {context.anamnese_freitext && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Stethoscope className="h-4 w-4" />
              {labels.medicalHistory}
            </div>
            <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
              {context.anamnese_freitext}
            </p>
          </div>
        )}

        {/* TNM Staging */}
        {(diagnosis.tnm_clinical || diagnosis.tnm_pathological || diagnosis.tnm_string || diagnosis.grading) && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm font-medium">{labels.tnmStaging}:</span>
            {diagnosis.tnm_clinical && formatTNM(diagnosis.tnm_clinical) && (
              <Badge variant="outline" className="font-mono">
                c{formatTNM(diagnosis.tnm_clinical)}
              </Badge>
            )}
            {diagnosis.tnm_pathological && formatTNM(diagnosis.tnm_pathological) && (
              <Badge variant="outline" className="font-mono">
                p{formatTNM(diagnosis.tnm_pathological)}
              </Badge>
            )}
            {/* v1.0 schema single TNM string */}
            {diagnosis.tnm_string && !diagnosis.tnm_clinical && (
              <Badge variant="outline" className="font-mono">
                {diagnosis.tnm_string}
              </Badge>
            )}
            {diagnosis.grading && (
              <Badge variant="secondary">{diagnosis.grading}</Badge>
            )}
            {diagnosis.imdc_risiko && (
              <Badge variant={
                diagnosis.imdc_risiko === 'guenstig' ? 'default' :
                diagnosis.imdc_risiko === 'intermediär' ? 'secondary' : 'destructive'
              }>
                IMDC: {diagnosis.imdc_risiko}
              </Badge>
            )}
          </div>
        )}

        {/* Secondary Diagnoses */}
        {context.nebendiagnosen && context.nebendiagnosen.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-medium">
              <AlertCircle className="h-4 w-4" />
              {labels.secondaryDiagnoses}
            </div>
            <div className="flex flex-wrap gap-1">
              {context.nebendiagnosen.map((dx, i) => {
                // Handle both string format and object format {diagnose, details}
                const diagText = typeof dx === 'string' ? dx : dx.diagnose;
                const details = typeof dx === 'object' && dx.details ? ` (${dx.details})` : '';
                return (
                  <Badge key={i} variant="outline" className="text-xs">
                    {diagText}{details}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {/* Medications */}
        {context.medikation && context.medikation.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Pill className="h-4 w-4" />
              {labels.medications}
            </div>
            <div className="flex flex-wrap gap-1">
              {context.medikation.map((med, i) => {
                // Handle both schema versions: wirkstoff_oder_klasse (v1.1) and wirkstoff (v1.0)
                const name = med.wirkstoff_oder_klasse || med.wirkstoff || 'Unknown';
                const details = med.details || med.hinweis;
                return (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {name}
                    {details && ` (${details})`}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {/* Expandable sections for detailed info */}
        <Accordion type="multiple" className="w-full">
          {/* Imaging */}
          {context.bildgebung && context.bildgebung.length > 0 && (
            <AccordionItem value="imaging">
              <AccordionTrigger className="text-sm py-2">
                <div className="flex items-center gap-2">
                  <ImageIcon className="h-4 w-4" />
                  {labels.imaging} ({context.bildgebung.length})
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2">
                  {context.bildgebung.map((img, i) => (
                    <div key={i} className="text-sm bg-muted/50 rounded p-2">
                      <div className="flex items-center gap-2 font-medium">
                        <span>{img.modalitaet}</span>
                        {img.region && <span className="text-muted-foreground">- {img.region}</span>}
                        {img.datum && <span className="text-xs text-muted-foreground">({img.datum})</span>}
                      </div>
                      <p className="text-muted-foreground mt-1">{img.befund_kurz}</p>
                    </div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Pathology */}
          {context.pathologie && context.pathologie.length > 0 && (
            <AccordionItem value="pathology">
              <AccordionTrigger className="text-sm py-2">
                <div className="flex items-center gap-2">
                  <Microscope className="h-4 w-4" />
                  {labels.pathology} ({context.pathologie.length})
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2">
                  {context.pathologie.map((path, i) => (
                    <div key={i} className="text-sm bg-muted/50 rounded p-2">
                      <div className="flex items-center gap-2 font-medium">
                        <span>{path.diagnose}</span>
                        {path.datum && <span className="text-xs text-muted-foreground">({path.datum})</span>}
                      </div>
                      {path.material && (
                        <p className="text-muted-foreground text-xs">Material: {path.material}</p>
                      )}
                      {path.details && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.entries(path.details).map(([key, val]) => (
                            <Badge key={key} variant="outline" className="text-xs font-mono">
                              {key}: {val}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Prior Therapies */}
          {context.therapien_und_eingriffe && context.therapien_und_eingriffe.length > 0 && (
            <AccordionItem value="therapies">
              <AccordionTrigger className="text-sm py-2">
                <div className="flex items-center gap-2">
                  <Scissors className="h-4 w-4" />
                  {labels.priorTherapies} ({context.therapien_und_eingriffe.length})
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2">
                  {context.therapien_und_eingriffe.map((therapy, i) => {
                    // Handle both schema versions: beschreibung (v1.1) and regime (v1.0)
                    const description = therapy.beschreibung || therapy.regime || '';
                    const date = therapy.datum || therapy.datum_start;
                    return (
                      <div key={i} className="text-sm bg-muted/50 rounded p-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant="outline" className="text-xs">{therapy.typ}</Badge>
                          {therapy.linie && <Badge variant="secondary" className="text-xs">Linie {therapy.linie}</Badge>}
                          <span className="font-medium">{description}</span>
                          {date && <span className="text-xs text-muted-foreground">({date})</span>}
                        </div>
                        {therapy.intent && (
                          <p className="text-xs text-muted-foreground mt-1">Intent: {therapy.intent}</p>
                        )}
                        {therapy.status && (
                          <p className="text-xs text-muted-foreground">Status: {therapy.status}</p>
                        )}
                        {therapy.details && (
                          <p className="text-xs text-muted-foreground">{therapy.details}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}
        </Accordion>
      </CardContent>
    </Card>
  );
}
