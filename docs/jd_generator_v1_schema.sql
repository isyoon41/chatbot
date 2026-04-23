-- JD Generator v1 PostgreSQL Schema
-- Assumptions:
--   * PostgreSQL 16+
--   * pgvector installed
--   * Multi-tenant SaaS, but source catalog is global
--   * Embedding dimension 1536 is a placeholder; adjust if your model differs

create extension if not exists pgcrypto;
create extension if not exists citext;
create extension if not exists vector;

create type source_name_enum as enum ('ncs', 'esco', 'onet', 'digcomp', 'sfia');
create type sync_mode_enum as enum ('full', 'incremental');
create type sync_status_enum as enum ('queued', 'running', 'succeeded', 'failed', 'partial');
create type tenant_role_enum as enum ('admin', 'hr_architect', 'reviewer', 'viewer');
create type entity_status_enum as enum ('draft', 'active', 'archived');
create type decision_status_enum as enum ('pending', 'approved', 'rejected', 'merged');
create type jd_status_enum as enum ('draft', 'in_review', 'approved', 'rejected', 'archived');
create type approval_action_enum as enum ('submit', 'approve', 'reject', 'request_changes');
create type export_format_enum as enum ('docx', 'pdf');
create type export_status_enum as enum ('queued', 'running', 'completed', 'failed');

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create table tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug citext not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table users (
  id uuid primary key default gen_random_uuid(),
  email citext not null unique,
  display_name text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table tenant_memberships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role tenant_role_enum not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, user_id)
);

create table org_units (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  parent_id uuid references org_units(id) on delete set null,
  name text not null,
  code text not null,
  depth integer not null default 0 check (depth >= 0),
  path text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, code)
);

create table source_registry (
  source_name source_name_enum primary key,
  enabled boolean not null default true,
  license_mode text,
  default_sync_mode sync_mode_enum not null default 'incremental',
  sync_interval_minutes integer not null default 1440 check (sync_interval_minutes > 0),
  notes text,
  updated_at timestamptz not null default now()
);

insert into source_registry (source_name, enabled, license_mode)
values
  ('ncs', true, 'public'),
  ('esco', true, 'public'),
  ('onet', true, 'registered'),
  ('digcomp', true, 'public_structured_data'),
  ('sfia', false, 'licensed')
on conflict do nothing;

create table source_sync_runs (
  id uuid primary key default gen_random_uuid(),
  source_name source_name_enum not null references source_registry(source_name),
  sync_mode sync_mode_enum not null,
  status sync_status_enum not null default 'queued',
  started_at timestamptz,
  finished_at timestamptz,
  items_fetched integer not null default 0 check (items_fetched >= 0),
  items_inserted integer not null default 0 check (items_inserted >= 0),
  items_updated integer not null default 0 check (items_updated >= 0),
  error_message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table source_items (
  id uuid primary key default gen_random_uuid(),
  source_name source_name_enum not null references source_registry(source_name),
  source_version text not null,
  raw_id text not null,
  item_type text not null,
  locale text not null default 'ko',
  title text,
  normalized_text text,
  raw_payload jsonb not null,
  content_hash text not null,
  license_flag boolean not null default false,
  embedding vector(1536),
  retrieved_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_name, source_version, raw_id)
);

