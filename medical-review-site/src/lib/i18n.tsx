'use client';

import { createContext, useContext, useSyncExternalStore, useCallback, ReactNode } from 'react';

export type Language = 'de' | 'en';

const translations = {
  de: {
    // Navigation
    'nav.start': 'Start',
    'nav.allCases': 'Alle Fälle',
    'nav.change': 'Ändern',

    // Home page
    'home.title': 'Medizinische Fall-Bewertung',
    'home.subtitle': 'NCC Therapieempfehlungen - LLM Review',
    'home.yourName': 'Ihr Name',
    'home.namePlaceholder': 'z.B. Dr. Schmidt',
    'home.startReview': 'Bewertung starten',
    'home.savedReviews': 'Gespeicherte Bewertungen:',
    'home.exportCsv': 'Als CSV exportieren',
    'home.exportAll': 'Alle exportieren',
    'home.exportMine': 'Meine exportieren',
    'home.exportReviews': 'Arzt-Bewertungen',
    'home.exportJudgeReviews': 'Richter-Bewertungen',
    'home.info1': '35 Nierenzellkarzinom-Fälle | 6 LLM-Modelle',
    'home.info2': 'Bewertungen werden auf dem Server gespeichert',
    'home.loading': 'Lade...',

    // Doctor selector
    'doctor.selectDoctor': 'Arzt auswählen',
    'doctor.addNew': 'Neuen Arzt hinzufügen',
    'doctor.register': 'Registrieren',
    'doctor.cancel': 'Abbrechen',
    'doctor.reviews': 'Bewertungen',
    'doctor.yourReviews': 'Ihre Bewertungen:',
    'doctor.totalReviews': 'Gesamt:',

    // Case page
    'case.reviewer': 'Gutachter',
    'case.back': 'Zurück',
    'case.next': 'Weiter',
    'case.caseOf': 'Fall {current} von {total}',
    'case.metastatic': 'Metastasiert',
    'case.nonMetastatic': 'Nicht metast.',
    'case.groundTruth': 'SOLL-THERAPIE (Tumorboard-Empfehlung)',
    'case.home': 'Startseite',
    'case.finished': 'Fertig - Zur Startseite',
    'case.loadingCase': 'Lade Fall...',

    // Model selector
    'models.select': 'Modelle auswählen:',
    'models.all': 'Alle',
    'models.none': 'Keine',
    'models.loading': 'Lade Modelle...',
    'models.noneSelected': 'Keine Modelle ausgewählt. Bitte wählen Sie oben mindestens ein Modell aus.',

    // Model card
    'model.overall': 'Gesamt:',
    'model.clinical': 'Klinisch:',
    'model.semantic': 'Semantik:',
    'model.reasoning': 'Begründung:',
    'model.showDetails': 'Details anzeigen',
    'model.therapy': 'Therapie:',
    'model.reason': 'Begründung:',
    'model.modelReasoning': 'Modell-Begründung:',
    'model.inference': 'Inferenz:',
    'model.judge': 'Richter:',

    // Review form
    'review.yourReview': 'Ihre Bewertung',
    'review.saved': 'Gespeichert',
    'review.loading': 'Lade Bewertung...',
    'review.acceptable': 'Therapie akzeptabel?',
    'review.yes': 'Ja',
    'review.no': 'Nein',
    'review.exactMatch': 'Übereinstimmung',
    'review.patientOriented': 'Patientenorientiert',
    'review.quality': 'Vorhersagequalität',
    'review.save': 'Speichern',
    'review.saveAll': 'Alle speichern',
    'review.allSaved': 'Alle gespeichert',

    // Cases list
    'cases.title': 'Fälle',
    'cases.subtitle': '{count} NCC-Fälle mit Therapieempfehlungen von {models} Modellen',
    'cases.search': 'Suche nach Fall-ID, Patient oder Diagnose...',
    'cases.all': 'Alle',
    'cases.metastatic': 'Metastasiert',
    'cases.nonMetastatic': 'Nicht metastasiert',
    'cases.results': '{count} Ergebnisse',
    'cases.filter': 'Filter:',
    'cases.noResults': 'Keine Fälle gefunden.',
    'cases.resetFilter': 'Filter zurücksetzen',
    'cases.reviewed': 'bewertet',
    'cases.modelsCorrect': '{correct}/{total} Modelle korrekt',
    'cases.recommendedTherapy': 'Empfohlene Therapie:',
    'cases.showUnreviewed': 'Nur unbewertete',
    'cases.showAll': 'Alle anzeigen',
    'cases.remaining': '{cases} Fälle · {count} Reviews offen',
    'cases.allReviewed': 'Alle bewertet',
    'cases.reviewedOf': '{done}/{total} bewertet',
    'models.reviewed': 'Bewertet',
    'models.optional': '(optional)',
    'case.reviewProgress': '{done} von {total} Pflichtmodellen bewertet',

    // Judge review page
    'judgeReview.title': 'Richter-Bewertung',
    'judgeReview.subtitle': 'Bewerten Sie die KI-Richter-Einschätzung',
    'judgeReview.backToCases': 'Zurück zu Fälle',
    'judgeReview.caseOf': 'Fall {current} von {total}',
    'judgeReview.groundTruth': 'Soll-Therapie',
    'judgeReview.yourReview': 'IHRE BEWERTUNG',
    'judgeReview.judgeEval': 'RICHTER-BEWERTUNG',
    'judgeReview.acceptable': 'Akzeptabel:',
    'judgeReview.exactMatch': 'Übereinstimmung:',
    'judgeReview.patientOriented': 'Patientenorientiert:',
    'judgeReview.quality': 'Qualität:',
    'judgeReview.correct': 'Korrekt:',
    'judgeReview.overall': 'Gesamt:',
    'judgeReview.clinical': 'Klinisch:',
    'judgeReview.semantic': 'Semantik:',
    'judgeReview.reasoning': 'Begründung:',
    'judgeReview.judgeReasoning': 'Richter-Begründung:',
    'judgeReview.agreeQuestion': 'Stimmen Sie dem Richter zu?',
    'judgeReview.agree': 'Stimme zu',
    'judgeReview.partial': 'Teilweise',
    'judgeReview.disagree': 'Widerspreche',
    'judgeReview.reasoningQuality': 'Richter-Begründungsqualität',
    'judgeReview.comment': 'Kommentar (optional)',
    'judgeReview.commentPlaceholder': 'z.B. "Richter hat X übersehen", "Gute Erkennung von Y"...',
    'judgeReview.saveAll': 'Alle Richter-Bewertungen speichern',
    'judgeReview.allSaved': 'Alle gespeichert',
    'judgeReview.saving': 'Speichern...',
    'judgeReview.saved': 'Gespeichert',
    'judgeReview.yes': 'Ja',
    'judgeReview.no': 'Nein',
    'judgeReview.prev': 'Vorheriger',
    'judgeReview.next': 'Nächster',
    'judgeReview.noReviews': 'Keine abgeschlossenen Bewertungen für diesen Fall gefunden.',
    'judgeReview.notReviewed': 'Noch nicht bewertet',
    'cases.reviewJudge': 'Richter bewerten',
    'judgeReview.ctaTitle': 'Alle Modelle bewertet!',
    'judgeReview.ctaDescription': 'Bewerten Sie jetzt die Einschätzung des KI-Richters — vergleichen Sie sein Urteil mit Ihrem für jedes Modell.',
    'judgeReview.ctaButton': 'Zur Richter-Bewertung',
    'nav.judgeReview': 'Richter-Bewertung',
    'judgeReview.reviewJudge': 'Richter bewerten',
    'judgeReview.selectJudge': 'Richter auswählen',
    'judgeReview.saveNextJudge': 'Speichern & Nächster Richter',
    'case.nextCase': 'Nächster Fall',

    // Clinical context
    'clinical.anamnese': 'Anamnese',
    'clinical.nebendiagnosen': 'Nebendiagnosen',
    'clinical.medikation': 'Medikation',
    'clinical.bildgebung': 'Bildgebung',
    'clinical.priorTherapies': 'Vortherapien',
    'clinical.karnofsky': 'Karnofsky',
    'clinical.comorbidity': 'Komorbidität',
    'clinical.lifeExpectancy': 'Lebenserwartung',
    'clinical.diagnosis': 'Diagnose',
    'clinical.stadium': 'Stadium',
    'clinical.histologie': 'Histologie',
    'clinical.tnm': 'TNM',
    'clinical.imdc': 'IMDC-Risiko',
    'clinical.grading': 'Grading',
    'clinical.klarzellig': 'Klarzelliger Subtyp',
    'clinical.patientOverview': 'Patientenübersicht',
  },
  en: {
    // Navigation
    'nav.start': 'Start',
    'nav.allCases': 'All Cases',
    'nav.change': 'Change',

    // Home page
    'home.title': 'Medical Case Review',
    'home.subtitle': 'NCC Therapy Recommendations - LLM Review',
    'home.yourName': 'Your Name',
    'home.namePlaceholder': 'e.g. Dr. Smith',
    'home.startReview': 'Start Review',
    'home.savedReviews': 'Saved Reviews:',
    'home.exportCsv': 'Export as CSV',
    'home.exportAll': 'Export All',
    'home.exportMine': 'Export Mine',
    'home.exportReviews': 'Doctor Reviews',
    'home.exportJudgeReviews': 'Judge Reviews',
    'home.info1': '35 Renal Cell Carcinoma Cases | 6 LLM Models',
    'home.info2': 'Reviews are saved on the server',
    'home.loading': 'Loading...',

    // Doctor selector
    'doctor.selectDoctor': 'Select Doctor',
    'doctor.addNew': 'Add New Doctor',
    'doctor.register': 'Register',
    'doctor.cancel': 'Cancel',
    'doctor.reviews': 'reviews',
    'doctor.yourReviews': 'Your Reviews:',
    'doctor.totalReviews': 'Total:',

    // Case page
    'case.reviewer': 'Reviewer',
    'case.back': 'Back',
    'case.next': 'Next',
    'case.caseOf': 'Case {current} of {total}',
    'case.metastatic': 'Metastatic',
    'case.nonMetastatic': 'Non-metastatic',
    'case.groundTruth': 'TARGET THERAPY (Tumor Board Recommendation)',
    'case.home': 'Home',
    'case.finished': 'Finished - Back to Home',
    'case.loadingCase': 'Loading case...',

    // Model selector
    'models.select': 'Select models:',
    'models.all': 'All',
    'models.none': 'None',
    'models.loading': 'Loading models...',
    'models.noneSelected': 'No models selected. Please select at least one model above.',

    // Model card
    'model.overall': 'Overall:',
    'model.clinical': 'Clinical:',
    'model.semantic': 'Semantic:',
    'model.reasoning': 'Reasoning:',
    'model.showDetails': 'Show details',
    'model.therapy': 'Therapy:',
    'model.reason': 'Reason:',
    'model.modelReasoning': 'Model reasoning:',
    'model.inference': 'Inference:',
    'model.judge': 'Judge:',

    // Review form
    'review.yourReview': 'Your Review',
    'review.saved': 'Saved',
    'review.loading': 'Loading review...',
    'review.acceptable': 'Therapy acceptable?',
    'review.yes': 'Yes',
    'review.no': 'No',
    'review.exactMatch': 'Exact Match',
    'review.patientOriented': 'Patient-Oriented',
    'review.quality': 'Prediction Quality',
    'review.save': 'Save',
    'review.saveAll': 'Save All',
    'review.allSaved': 'All Saved',

    // Cases list
    'cases.title': 'Cases',
    'cases.subtitle': '{count} NCC cases with therapy recommendations from {models} models',
    'cases.search': 'Search by case ID, patient, or diagnosis...',
    'cases.all': 'All',
    'cases.metastatic': 'Metastatic',
    'cases.nonMetastatic': 'Non-metastatic',
    'cases.results': '{count} results',
    'cases.filter': 'Filter:',
    'cases.noResults': 'No cases found.',
    'cases.resetFilter': 'Reset filter',
    'cases.reviewed': 'reviewed',
    'cases.modelsCorrect': '{correct}/{total} models correct',
    'cases.recommendedTherapy': 'Recommended therapy:',
    'cases.showUnreviewed': 'Unreviewed only',
    'cases.showAll': 'Show all',
    'cases.remaining': '{cases} cases · {count} reviews remaining',
    'cases.allReviewed': 'All reviewed',
    'cases.reviewedOf': '{done}/{total} reviewed',
    'models.reviewed': 'Reviewed',
    'models.optional': '(optional)',
    'case.reviewProgress': '{done} of {total} required models reviewed',

    // Judge review page
    'judgeReview.title': 'Judge Review',
    'judgeReview.subtitle': 'Evaluate the AI judge\'s assessment',
    'judgeReview.backToCases': 'Back to Cases',
    'judgeReview.caseOf': 'Case {current} of {total}',
    'judgeReview.groundTruth': 'Target Therapy',
    'judgeReview.yourReview': 'YOUR REVIEW',
    'judgeReview.judgeEval': 'JUDGE EVALUATION',
    'judgeReview.acceptable': 'Acceptable:',
    'judgeReview.exactMatch': 'Exact Match:',
    'judgeReview.patientOriented': 'Patient-Oriented:',
    'judgeReview.quality': 'Quality:',
    'judgeReview.correct': 'Correct:',
    'judgeReview.overall': 'Overall:',
    'judgeReview.clinical': 'Clinical:',
    'judgeReview.semantic': 'Semantic:',
    'judgeReview.reasoning': 'Reasoning:',
    'judgeReview.judgeReasoning': 'Judge Reasoning:',
    'judgeReview.agreeQuestion': 'Do you agree with the judge?',
    'judgeReview.agree': 'Agree',
    'judgeReview.partial': 'Partial',
    'judgeReview.disagree': 'Disagree',
    'judgeReview.reasoningQuality': 'Judge Reasoning Quality',
    'judgeReview.comment': 'Comment (optional)',
    'judgeReview.commentPlaceholder': 'e.g. "Judge missed X", "Good catch on Y"...',
    'judgeReview.saveAll': 'Save All Judge Reviews',
    'judgeReview.allSaved': 'All Saved',
    'judgeReview.saving': 'Saving...',
    'judgeReview.saved': 'Saved',
    'judgeReview.yes': 'Yes',
    'judgeReview.no': 'No',
    'judgeReview.prev': 'Previous',
    'judgeReview.next': 'Next',
    'judgeReview.noReviews': 'No completed reviews found for this case.',
    'judgeReview.notReviewed': 'Not yet reviewed',
    'cases.reviewJudge': 'Review Judge',
    'judgeReview.ctaTitle': 'All models reviewed!',
    'judgeReview.ctaDescription': 'Now evaluate the AI judge\'s assessment — compare its verdict with yours for each model.',
    'judgeReview.ctaButton': 'Go to Judge Review',
    'nav.judgeReview': 'Judge Review',
    'judgeReview.reviewJudge': 'Review Judge',
    'judgeReview.selectJudge': 'Select Judge',
    'judgeReview.saveNextJudge': 'Save & Next Judge',
    'case.nextCase': 'Next Case',

    // Clinical context
    'clinical.anamnese': 'Medical History',
    'clinical.nebendiagnosen': 'Secondary Diagnoses',
    'clinical.medikation': 'Medication',
    'clinical.bildgebung': 'Imaging',
    'clinical.priorTherapies': 'Prior Therapies',
    'clinical.karnofsky': 'Karnofsky',
    'clinical.comorbidity': 'Comorbidity',
    'clinical.lifeExpectancy': 'Life Expectancy',
    'clinical.diagnosis': 'Diagnosis',
    'clinical.stadium': 'Stage',
    'clinical.histologie': 'Histology',
    'clinical.tnm': 'TNM',
    'clinical.imdc': 'IMDC Risk',
    'clinical.grading': 'Grading',
    'clinical.klarzellig': 'Clear Cell Subtype',
    'clinical.patientOverview': 'Patient Overview',
  },
};

