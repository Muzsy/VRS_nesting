-- H2-E3-T1: cut rule set model
-- Scope: cut_rule_sets truth table + owner-scoped CRUD support.
-- Does NOT introduce cut_contour_rules, rule matching, or manufacturing profile FK binding.

create table if not exists app.cut_rule_sets (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  machine_code text,
  material_code text,
  thickness_mm numeric(10,3),
  version_no integer not null default 1,
  is_active boolean not null default true,
  notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(name)) > 0),
  check (machine_code is null or length(btrim(machine_code)) > 0),
  check (material_code is null or length(btrim(material_code)) > 0),
  check (thickness_mm is null or thickness_mm > 0),
  check (version_no > 0),
  unique (owner_user_id, name, version_no)
);

create index if not exists idx_cut_rule_sets_owner_user_id
  on app.cut_rule_sets(owner_user_id);

create index if not exists idx_cut_rule_sets_owner_name
  on app.cut_rule_sets(owner_user_id, name);

-- RLS -------------------------------------------------------------------

alter table app.cut_rule_sets enable row level security;

drop policy if exists h2_e3_t1_cut_rule_sets_select_owner on app.cut_rule_sets;
create policy h2_e3_t1_cut_rule_sets_select_owner
on app.cut_rule_sets
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e3_t1_cut_rule_sets_insert_owner on app.cut_rule_sets;
create policy h2_e3_t1_cut_rule_sets_insert_owner
on app.cut_rule_sets
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e3_t1_cut_rule_sets_update_owner on app.cut_rule_sets;
create policy h2_e3_t1_cut_rule_sets_update_owner
on app.cut_rule_sets
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e3_t1_cut_rule_sets_delete_owner on app.cut_rule_sets;
create policy h2_e3_t1_cut_rule_sets_delete_owner
on app.cut_rule_sets
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- updated_at trigger ----------------------------------------------------

drop trigger if exists trg_cut_rule_sets_set_updated_at on app.cut_rule_sets;
create trigger trg_cut_rule_sets_set_updated_at
before update on app.cut_rule_sets
for each row execute function app.set_updated_at();
