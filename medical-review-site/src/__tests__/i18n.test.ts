import { describe, it, expect } from 'vitest';

// Import the translations directly to test completeness
// We need to access the module internals, so we'll read the source
// and test the translation objects

describe('i18n translations', () => {
  // New keys added for the unreviewed filter feature
  const newKeys = [
    'cases.showUnreviewed',
    'cases.showAll',
    'cases.remaining',
    'cases.allReviewed',
    'cases.reviewedOf',
    'models.reviewed',
    'models.optional',
    'case.reviewProgress',
  ] as const;

  // We'll dynamically import the i18n module and inspect translations
  let deTranslations: Record<string, string>;
  let enTranslations: Record<string, string>;

  // Since the translations are embedded in the module, let's read them from the file
  it('can load the i18n module', async () => {
    // Read the raw file to extract translations
    const fs = await import('fs');
    const path = await import('path');
    const content = fs.readFileSync(
      path.resolve(__dirname, '../lib/i18n.tsx'),
      'utf-8'
    );

    // Extract German translations block
    const deMatch = content.match(/de:\s*\{([\s\S]*?)\n\s*\},\s*\n\s*en:/);
    const enMatch = content.match(/en:\s*\{([\s\S]*?)\n\s*\},?\s*\n\s*\};/);

    expect(deMatch).toBeTruthy();
    expect(enMatch).toBeTruthy();

    // Parse the key-value pairs
    const parseTranslations = (block: string): Record<string, string> => {
      const result: Record<string, string> = {};
      const regex = /['"]([^'"]+)['"]\s*:\s*['"]([^'"]*)['"]/g;
      let match;
      while ((match = regex.exec(block)) !== null) {
        result[match[1]] = match[2];
      }
      return result;
    };

    deTranslations = parseTranslations(deMatch![1]);
    enTranslations = parseTranslations(enMatch![1]);
  });

  describe('new feature translation keys', () => {
    for (const key of newKeys) {
      it(`has German translation for '${key}'`, () => {
        expect(deTranslations[key]).toBeDefined();
        expect(deTranslations[key].length).toBeGreaterThan(0);
      });

      it(`has English translation for '${key}'`, () => {
        expect(enTranslations[key]).toBeDefined();
        expect(enTranslations[key].length).toBeGreaterThan(0);
      });
    }
  });

  describe('translation parity', () => {
    it('German and English have the same keys', () => {
      const deKeys = new Set(Object.keys(deTranslations));
      const enKeys = new Set(Object.keys(enTranslations));

      const onlyInDe = [...deKeys].filter(k => !enKeys.has(k));
      const onlyInEn = [...enKeys].filter(k => !deKeys.has(k));

      expect(onlyInDe).toEqual([]);
      expect(onlyInEn).toEqual([]);
    });
  });

  describe('parameterized translations', () => {
    it('cases.remaining has {count} placeholder', () => {
      expect(deTranslations['cases.remaining']).toContain('{count}');
      expect(enTranslations['cases.remaining']).toContain('{count}');
    });

    it('cases.reviewedOf has {done} and {total} placeholders', () => {
      expect(deTranslations['cases.reviewedOf']).toContain('{done}');
      expect(deTranslations['cases.reviewedOf']).toContain('{total}');
      expect(enTranslations['cases.reviewedOf']).toContain('{done}');
      expect(enTranslations['cases.reviewedOf']).toContain('{total}');
    });

    it('case.reviewProgress has {done} and {total} placeholders', () => {
      expect(deTranslations['case.reviewProgress']).toContain('{done}');
      expect(deTranslations['case.reviewProgress']).toContain('{total}');
      expect(enTranslations['case.reviewProgress']).toContain('{done}');
      expect(enTranslations['case.reviewProgress']).toContain('{total}');
    });
  });
});
