import { describe, it, expect } from 'vitest';
import {
  REQUIRED_MODEL_IDS,
  OPTIONAL_MODEL_IDS,
  MODEL_DISPLAY_NAMES,
  getModelDisplayName,
  getScoreLevel,
} from '@/lib/types';

describe('REQUIRED_MODEL_IDS', () => {
  it('contains exactly 5 required models', () => {
    expect(REQUIRED_MODEL_IDS).toHaveLength(5);
  });

  it('includes MedGemma 27B', () => {
    expect(REQUIRED_MODEL_IDS).toContain('google/medgemma-27b-text-it');
  });

  it('includes Gemma 3 27B', () => {
    expect(REQUIRED_MODEL_IDS).toContain('google/gemma-3-27b-it');
  });

  it('includes OLMo 32B Think', () => {
    expect(REQUIRED_MODEL_IDS).toContain('allenai/Olmo-3.1-32B-Think');
  });

  it('includes Gemma 3 4B', () => {
    expect(REQUIRED_MODEL_IDS).toContain('google/gemma-3-4b-it');
  });

  it('includes Meditron3 7B', () => {
    expect(REQUIRED_MODEL_IDS).toContain('OpenMeditron/Meditron3-Qwen2.5-7B');
  });

  it('does NOT include OLMo 32B Instruct (that is optional)', () => {
    expect(REQUIRED_MODEL_IDS).not.toContain('allenai/Olmo-3.1-32B-Instruct');
  });
});

describe('OPTIONAL_MODEL_IDS', () => {
  it('is empty (all models are required)', () => {
    expect(OPTIONAL_MODEL_IDS).toHaveLength(0);
  });
});

describe('REQUIRED + OPTIONAL cover all known models', () => {
  it('every model in MODEL_DISPLAY_NAMES is either required or optional', () => {
    const allModelIds = Object.keys(MODEL_DISPLAY_NAMES);
    const classified = [
      ...REQUIRED_MODEL_IDS,
      ...OPTIONAL_MODEL_IDS,
    ] as string[];

    for (const modelId of allModelIds) {
      expect(classified).toContain(modelId);
    }
  });

  it('required and optional sets do not overlap', () => {
    const overlap = REQUIRED_MODEL_IDS.filter(m =>
      (OPTIONAL_MODEL_IDS as readonly string[]).includes(m)
    );
    expect(overlap).toHaveLength(0);
  });
});

describe('getModelDisplayName', () => {
  it('returns display name for known models', () => {
    expect(getModelDisplayName('google/gemma-3-27b-it')).toBe('Gemma 3 27B');
    expect(getModelDisplayName('google/medgemma-27b-text-it')).toBe('MedGemma 27B');
    expect(getModelDisplayName('allenai/Olmo-3.1-32B-Instruct')).toBe('OLMo 32B Instruct');
  });

  it('returns a derived name for unknown models', () => {
    const name = getModelDisplayName('some-org/some-model-name');
    expect(name).toBe('some model name');
  });

  it('replaces dashes with spaces when no slash present', () => {
    const name = getModelDisplayName('local-model');
    expect(name).toBe('local model');
  });
});

describe('getScoreLevel', () => {
  it('returns "high" for scores >= 0.7', () => {
    expect(getScoreLevel(0.7)).toBe('high');
    expect(getScoreLevel(0.95)).toBe('high');
    expect(getScoreLevel(1.0)).toBe('high');
  });

  it('returns "medium" for scores >= 0.4 and < 0.7', () => {
    expect(getScoreLevel(0.4)).toBe('medium');
    expect(getScoreLevel(0.5)).toBe('medium');
    expect(getScoreLevel(0.69)).toBe('medium');
  });

  it('returns "low" for scores < 0.4', () => {
    expect(getScoreLevel(0.0)).toBe('low');
    expect(getScoreLevel(0.2)).toBe('low');
    expect(getScoreLevel(0.39)).toBe('low');
  });
});