create table canonical_roles (
  id uuid primary key default gen_random_uuid(),
  role_key text not null unique,
  family text,
  domain text,
  title_ko text not null,
  title_en text,
  summary text,
  embedding vector(1536),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table canonical_role_aliases (
  id uuid primary key default gen_random_uuid(),
  canonical_role_id uuid not null references canonical_roles(id) on delete cascade,
  alias text not null,
  locale text not null default 'ko',
  alias_type text not null default 'title',
  created_at timestamptz not null default now(),
  unique (canonical_role_id, alias, locale)
);

create table canonical_tasks (
  id uuid primary key default gen_random_uuid(),
  task_key text not null unique,
  label_ko text not null,
  label_en text,
  description text,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table canonical_skills (
  id uuid primary key default gen_random_uuid(),
  skill_key text not null unique,
  label_ko text not null,
  label_en text,
  skill_type text not null, -- technical | behavioral | digital | governance | tool
  description text,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table canonical_knowledge (
  id uuid primary key default gen_random_uuid(),
  knowledge_key text not null unique,
  label_ko text not null,
  label_en text,
  description text,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table canonical_tools (
  id uuid primary key default gen_random_uuid(),
  tool_key text not null unique,
  label text not null,
  category text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table canonical_role_tasks (
  canonical_role_id uuid not null references canonical_roles(id) on delete cascade,
  canonical_task_id uuid not null references canonical_tasks(id) on delete cascade,
  importance_score numeric(5,4) not null default 0.5000 check (importance_score >= 0 and importance_score <= 1),
  is_required boolean not null default true,
  primary key (canonical_role_id, canonical_task_id)
);

create table canonical_role_skills (
  canonical_role_id uuid not null references canonical_roles(id) on delete cascade,
  canonical_skill_id uuid not null references canonical_skills(id) on delete cascade,
  importance_score numeric(5,4) not null default 0.5000 check (importance_score >= 0 and importance_score <= 1),
  is_required boolean not null default true,
  primary key (canonical_role_id, canonical_skill_id)
);

create table canonical_role_knowledge (
  canonical_role_id uuid not null references canonical_roles(id) on delete cascade,
  canonical_knowledge_id uuid not null references canonical_knowledge(id) on delete cascade,
  importance_score numeric(5,4) not null default 0.5000 check (importance_score >= 0 and importance_score <= 1),
  is_required boolean not null default true,
  primary key (canonical_role_id, canonical_knowledge_id)
);

create table canonical_role_tools (
  canonical_role_id uuid not null references canonical_roles(id) on delete cascade,
  canonical_tool_id uuid not null references canonical_tools(id) on delete cascade,
  importance_score numeric(5,4) not null default 0.5000 check (importance_score >= 0 and importance_score <= 1),
  is_required boolean not null default false,
  primary key (canonical_role_id, canonical_tool_id)
);

create table canonical_links (
  id uuid primary key default gen_random_uuid(),
  source_item_id uuid not null references source_items(id) on delete cascade,
  target_type text not null check (target_type in ('role', 'task', 'skill', 'knowledge', 'tool')),
  target_id uuid not null,
  relation_type text not null default 'derived_from',
  confidence numeric(5,4) not null default 0.7000 check (confidence >= 0 and confidence <= 1),
  created_at timestamptz not null default now()
);

create table company_roles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  org_unit_id uuid references org_units(id) on delete set null,
  title_ko text not null,
  title_en text,
  family text,
  domain text,
  status entity_status_enum not null default 'draft',
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table role_input_snapshots (
  id uuid primary key default gen_random_uuid(),
  company_role_id uuid not null references company_roles(id) on delete cascade,
  snapshot_no integer not null check (snapshot_no > 0),
  mission text,
  deliverables jsonb not null default '[]'::jsonb,
  recurring_tasks jsonb not null default '[]'::jsonb,
  tools jsonb not null default '[]'::jsonb,
  stakeholders jsonb not null default '[]'::jsonb,
  seniority_hint text,
  notes text,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (company_role_id, snapshot_no)
);

create table mapping_candidates (
  id uuid primary key default gen_random_uuid(),
  company_role_id uuid not null references company_roles(id) on delete cascade,
  canonical_role_id uuid not null references canonical_roles(id) on delete cascade,
  score_total numeric(5,4) not null check (score_total >= 0 and score_total <= 1),
  score_breakdown jsonb not null default '{}'::jsonb,
  source_mix jsonb not null default '[]'::jsonb,
  rationale text,
  decision_status decision_status_enum not null default 'pending',
  is_primary boolean not null default false,
  decided_by uuid references users(id) on delete set null,
  decided_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_role_id, canonical_role_id)
);

create table kpi_templates (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references tenants(id) on delete cascade,
  family text,
  domain text,
  metric_name text not null,
  metric_type text not null, -- outcome | process | quality | risk | capability
  formula_template text,
  data_source_hint text,
  review_cycle text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table jd_versions (
  id uuid primary key default gen_random_uuid(),
  company_role_id uuid not null references company_roles(id) on delete cascade,
  version_no integer not null check (version_no > 0),
  generator_profile text not null,
  language_code text not null default 'ko',
  source_bundle jsonb not null default '[]'::jsonb,
  jd_json jsonb not null,
  status jd_status_enum not null default 'draft',
  created_by uuid references users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_role_id, version_no)
);

create table jd_sections (
  id uuid primary key default gen_random_uuid(),
  jd_version_id uuid not null references jd_versions(id) on delete cascade,
  section_key text not null,
  section_title text not null,
  section_order integer not null default 0,
  content_md text not null,
  is_locked boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (jd_version_id, section_key)
);

create table jd_evidences (
  id uuid primary key default gen_random_uuid(),
  jd_section_id uuid not null references jd_sections(id) on delete cascade,
  source_item_id uuid not null references source_items(id) on delete restrict,
  evidence_type text not null, -- task | skill | knowledge | level | company_input
  snippet text,
  confidence numeric(5,4) not null default 0.7000 check (confidence >= 0 and confidence <= 1),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table kpi_instances (
  id uuid primary key default gen_random_uuid(),
  jd_version_id uuid not null references jd_versions(id) on delete cascade,
  kpi_template_id uuid references kpi_templates(id) on delete set null,
  sort_order integer not null default 0,
  name text not null,
  metric_type text not null,
  definition text,
  formula text,
  data_source text,
  review_cycle text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table approval_logs (
  id uuid primary key default gen_random_uuid(),
  jd_version_id uuid not null references jd_versions(id) on delete cascade,
  actor_user_id uuid references users(id) on delete set null,
  action approval_action_enum not null,
  comment text,
  created_at timestamptz not null default now()
);

create table feedback_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  company_role_id uuid references company_roles(id) on delete cascade,
  mapping_candidate_id uuid references mapping_candidates(id) on delete cascade,
  jd_version_id uuid references jd_versions(id) on delete cascade,
  actor_user_id uuid references users(id) on delete set null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table export_jobs (
  id uuid primary key default gen_random_uuid(),
  jd_version_id uuid not null references jd_versions(id) on delete cascade,
  requested_by uuid references users(id) on delete set null,
  format export_format_enum not null,
  status export_status_enum not null default 'queued',
  file_path text,
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

-- Triggers
create trigger trg_tenants_updated_at
before update on tenants
for each row execute function set_updated_at();

create trigger trg_users_updated_at
before update on users
for each row execute function set_updated_at();

create trigger trg_org_units_updated_at
before update on org_units
for each row execute function set_updated_at();

create trigger trg_source_items_updated_at
before update on source_items
for each row execute function set_updated_at();

create trigger trg_canonical_roles_updated_at
before update on canonical_roles
for each row execute function set_updated_at();

create trigger trg_canonical_tasks_updated_at
before update on canonical_tasks
for each row execute function set_updated_at();

create trigger trg_canonical_skills_updated_at
before update on canonical_skills
for each row execute function set_updated_at();

create trigger trg_canonical_knowledge_updated_at
before update on canonical_knowledge
for each row execute function set_updated_at();

create trigger trg_canonical_tools_updated_at
before update on canonical_tools
for each row execute function set_updated_at();

create trigger trg_company_roles_updated_at
before update on company_roles
for each row execute function set_updated_at();

create trigger trg_mapping_candidates_updated_at
before update on mapping_candidates
for each row execute function set_updated_at();

create trigger trg_kpi_templates_updated_at
before update on kpi_templates
for each row execute function set_updated_at();

create trigger trg_jd_versions_updated_at
before update on jd_versions
for each row execute function set_updated_at();

create trigger trg_jd_sections_updated_at
before update on jd_sections
for each row execute function set_updated_at();

create trigger trg_kpi_instances_updated_at
before update on kpi_instances
for each row execute function set_updated_at();

-- Useful indexes
create index idx_org_units_tenant_parent on org_units (tenant_id, parent_id);
create index idx_source_sync_runs_source_status on source_sync_runs (source_name, status, created_at desc);
create index idx_source_items_source_type on source_items (source_name, item_type, retrieved_at desc);
create index idx_source_items_content_hash on source_items (content_hash);
create index idx_canonical_roles_family_domain on canonical_roles (family, domain);
create index idx_canonical_role_aliases_alias on canonical_role_aliases using gin (to_tsvector('simple', alias));
create index idx_company_roles_tenant_org on company_roles (tenant_id, org_unit_id, status);
create index idx_role_input_snapshots_role_created on role_input_snapshots (company_role_id, created_at desc);
create index idx_mapping_candidates_role_status on mapping_candidates (company_role_id, decision_status, score_total desc);
create index idx_jd_versions_role_status on jd_versions (company_role_id, status, version_no desc);
create index idx_jd_sections_version_order on jd_sections (jd_version_id, section_order);
create index idx_jd_evidences_section on jd_evidences (jd_section_id);
create index idx_kpi_instances_version_order on kpi_instances (jd_version_id, sort_order);
create index idx_approval_logs_version_created on approval_logs (jd_version_id, created_at desc);
create index idx_feedback_events_role_created on feedback_events (company_role_id, created_at desc);
create index idx_export_jobs_version_status on export_jobs (jd_version_id, status, created_at desc);
create index idx_source_items_text_search on source_items using gin (
  to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(normalized_text, ''))
);

-- Optional: enable after enough rows accumulate and your pgvector version supports HNSW.
-- create index idx_source_items_embedding_hnsw on source_items using hnsw (embedding vector_cosine_ops);
-- create index idx_canonical_roles_embedding_hnsw on canonical_roles using hnsw (embedding vector_cosine_ops);

-- Optional view for currently approved JD per company role
create or replace view v_current_approved_jd as
select distinct on (j.company_role_id)
  j.company_role_id,
  j.id as jd_version_id,
  j.version_no,
  j.approved_at,
  j.jd_json
from jd_versions j
where j.status = 'approved'
order by j.company_role_id, j.version_no desc;
