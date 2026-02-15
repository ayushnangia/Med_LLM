import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
}));

// Mock the i18n hook
vi.mock('@/lib/i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, string | number>) => {
      const translations: Record<string, string> = {
        'cases.metastatic': 'Metastatic',
        'cases.nonMetastatic': 'Non-metastatic',
        'cases.allReviewed': 'All reviewed',
        'cases.reviewedOf': `${params?.done ?? '?'}/${params?.total ?? '?'} reviewed`,
        'cases.recommendedTherapy': 'Recommended therapy:',
        'cases.modelsCorrect': `${params?.correct ?? '?'}/${params?.total ?? '?'} models correct`,
        'models.select': 'Select models:',
        'models.all': 'All',
        'models.none': 'None',
        'models.loading': 'Loading models...',
        'models.reviewed': 'Reviewed',
        'models.optional': '(optional)',
        'models.noneSelected': 'No models selected.',
        'cases.reviewJudge': 'Review Judge',
      };
      return translations[key] || key;
    },
    language: 'en' as const,
  }),
  I18nProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock data module
vi.mock('@/lib/data', () => ({
  getCaseCorrectCount: () => 3,
}));

// Mock storage module
vi.mock('@/lib/storage', () => ({
  getSelectedModels: () => [],
  setSelectedModels: vi.fn(),
  getReviewerName: () => 'Test Doctor',
}));

// Mock types to provide constants
vi.mock('@/lib/types', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/types')>();
  return {
    ...actual,
  };
});

// ============================================================
// CaseCard Tests
// ============================================================
describe('CaseCard', () => {
  const mockCase = {
    case_id: 'ncc_1',
    patient: {
      name: 'Müller, Hans',
      age: 65,
      ecog: 1,
      karnofsky: 80,
      comorbidity: 'mittel',
    },
    diagnosis: {
      diagnose_kurz: 'Nierenzellkarzinom',
      stadium: 'Stadium IV',
      histologie_subtyp: 'klarzellig',
      klarzellig: true,
      tnm_cM: 'M1',
    },
    ground_truth: {
      metastatic: true,
      therapy: 'Nivolumab + Cabozantinib',
    },
    predictions: {
      'google/gemma-3-27b-it': {},
      'google/gemma-3-4b-it': {},
      'google/medgemma-27b-text-it': {},
    },
  };

  it('renders case ID and patient name', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    render(<CaseCard caseItem={mockCase as any} />);

    expect(screen.getByText('ncc_1')).toBeInTheDocument();
    expect(screen.getByText('Müller, Hans')).toBeInTheDocument();
  });

  it('shows progress badge when reviewedRequiredCount is provided', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    render(
      <CaseCard
        caseItem={mockCase as any}
        reviewedRequiredCount={2}
        totalRequiredCount={5}
      />
    );

    expect(screen.getByText('2/5 reviewed')).toBeInTheDocument();
  });

  it('shows "All reviewed" when all required models are reviewed', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    render(
      <CaseCard
        caseItem={mockCase as any}
        reviewedRequiredCount={5}
        totalRequiredCount={5}
      />
    );

    expect(screen.getByText('All reviewed')).toBeInTheDocument();
  });

  it('dims the card when all required models are reviewed', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    const { container } = render(
      <CaseCard
        caseItem={mockCase as any}
        reviewedRequiredCount={5}
        totalRequiredCount={5}
      />
    );

    // The Card should have opacity-60 class
    const card = container.querySelector('[class*="opacity-60"]');
    expect(card).toBeTruthy();
  });

  it('does NOT dim the card when there are unreviewed models', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    const { container } = render(
      <CaseCard
        caseItem={mockCase as any}
        reviewedRequiredCount={2}
        totalRequiredCount={5}
      />
    );

    const card = container.querySelector('[class*="opacity-60"]');
    expect(card).toBeFalsy();
  });

  it('renders progress bar', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    const { container } = render(
      <CaseCard
        caseItem={mockCase as any}
        reviewedRequiredCount={3}
        totalRequiredCount={5}
      />
    );

    // Progress bar should be 60% width
    const progressBar = container.querySelector('[style*="width: 60%"]');
    expect(progressBar).toBeTruthy();
  });

  it('renders metastatic badge', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    render(<CaseCard caseItem={mockCase as any} />);

    expect(screen.getByText('Metastatic')).toBeInTheDocument();
  });

  it('renders therapy preview', async () => {
    const { CaseCard } = await import('@/components/CaseCard');
    render(<CaseCard caseItem={mockCase as any} />);

    expect(screen.getByText('Nivolumab + Cabozantinib')).toBeInTheDocument();
  });
});

