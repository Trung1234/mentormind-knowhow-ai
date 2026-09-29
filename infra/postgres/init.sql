
-- spec 01 FR-05: extensions the vector store (spec 05) needs, created on first start.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- MentorMind / DENSO Factory Hacks
-- PostgreSQL + pgvector schema v1.1
-- Goal: Case -> Evidence -> Knowledge -> Expert Review -> Approved Knowledge -> RAG
--
-- IMPORTANT:
-- 1) This migration assumes pgvector embedding dimension = 1024.
--    If your embedding model uses another dimension, change vector(1024)
--    BEFORE running this migration.
-- 2) Runtime architecture:
--    Frontend -> FastAPI -> PostgreSQL.
--    The frontend must not connect directly to PostgreSQL.
-- 3) This file is intended for Docker/PostgreSQL bootstrap, e.g.
--    /docker-entrypoint-initdb.d/init.sql. It runs automatically only when
--    the PostgreSQL data directory is initialized for the first time.

begin;

create extension if not exists pgcrypto;
create extension if not exists vector;
create extension if not exists unaccent;

-- =========================================================
-- 0. Common updated_at trigger
-- =========================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =========================================================
-- 1. User / Expert profile
-- =========================================================
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  employee_code text,
  role text not null default 'engineer'
    check (role in ('admin','expert','engineer','reviewer')),
  department text,
  expertise jsonb not null default '[]'::jsonb,
  is_demo boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =========================================================
