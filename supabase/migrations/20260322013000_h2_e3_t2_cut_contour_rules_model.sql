-- H2-E3-T2: cut contour rules model
-- Scope: cut_contour_rules truth table for per-contour cutting rules within a rule set.
-- Owner-scope is inherited via cut_rule_set_id -> cut_rule_sets.owner_user_id.
-- Does NOT introduce rule matching, manufacturing profile binding, or snapshot changes.

create table if not exists app.cut_contour_rules (
  id uuid primary key default gen_random_uuid(),
  cut_rule_set_id uuid not null references app.cut_rule_sets(id) on delete cascade,
  contour_kind text not null check (contour_kind in ('outer', 'inner')),
  feature_class text not null default 'default',
  lead_in_type text not null default 'none' check (lead_in_type in ('none', 'line', 'arc')),
  lead_in_length_mm numeric(10,3) check (lead_in_length_mm is null or lead_in_length_mm > 0),
  lead_in_radius_mm numeric(10,3) check (lead_in_radius_mm is null or lead_in_radius_mm > 0),
  lead_out_type text not null default 'none' check (lead_out_type in ('none', 'line', 'arc')),
  lead_out_length_mm numeric(10,3) check (lead_out_length_mm is null or lead_out_length_mm > 0),
  lead_out_radius_mm numeric(10,3) check (lead_out_radius_mm is null or lead_out_radius_mm > 0),
  entry_side_policy text not null default 'auto',
  min_contour_length_mm numeric(10,3) check (min_contour_length_mm is null or min_contour_length_mm >= 0),
  max_contour_length_mm numeric(10,3) check (max_contour_length_mm is null or max_contour_length_mm >= 0),
  pierce_count integer not null default 1 check (pierce_count > 0),
  cut_direction text not null default 'cw',
  sort_order integer not null default 0,
  enabled boolean not null default true,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (min_contour_length_mm is null or max_contour_length_mm is null)
    or min_contour_length_mm <= max_contour_length_mm
  )
);

create index if not exists idx_cut_contour_rules_cut_rule_set_id
  on app.cut_contour_rules(cut_rule_set_id);

create index if not exists idx_cut_contour_rules_set_kind
  on app.cut_contour_rules(cut_rule_set_id, contour_kind);

-- RLS -------------------------------------------------------------------

alter table app.cut_contour_rules enable row level security;

drop policy if exists h2_e3_t2_cut_contour_rules_select_owner on app.cut_contour_rules;
create policy h2_e3_t2_cut_contour_rules_select_owner
on app.cut_contour_rules
for select
to authenticated
using (
  exists (
    select 1 from app.cut_rule_sets crs
    where crs.id = cut_contour_rules.cut_rule_set_id
      and crs.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e3_t2_cut_contour_rules_insert_owner on app.cut_contour_rules;
create policy h2_e3_t2_cut_contour_rules_insert_owner
on app.cut_contour_rules
for insert
to authenticated
with check (
  exists (
    select 1 from app.cut_rule_sets crs
    where crs.id = cut_contour_rules.cut_rule_set_id
      and crs.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e3_t2_cut_contour_rules_update_owner on app.cut_contour_rules;
create policy h2_e3_t2_cut_contour_rules_update_owner
on app.cut_contour_rules
for update
to authenticated
using (
  exists (
    select 1 from app.cut_rule_sets crs
    where crs.id = cut_contour_rules.cut_rule_set_id
      and crs.owner_user_id = app.current_user_id()
  )
)
with check (
  exists (
    select 1 from app.cut_rule_sets crs
    where crs.id = cut_contour_rules.cut_rule_set_id
      and crs.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e3_t2_cut_contour_rules_delete_owner on app.cut_contour_rules;
create policy h2_e3_t2_cut_contour_rules_delete_owner
on app.cut_contour_rules
for delete
to authenticated
using (
  exists (
    select 1 from app.cut_rule_sets crs
    where crs.id = cut_contour_rules.cut_rule_set_id
      and crs.owner_user_id = app.current_user_id()
  )
);

-- updated_at trigger ----------------------------------------------------

drop trigger if exists trg_cut_contour_rules_set_updated_at on app.cut_contour_rules;
create trigger trg_cut_contour_rules_set_updated_at
before update on app.cut_contour_rules
for each row execute function app.set_updated_at();
