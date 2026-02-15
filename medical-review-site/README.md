# Medical Review Site

A web application for medical professionals to review LLM-generated therapy recommendations for kidney cancer (NCC) cases.

## Features

- **Multi-Doctor Support**: Each doctor has isolated reviews - no data overwrites
- **35 NCC Cases**: Renal cell carcinoma cases with ground truth therapy recommendations
- **6 LLM Models**: Compare predictions from different AI models
- **Bilingual**: German (DE) and English (EN) interface
- **Export**: Download reviews as CSV (per doctor or all)

## Tech Stack

- **Framework**: Next.js 16 with App Router
- **UI**: Shadcn/ui + Tailwind CSS
- **Storage**: Netlify Blobs (production) / Local JSON (development)
- **Language**: TypeScript

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npx tsx scripts/test-multi-doctor.ts

# Build for production
npm run build
```

## Deployment (Netlify)

1. Push to GitHub
2. Connect to Netlify
3. Netlify auto-detects Next.js and configures build
4. Reviews stored in Netlify Blobs (serverless KV storage)

### Environment

No environment variables required. The app auto-detects Netlify environment.

## Data Structure

```
src/data/
├── cases.json        # 35 NCC cases with predictions (706KB)
├── reviews.json      # Doctor reviews (starts empty, populated at runtime)
└── source/           # Original CSV data from model inference
    ├── gemma-3-27b-it_treatment_*.csv
    ├── medgemma-27b-text-it_treatment_*.csv
    └── ... (6 model result files)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/doctors` | GET | List all registered doctors |
| `/api/doctors` | POST | Register new doctor |
| `/api/reviews` | GET | Get reviews (filter by ?doctor, ?case, ?model) |
| `/api/reviews` | POST | Save a review |
| `/api/export` | GET | Download CSV (filter by ?doctor) |

## Review Data Model

Each review is uniquely keyed by: `${case_id}__${model_id}__${reviewer_name}`

```json
{
  "id": "ncc_1__gemma-3-27b-it__Dr. Schmidt",
  "case_id": "ncc_1",
  "model_id": "google/gemma-3-27b-it",
  "reviewer_name": "Dr. Schmidt",
  "therapy_acceptable_ra": true,
  "recommendation_exact_match": 85,
  "recommendation_patient_oriented": 90,
  "prediction_quality": 8,
  "timestamp": "2026-02-02T16:30:00Z"
}
```

## License

Private - Medical Research Use Only
