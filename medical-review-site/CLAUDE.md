# CLAUDE.md — medical-review-site

## Quick Reference

```bash
npm run dev          # Start Next.js dev server (localhost:3000)
npm run build        # Production build
npm run build:data   # Rebuild src/data/cases.json from CSV/JSON sources
npm run build:all    # build:data then build
npm run test         # Vitest (jsdom, single run)
npm run test:watch   # Vitest in watch mode
npm run lint         # ESLint
```

## What This App Does

A Next.js 16 review tool where doctors evaluate LLM therapy predictions for renal cell carcinoma (NCC) cases. Two review flows exist:

1. **Doctor review** — rate each model's therapy prediction (acceptable? exact match? patient-oriented? quality score)
2. **Judge review** — evaluate how well an AI judge (GPT-5.2, MedGemma) assessed the model predictions, comparing the judge's verdict against the doctor's own review

## Architecture

### Data Pipeline

```
CSV files + JSON result files (../to_be_reviewed_results/, ../results/modal_treatment/)
  └─ scripts/build-data.ts  (run via `npm run build:data`)
       └─ src/data/cases.json  (static, checked into git)
            └─ src/lib/data.ts  (typed accessors: getAllCases, getCaseById, etc.)
```

`build-data.ts` merges three data sources:
- **CSVs** in `../to_be_reviewed_results/` — original model predictions (cases 1-35)
- **Per-case JSON** in `../results/modal_treatment/{model}/{run}/ncc_XX.json` — newer cases (36-69+), includes clinical context
- **Judge evaluation JSON** in the same results dirs (`judge_evaluation_*.json`) — multi-judge scores keyed by judge model ID
- **Doctor review XLSX** — pre-existing reviews for OLMo 32B Instruct

### Storage Layers

| What | Where | Module |
|------|-------|--------|
| Case data (read-only) | `src/data/cases.json` (static import) | `src/lib/data.ts` |
| Doctor reviews | Supabase `reviews` table | `src/lib/server-storage.ts` |
| Judge reviews | Supabase `judge_reviews` table | `src/lib/server-storage.ts` |
| Session prefs (reviewer name, selected models) | `localStorage` | `src/lib/storage.ts` |

**Supabase** is the persistence backend. The client is created in `server-storage.ts` using `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars.

Review IDs are deterministic composites: `{case_id}__{model_id}__{reviewer_name}` (doctor reviews) or `{case_id}__{model_id}__{reviewer_name}__{judge_model}` (judge reviews). All writes use upsert with `onConflict: 'id'`.

### API Routes (Next.js Route Handlers)

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/reviews` | GET, POST | Fetch/save doctor reviews (single or batch) |
| `/api/judge-reviews` | GET, POST | Fetch/save judge reviews (batch) |
| `/api/doctors` | GET, POST | List/register doctors |
| `/api/export` | GET | CSV export of doctor reviews |
| `/api/export/judge` | GET | CSV export of judge reviews |
| `/api/health` | GET | Health check |

### Client-Side API Layer

`src/lib/api.ts` — fetch wrappers for all API routes. `src/lib/storage.ts` re-exports these and adds localStorage helpers for session preferences.

`src/lib/save-queue.ts` — serializes concurrent save operations to prevent lost updates.

### Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `src/app/page.tsx` | Home — doctor selector, review count, CSV export |
| `/cases` | `src/app/cases/page.tsx` | Case list with search/filter |
| `/cases/[id]` | `src/app/cases/[id]/page.tsx` | Case detail — model predictions + doctor review forms |
| `/judge-review/[id]` | `src/app/judge-review/[id]/page.tsx` | Judge review — evaluate AI judge assessments |
| `/models` | `src/app/models/page.tsx` | Model comparison dashboard |

### i18n

`src/lib/i18n.tsx` — client-side German/English toggle using React Context + `useSyncExternalStore`. Default language is German (`de`). All UI strings use `t('key.name')` with `{param}` interpolation. Language preference stored in `localStorage`.

## Key Patterns

- **Path alias**: `@/*` maps to `./src/*`
- **UI components**: Radix UI primitives in `src/components/ui/` (shadcn/ui style with `class-variance-authority` + `tailwind-merge`)
- **Styling**: Tailwind CSS v4 with `tw-animate-css`
- **Charts**: Recharts for model comparison visualizations
- **Constants in types.ts**: `DEFAULT_JUDGE_ID`, `JUDGE_MODEL_IDS`, `REQUIRED_MODEL_IDS`, `MODEL_DISPLAY_NAMES` — update these when adding new models or judges
- **Dual JSON schema support**: Types handle both v1.0 and v1.1 NCC case schemas (e.g., `wirkstoff` vs `wirkstoff_oder_klasse`, `datum` vs `datum_start`)

## Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL      # Supabase project URL
NEXT_PUBLIC_SUPABASE_ANON_KEY # Supabase anon/publishable key
```

## Deployment

Deployed on **Netlify** with `@netlify/plugin-nextjs`. Build command: `npm run build`. Node 20.
