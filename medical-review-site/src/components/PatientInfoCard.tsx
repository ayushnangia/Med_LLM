'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { PatientInfo, DiagnosisInfo } from '@/lib/types';

interface PatientInfoCardProps {
  patient: PatientInfo;
  diagnosis: DiagnosisInfo;
  caseId: string;
}

export function PatientInfoCard({ patient, diagnosis, caseId }: PatientInfoCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{patient.name}</span>
          <Badge variant="outline">{caseId}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Demographics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <InfoItem label="Alter" value={patient.age ? `${patient.age} Jahre` : '-'} />
          <InfoItem label="ECOG" value={patient.ecog !== null ? patient.ecog.toString() : '-'} />
          <InfoItem label="Karnofsky" value={patient.karnofsky !== null ? `${patient.karnofsky}%` : '-'} />
          <InfoItem label="Komorbidität" value={patient.comorbidity || '-'} />
        </div>

        {/* Diagnosis */}
        <div className="pt-4 border-t">
          <h4 className="text-sm font-medium text-muted-foreground mb-2">Diagnose</h4>
          <p className="text-sm font-medium mb-2">{diagnosis.diagnose_kurz}</p>
          <div className="flex flex-wrap gap-2">
            {diagnosis.stadium && (
              <Badge variant="secondary">{diagnosis.stadium}</Badge>
            )}
            {diagnosis.histologie_subtyp && (
              <Badge variant="outline">Histologie: {diagnosis.histologie_subtyp}</Badge>
            )}
            {diagnosis.klarzellig !== null && (
              <Badge variant={diagnosis.klarzellig ? 'default' : 'secondary'}>
                {diagnosis.klarzellig ? 'Klarzellig' : 'Nicht-klarzellig'}
              </Badge>
            )}
            {diagnosis.tnm_cM && (
              <Badge variant="outline">TNM: {diagnosis.tnm_cM}</Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