-- 2. Manufacturing process / station
-- =========================================================
create table if not exists public.processes (
  id uuid primary key default gen_random_uuid(),
  process_code text not null unique,
  process_name text not null,
  department text,
  station_code text,
  description text,
  status text not null default 'active'
    check (status in ('active','inactive','archived')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =========================================================
-- 3. Knowledge case = one captured work/interview/problem-solving case
-- =========================================================
create table if not exists public.knowledge_cases (
  id uuid primary key default gen_random_uuid(),
  case_code text not null unique,
  process_id uuid references public.processes(id) on delete set null,
  expert_id uuid references public.profiles(id) on delete set null,

  title text not null,
  description text,

  capture_mode text not null default 'document_only'
    check (capture_mode in (
      'work_video',
      'expert_interview',
      'review_session',
      'document_only',
      'mixed'
    )),

  scenario_type text not null default 'normal'
    check (scenario_type in (
      'normal',
      'exception',
      'abnormal',
      'troubleshooting',
      'quality_issue',
      'unknown'
    )),

  lot_code text,
  part_code text,
  equipment_code text,

  source_label text not null default 'public'
    check (source_label in ('public','denso_internal','partner')),
  data_classification text not null default 'public'
    check (data_classification in ('public','internal','confidential','restricted')),

  status text not null default 'draft'
    check (status in ('draft','processing','in_review','verified','rejected','archived')),

  started_at timestamptz,
  ended_at timestamptz,

  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =========================================================
-- 4. Raw/derived assets: video/audio/PDF/XLSX/image/log/CSV...
--    A row may represent a public source not yet copied into project/object storage.
-- =========================================================
create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  asset_code text unique,
  file_name text not null,
  asset_type text not null
    check (asset_type in (
      'video','audio','image','pdf','xlsx','csv','document','drawing','machine_log','sensor_data','other'
    )),
  mime_type text,

  source_label text not null default 'public'
    check (source_label in ('public','denso_internal','partner')),
  data_classification text not null default 'public'
    check (data_classification in ('public','internal','confidential','restricted')),

  availability_status text not null default 'available'
    check (availability_status in ('available','restricted','unavailable')),

  origin_url text,
  storage_bucket text,
  storage_path text,

  language_code text,
  has_transcript boolean not null default false,
  transcript_language_code text,

  sha256 text,
  file_size_bytes bigint,
  duration_ms bigint,

  license_note text,
  description text,
  metadata jsonb not null default '{}'::jsonb,

  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint asset_has_location
    check (origin_url is not null or storage_path is not null)
);

-- A reusable SOP/drawing can support many cases.
create table if not exists public.case_assets (
  case_id uuid not null references public.knowledge_cases(id) on delete cascade,
  asset_id uuid not null references public.assets(id) on delete cascade,
  relation_type text not null default 'evidence'
    check (relation_type in ('evidence','reference','input','output','derived')),
  note text,
  created_at timestamptz not null default now(),
  primary key (case_id, asset_id, relation_type)
);

-- =========================================================
-- 5. Video/audio transcript with timestamps
-- =========================================================
create table if not exists public.transcript_segments (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  segment_index integer not null,
  start_ms bigint not null default 0 check (start_ms >= 0),
  end_ms bigint check (end_ms is null or end_ms >= start_ms),
  speaker_label text,
  speaker_profile_id uuid references public.profiles(id) on delete set null,
  language_code text,
  text text not null,
  confidence numeric(5,4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  source text not null default 'asr'
    check (source in ('asr','manual','subtitle','imported')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(asset_id, segment_index)
);

-- =========================================================
-- 6. Parsed/OCR document chunks + hybrid retrieval
-- =========================================================
create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  chunk_index integer not null,
  page_number integer,
  section_title text,
  content text not null,
  bbox jsonb,
  parser_name text,
  parser_version text,
  embedding vector(1024),
  metadata jsonb not null default '{}'::jsonb,
  search_tsv tsvector generated always as (
    to_tsvector('simple', coalesce(section_title,'') || ' ' || coalesce(content,''))
  ) stored,
  created_at timestamptz not null default now(),
  unique(asset_id, chunk_index)
);

-- =========================================================
-- 7. Signals the expert was observing
-- =========================================================
create table if not exists public.case_signals (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.knowledge_cases(id) on delete cascade,
  asset_id uuid references public.assets(id) on delete set null,

  observed_at_ms bigint check (observed_at_ms is null or observed_at_ms >= 0),
  signal_type text not null,
  signal_name text not null,

  value_text text,
  value_number double precision,
  unit text,

  is_abnormal boolean,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- =========================================================
-- 8. Final outcome / confirmed result of a case
-- =========================================================
create table if not exists public.case_outcomes (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.knowledge_cases(id) on delete cascade,

  result text,
  final_cause text,
  final_action text,
  quality_result text,
  resolved boolean,
  reoccurred boolean,

  metrics jsonb not null default '{}'::jsonb,

  verified_by uuid references public.profiles(id) on delete set null,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique(case_id)
);

-- =========================================================
-- 9. Canonical reusable knowledge
--    Core model: Context + Observation + Reasoning + Decision/Action
--                + Exception + Outcome + Provenance
-- =========================================================
create table if not exists public.knowledge_units (
  id uuid primary key default gen_random_uuid(),
  knowledge_code text not null unique,

  case_id uuid references public.knowledge_cases(id) on delete set null,
  process_id uuid references public.processes(id) on delete set null,
  contributor_id uuid references public.profiles(id) on delete set null,

  knowledge_type text not null default 'work_step'
    check (knowledge_type in (
      'work_step',
      'rule',
      'quality_criterion',
      'diagnostic',
      'exception',
      'troubleshooting',
      'lesson_learned'
    )),

  step_order integer,
  title text not null,

  context text,
  observation text,
  conditions jsonb not null default '[]'::jsonb,

  action text,
  reasoning text,
  decision text,

  exceptions jsonb not null default '[]'::jsonb,
  pass_criteria text,
  expected_outcome text,

  reason_source text
    check (reason_source is null or reason_source in (
      'expert_verbal',
      'expert_written',
      'document',
      'historical_case',
      'model_inference',
      'unknown'
    )),

  confidence numeric(5,4)
    check (confidence is null or (confidence >= 0 and confidence <= 1)),

  generated_by text not null default 'human'
    check (generated_by in ('human','ai','hybrid')),
  model_info jsonb not null default '{}'::jsonb,

  status text not null default 'draft'
    check (status in ('draft','in_review','approved','rejected','archived')),

  version integer not null default 1 check (version > 0),

  embedding vector(1024),

  search_tsv tsvector generated always as (
    to_tsvector(
      'simple',
      coalesce(title,'') || ' ' ||
      coalesce(context,'') || ' ' ||
      coalesce(observation,'') || ' ' ||
      coalesce(action,'') || ' ' ||
      coalesce(reasoning,'') || ' ' ||
      coalesce(decision,'') || ' ' ||
      coalesce(pass_criteria,'') || ' ' ||
      coalesce(expected_outcome,'')
    )
  ) stored,

  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =========================================================
-- 10. Provenance: each knowledge claim points back to evidence
-- =========================================================
create table if not exists public.knowledge_evidence (
  id uuid primary key default gen_random_uuid(),
  knowledge_unit_id uuid not null references public.knowledge_units(id) on delete cascade,
  asset_id uuid not null references public.assets(id) on delete cascade,

  transcript_segment_id uuid references public.transcript_segments(id) on delete set null,
  document_chunk_id uuid references public.document_chunks(id) on delete set null,
  signal_id uuid references public.case_signals(id) on delete set null,

  start_ms bigint,
  end_ms bigint,
  page_number integer,

  evidence_role text not null default 'support'
    check (evidence_role in ('support','context','reason','exception','outcome','conflict')),

  excerpt text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),

  constraint valid_evidence_time
    check (
      start_ms is null
      or end_ms is null
      or end_ms >= start_ms
    )
);

-- =========================================================
-- 11. Expert verification
-- =========================================================
create table if not exists public.knowledge_reviews (
  id uuid primary key default gen_random_uuid(),
  knowledge_unit_id uuid not null references public.knowledge_units(id) on delete cascade,
  reviewer_id uuid references public.profiles(id) on delete set null,

  decision text not null
    check (decision in ('approve','reject','request_change')),

  comment text,
  corrected_payload jsonb,
  error_tags jsonb not null default '[]'::jsonb,

  reviewed_at timestamptz not null default now()
);

-- Snapshots preserve audit/version history.
create table if not exists public.knowledge_versions (
  id uuid primary key default gen_random_uuid(),
  knowledge_unit_id uuid not null references public.knowledge_units(id) on delete cascade,
  version integer not null,
  snapshot jsonb not null,
  change_note text,
  changed_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  unique(knowledge_unit_id, version)
);

-- =========================================================
-- 12. Evaluation / Golden Set
-- =========================================================
create table if not exists public.evaluation_questions (
  id uuid primary key default gen_random_uuid(),
  qid text not null unique,
  process_id uuid references public.processes(id) on delete set null,

  question_type text not null
    check (question_type in ('how','why','exception','relation','out_of_scope')),
  question text not null,
  expected_answer text,
  expected_behavior text not null default 'answer'
    check (expected_behavior in ('answer','abstain')),

  expected_citations jsonb not null default '[]'::jsonb,
  tags jsonb not null default '[]'::jsonb,

  source_label text not null default 'public'
    check (source_label in ('public','denso_internal','partner')),
  active boolean not null default true,

  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.evaluation_runs (
  id uuid primary key default gen_random_uuid(),
  run_name text not null,
  model_name text,
  retriever_name text,
  config jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  created_by uuid references public.profiles(id) on delete set null
);

create table if not exists public.evaluation_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.evaluation_runs(id) on delete cascade,
  question_id uuid not null references public.evaluation_questions(id) on delete cascade,

  answer text,
  citations jsonb not null default '[]'::jsonb,

  retrieval_metrics jsonb not null default '{}'::jsonb,
  answer_metrics jsonb not null default '{}'::jsonb,

  passed boolean,
  latency_ms integer,
  error_tag text,

  created_at timestamptz not null default now(),
  unique(run_id, question_id)
);

-- =========================================================
-- 13. Indexes
-- =========================================================
create index if not exists idx_cases_process
  on public.knowledge_cases(process_id);

create index if not exists idx_cases_status
  on public.knowledge_cases(status);

create index if not exists idx_assets_type
  on public.assets(asset_type);

create index if not exists idx_assets_source
  on public.assets(source_label, data_classification);

create unique index if not exists idx_assets_sha256_unique
  on public.assets(sha256)
  where sha256 is not null;

create index if not exists idx_transcript_asset_time
  on public.transcript_segments(asset_id, start_ms);

create index if not exists idx_doc_chunks_asset
  on public.document_chunks(asset_id, chunk_index);

create index if not exists idx_doc_chunks_fts
  on public.document_chunks using gin(search_tsv);

create index if not exists idx_doc_chunks_embedding_hnsw
  on public.document_chunks
  using hnsw (embedding vector_cosine_ops)
  where embedding is not null;

create index if not exists idx_signals_case
  on public.case_signals(case_id, observed_at_ms);

create index if not exists idx_knowledge_process_status
  on public.knowledge_units(process_id, status);

create index if not exists idx_knowledge_case
  on public.knowledge_units(case_id);

create index if not exists idx_knowledge_fts
  on public.knowledge_units using gin(search_tsv);

create index if not exists idx_knowledge_embedding_hnsw
  on public.knowledge_units
  using hnsw (embedding vector_cosine_ops)
  where embedding is not null;

create index if not exists idx_evidence_knowledge
  on public.knowledge_evidence(knowledge_unit_id);

create index if not exists idx_reviews_knowledge
  on public.knowledge_reviews(knowledge_unit_id, reviewed_at desc);

-- =========================================================
-- 14. updated_at triggers
-- =========================================================
drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists trg_processes_updated_at on public.processes;
create trigger trg_processes_updated_at
before update on public.processes
for each row execute function public.set_updated_at();

drop trigger if exists trg_cases_updated_at on public.knowledge_cases;
create trigger trg_cases_updated_at
before update on public.knowledge_cases
for each row execute function public.set_updated_at();

drop trigger if exists trg_assets_updated_at on public.assets;
create trigger trg_assets_updated_at
before update on public.assets
for each row execute function public.set_updated_at();

drop trigger if exists trg_outcomes_updated_at on public.case_outcomes;
create trigger trg_outcomes_updated_at
before update on public.case_outcomes
for each row execute function public.set_updated_at();

drop trigger if exists trg_knowledge_updated_at on public.knowledge_units;
create trigger trg_knowledge_updated_at
before update on public.knowledge_units
for each row execute function public.set_updated_at();

drop trigger if exists trg_eval_questions_updated_at on public.evaluation_questions;
create trigger trg_eval_questions_updated_at
before update on public.evaluation_questions
for each row execute function public.set_updated_at();

-- =========================================================
-- 15. Access-control boundary
-- =========================================================
-- This bootstrap targets plain PostgreSQL, not Supabase.
-- Authorization is enforced by the FastAPI application layer for the MVP.
-- Do not expose PostgreSQL directly to the frontend.

-- =========================================================
-- 16. Convenience views
-- =========================================================
create or replace view public.approved_knowledge_view as
select
  ku.id,
  ku.knowledge_code,
  p.process_code,
  p.process_name,
  ku.knowledge_type,
  ku.title,
  ku.context,
  ku.observation,
  ku.conditions,
  ku.action,
  ku.reasoning,
  ku.decision,
  ku.exceptions,
  ku.pass_criteria,
  ku.expected_outcome,
  ku.reason_source,
  ku.confidence,
  ku.version,
  ku.updated_at
from public.knowledge_units ku
left join public.processes p on p.id = ku.process_id
where ku.status = 'approved';

-- =========================================================
-- 17. File/object storage
-- =========================================================
-- Plain PostgreSQL does not provide Supabase Storage buckets.
-- Binary files stay outside PostgreSQL (local/object storage).
-- The assets table stores origin_url / storage_bucket / storage_path metadata.

commit;