// ============================================================
// ModelSelector Tests
// ============================================================
describe('ModelSelector', () => {
  const availableModels = [
    'google/gemma-3-27b-it',
    'google/gemma-3-4b-it',
    'google/medgemma-27b-text-it',
    'allenai/Olmo-3.1-32B-Instruct',
    'allenai/Olmo-3.1-32B-Think',
    'OpenMeditron/Meditron3-Qwen2.5-7B',
  ];

  it('renders all available models', async () => {
    const { ModelSelector } = await import('@/components/ModelSelector');
    render(<ModelSelector availableModels={availableModels} selectedModels={availableModels.slice(0, 3)} />);

    expect(screen.getByText(/Gemma 3 27B/)).toBeInTheDocument();
    expect(screen.getByText(/Gemma 3 4B/)).toBeInTheDocument();
    expect(screen.getByText(/MedGemma 27B/)).toBeInTheDocument();
    expect(screen.getByText(/OLMo 32B Instruct/)).toBeInTheDocument();
  });

  it('shows "(optional)" label for optional models', async () => {
    const { ModelSelector } = await import('@/components/ModelSelector');
    render(<ModelSelector availableModels={availableModels} selectedModels={availableModels.slice(0, 3)} />);

    expect(screen.getByText('(optional)')).toBeInTheDocument();
  });

  it('shows green checkmark for reviewed models', async () => {
    const { ModelSelector } = await import('@/components/ModelSelector');
    const reviewedModels = new Set(['google/gemma-3-27b-it', 'google/gemma-3-4b-it']);

    const { container } = render(
      <ModelSelector
        availableModels={availableModels}
        selectedModels={availableModels.slice(0, 3)}
        reviewedModels={reviewedModels}
      />
    );

    // Should have 2 CheckCircle icons for reviewed models
    const checkIcons = container.querySelectorAll('.text-green-500');
    expect(checkIcons.length).toBe(2);
  });

  it('shows model count indicator', async () => {
    const { ModelSelector } = await import('@/components/ModelSelector');
    render(<ModelSelector availableModels={availableModels} selectedModels={availableModels.slice(0, 3)} />);

    // Should show count like "3 / 6"
    expect(screen.getByText(/\/ 6/)).toBeInTheDocument();
  });

  it('calls onChange when model is toggled', async () => {
    const { ModelSelector } = await import('@/components/ModelSelector');
    const onChange = vi.fn();
    render(<ModelSelector availableModels={availableModels} selectedModels={availableModels.slice(0, 3)} onChange={onChange} />);

    const user = userEvent.setup();
    // Click on a model button to toggle it
    const gemmaButton = screen.getByText(/MedGemma 27B/);
    await user.click(gemmaButton);

    expect(onChange).toHaveBeenCalled();
  });
});

// ============================================================
// ModelGrid Tests
// ============================================================
describe('ModelGrid', () => {
  it('shows "No models selected" when empty selection', async () => {
    const { ModelGrid } = await import('@/components/ModelGrid');
    const mockCase = {
      case_id: 'ncc_1',
      predictions: {},
    };

    render(<ModelGrid caseItem={mockCase as any} selectedModels={[]} />);
    expect(screen.getByText('No models selected.')).toBeInTheDocument();
  });
});