type TranslationKey = keyof typeof translations.de;

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

const LANGUAGE_KEY = 'medical-review-language';

// Language change listeners for useSyncExternalStore
const languageListeners = new Set<() => void>();

function notifyLanguageListeners() {
  languageListeners.forEach(cb => cb());
}

// Hook to sync language with localStorage
function useStoredLanguage(): Language {
  const subscribe = useCallback((callback: () => void) => {
    languageListeners.add(callback);
    window.addEventListener('storage', callback);
    return () => {
      languageListeners.delete(callback);
      window.removeEventListener('storage', callback);
    };
  }, []);

  const getSnapshot = useCallback(() => {
    const stored = localStorage.getItem(LANGUAGE_KEY);
    return (stored === 'de' || stored === 'en') ? stored : 'de';
  }, []);

  const getServerSnapshot = useCallback(() => 'de' as Language, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const language = useStoredLanguage();

  const setLanguage = useCallback((lang: Language) => {
    localStorage.setItem(LANGUAGE_KEY, lang);
    notifyLanguageListeners();
  }, []);

  const t = useCallback((key: TranslationKey, params?: Record<string, string | number>): string => {
    let text = translations[language][key] || translations.de[key] || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, String(v));
      });
    }
    return text;
  }, [language]);

  const contextValue: I18nContextType = {
    language,
    setLanguage,
    t,
  };

  return (
    <I18nContext.Provider value={contextValue}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

export function LanguageToggle() {
  const { language, setLanguage } = useI18n();

  return (
    <button
      onClick={() => setLanguage(language === 'de' ? 'en' : 'de')}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md border bg-background hover:bg-muted transition-colors"
      title={language === 'de' ? 'Switch to English' : 'Auf Deutsch wechseln'}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
        <path d="M2 12h20" />
      </svg>
      <span>{language === 'de' ? 'EN' : 'DE'}</span>
    </button>
  );
}
