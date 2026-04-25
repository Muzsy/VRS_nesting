-- New Run Wizard Step2 Strategy T1
-- run_configs contract extension:
--   - run_strategy_profile_version_id
--   - solver_config_overrides_jsonb
-- plus public.run_configs bridge update.

alter table app.run_configs
  add column if not exists run_strategy_profile_version_id uuid;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'fk_run_configs_run_strategy_profile_version_id'
      and conrelid = 'app.run_configs'::regclass
  ) then
    alter table app.run_configs
      add constraint fk_run_configs_run_strategy_profile_version_id
      foreign key (run_strategy_profile_version_id)
      references app.run_strategy_profile_versions(id)
      on delete set null;
  end if;
end
$$;

alter table app.run_configs
  add column if not exists solver_config_overrides_jsonb jsonb;

update app.run_configs
set solver_config_overrides_jsonb = '{}'::jsonb
where solver_config_overrides_jsonb is null;

alter table app.run_configs
  alter column solver_config_overrides_jsonb set default '{}'::jsonb;

alter table app.run_configs
  alter column solver_config_overrides_jsonb set not null;

create index if not exists idx_run_configs_run_strategy_profile_version_id
  on app.run_configs(run_strategy_profile_version_id);

create or replace view public.run_configs as
select
  rc.id,
  rc.project_id,
  rc.created_by,
  rc.name,
  rc.schema_version,
  rc.seed,
  rc.time_limit_s,
  rc.spacing_mm,
  rc.margin_mm,
  rc.stock_file_id,
  rc.parts_config,
  rc.created_at,
  rc.run_strategy_profile_version_id,
  rc.solver_config_overrides_jsonb
from app.run_configs rc;

create or replace function public.run_configs_view_iud()
returns trigger
language plpgsql
security definer
set search_path = app
as $$
declare
  v_row app.run_configs%rowtype;
begin
  if tg_op = 'INSERT' then
    if not app.is_project_owner(new.project_id) then
      raise exception 'project_forbidden' using errcode = '42501';
    end if;

    insert into app.run_configs (
      project_id,
      created_by,
      name,
      schema_version,
      seed,
      time_limit_s,
      spacing_mm,
      margin_mm,
      stock_file_id,
      parts_config,
      run_strategy_profile_version_id,
      solver_config_overrides_jsonb
    ) values (
      new.project_id,
      coalesce(new.created_by, app.current_user_id()),
      new.name,
      coalesce(new.schema_version, 'dxf_v1'),
      coalesce(new.seed, 0),
      coalesce(new.time_limit_s, 60),
      coalesce(new.spacing_mm, 2.0),
      coalesce(new.margin_mm, 5.0),
      new.stock_file_id,
      coalesce(new.parts_config, '[]'::jsonb),
      new.run_strategy_profile_version_id,
      coalesce(new.solver_config_overrides_jsonb, '{}'::jsonb)
    ) returning * into v_row;

    new.id := v_row.id;
    new.created_by := v_row.created_by;
    new.run_strategy_profile_version_id := v_row.run_strategy_profile_version_id;
    new.solver_config_overrides_jsonb := v_row.solver_config_overrides_jsonb;
    new.created_at := v_row.created_at;
    return new;
  end if;

  if tg_op = 'UPDATE' then
    update app.run_configs
       set name = new.name,
           schema_version = coalesce(new.schema_version, app.run_configs.schema_version),
           seed = coalesce(new.seed, app.run_configs.seed),
           time_limit_s = coalesce(new.time_limit_s, app.run_configs.time_limit_s),
           spacing_mm = coalesce(new.spacing_mm, app.run_configs.spacing_mm),
           margin_mm = coalesce(new.margin_mm, app.run_configs.margin_mm),
           stock_file_id = coalesce(new.stock_file_id, app.run_configs.stock_file_id),
           parts_config = coalesce(new.parts_config, app.run_configs.parts_config),
           run_strategy_profile_version_id = coalesce(new.run_strategy_profile_version_id, app.run_configs.run_strategy_profile_version_id),
           solver_config_overrides_jsonb = coalesce(new.solver_config_overrides_jsonb, app.run_configs.solver_config_overrides_jsonb)
     where id = old.id
     returning * into v_row;

    if v_row.id is null then
      raise exception 'run_config_not_found' using errcode = 'P0001';
    end if;

    new.id := v_row.id;
    new.project_id := v_row.project_id;
    new.created_by := v_row.created_by;
    new.run_strategy_profile_version_id := v_row.run_strategy_profile_version_id;
    new.solver_config_overrides_jsonb := v_row.solver_config_overrides_jsonb;
    new.created_at := v_row.created_at;
    return new;
  end if;

  if tg_op = 'DELETE' then
    delete from app.run_configs where id = old.id;
    return old;
  end if;

  return null;
end;
$$;
