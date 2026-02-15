-- Supabase schema for medical-review-site
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor)

-- Reviews table
create table if not exists reviews (
  id text primary key,
  case_id text not null,
  model_id text not null,
  reviewer_name text not null,
  therapy_acceptable_ra boolean,
  recommendation_exact_match integer,
  recommendation_patient_oriented integer,
  prediction_quality integer,
  created_at timestamptz default now(),

  -- Each doctor gets one review per case+model
  unique (case_id, model_id, reviewer_name)
);

-- Indexes for common queries
create index if not exists idx_reviews_reviewer on reviews (reviewer_name);
create index if not exists idx_reviews_case on reviews (case_id);
create index if not exists idx_reviews_case_model on reviews (case_id, model_id);

-- Doctors table
create table if not exists doctors (
  name text primary key,
  created_at timestamptz default now()
);

-- Judge reviews table: doctor's assessment of the AI judge's evaluation
create table if not exists judge_reviews (
  id text primary key,
  case_id text not null,
  model_id text not null,
  reviewer_name text not null,
  judge_correct text not null,          -- 'agree' | 'disagree' | 'partial'
  judge_reasoning_quality integer,      -- 0-9 scale
  comment text,                         -- optional free text
  doctor_acceptable boolean,            -- doctor's blind review snapshot
  doctor_quality integer,               -- doctor's blind quality score
  judge_is_correct boolean,             -- judge's verdict snapshot
  judge_overall_score real,             -- judge's overall score snapshot
  created_at timestamptz default now(),
  unique (case_id, model_id, reviewer_name)
);

create index if not exists idx_judge_reviews_reviewer on judge_reviews (reviewer_name);
create index if not exists idx_judge_reviews_case on judge_reviews (case_id);
create index if not exists idx_judge_reviews_case_model on judge_reviews (case_id, model_id);

-- Disable RLS (this is an internal tool, no auth needed)
alter table reviews enable row level security;
alter table doctors enable row level security;
alter table judge_reviews enable row level security;

-- Allow all operations via anon key (no auth)
create policy "Allow all on reviews" on reviews for all using (true) with check (true);
create policy "Allow all on doctors" on doctors for all using (true) with check (true);
create policy "Allow all on judge_reviews" on judge_reviews for all using (true) with check (true);
