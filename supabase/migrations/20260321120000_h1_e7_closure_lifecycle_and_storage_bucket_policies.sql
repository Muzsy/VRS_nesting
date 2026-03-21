-- H1 closure blocker fixes
-- 1) Align part/sheet revision lifecycle with snapshot builder expectations.
-- 2) Extend storage.objects owner policies to run-artifacts and geometry-artifacts buckets.

-- -----------------------------------------------------------------------------
-- 1) Atomic revision creators now produce approved revisions for H1 minimum flow
-- -----------------------------------------------------------------------------

create or replace function app.create_part_revision_atomic(
  p_part_definition_id             uuid,
  p_source_geometry_revision_id    uuid,
  p_selected_nesting_derivative_id uuid,
  p_source_label                   text default null,
  p_source_checksum_sha256         text default null,
  p_notes                          text default null
)
returns jsonb
language plpgsql
security definer
set search_path = app
as $$
declare
  v_definition  app.part_definitions%rowtype;
  v_next_rev_no integer;
  v_revision    app.part_revisions%rowtype;
begin
  select *
    into v_definition
    from app.part_definitions
   where id = p_part_definition_id
   for update;

  if v_definition.id is null then
    raise exception 'part_definition_not_found' using errcode = 'P0001';
  end if;

  if v_definition.owner_user_id <> app.current_user_id() then
    raise exception 'part_definition_forbidden' using errcode = '42501';
  end if;

  select coalesce(max(pr.revision_no), 0) + 1
    into v_next_rev_no
    from app.part_revisions pr
   where pr.part_definition_id = p_part_definition_id;

  insert into app.part_revisions (
    part_definition_id,
    revision_no,
    lifecycle,
    source_geometry_revision_id,
    selected_nesting_derivative_id,
    source_label,
    source_checksum_sha256,
    notes
  ) values (
    p_part_definition_id,
    v_next_rev_no,
    'approved',
    p_source_geometry_revision_id,
    p_selected_nesting_derivative_id,
    p_source_label,
    p_source_checksum_sha256,
    p_notes
  )
  returning * into v_revision;

  update app.part_definitions
     set current_revision_id = v_revision.id,
         updated_at          = now()
   where id = p_part_definition_id
  returning * into v_definition;

  return jsonb_build_object(
    'part_definition', to_jsonb(v_definition),
    'part_revision',   to_jsonb(v_revision)
  );
end;
$$;

revoke all on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) from public;
grant execute on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) to authenticated;


create or replace function app.create_sheet_revision_atomic(
  p_sheet_definition_id  uuid,
  p_width_mm             numeric,
  p_height_mm            numeric,
  p_grain_direction      text    default null,
  p_source_label         text    default null,
  p_notes                text    default null
)
returns jsonb
language plpgsql
security definer
set search_path = app
as $$
declare
  v_definition  app.sheet_definitions%rowtype;
  v_next_rev_no integer;
  v_revision    app.sheet_revisions%rowtype;
begin
  select *
    into v_definition
    from app.sheet_definitions
   where id = p_sheet_definition_id
   for update;

  if v_definition.id is null then
    raise exception 'sheet_definition_not_found' using errcode = 'P0001';
  end if;

  if v_definition.owner_user_id <> app.current_user_id() then
    raise exception 'sheet_definition_forbidden' using errcode = '42501';
  end if;

  select coalesce(max(sr.revision_no), 0) + 1
    into v_next_rev_no
    from app.sheet_revisions sr
   where sr.sheet_definition_id = p_sheet_definition_id;

  insert into app.sheet_revisions (
    sheet_definition_id,
    revision_no,
    lifecycle,
    width_mm,
    height_mm,
    grain_direction,
    source_label,
    notes
  ) values (
    p_sheet_definition_id,
    v_next_rev_no,
    'approved',
    p_width_mm,
    p_height_mm,
    p_grain_direction,
    p_source_label,
    p_notes
  )
  returning * into v_revision;

  update app.sheet_definitions
     set current_revision_id = v_revision.id,
         updated_at          = now()
   where id = p_sheet_definition_id
  returning * into v_definition;

  return jsonb_build_object(
    'sheet_definition', to_jsonb(v_definition),
    'sheet_revision',   to_jsonb(v_revision)
  );
end;
$$;

revoke all on function app.create_sheet_revision_atomic(uuid, numeric, numeric, text, text, text) from public;
grant execute on function app.create_sheet_revision_atomic(uuid, numeric, numeric, text, text, text) to authenticated;

-- ---------------------------------------------------------------------------
-- 1/b) Backfill existing draft revisions for H1 closure compatibility
-- ---------------------------------------------------------------------------

update app.part_revisions
   set lifecycle = 'approved'
 where lifecycle = 'draft';

update app.sheet_revisions
   set lifecycle = 'approved'
 where lifecycle = 'draft';

-- -----------------------------------------------------------------------------
-- 2) storage.objects project-owner policies for run-artifacts + geometry-artifacts
-- -----------------------------------------------------------------------------

do $$
declare
  v_bucket text;
  v_slug text;
begin
  begin
    execute 'alter table storage.objects enable row level security';

    foreach v_bucket in array array['run-artifacts', 'geometry-artifacts'] loop
      v_slug := replace(v_bucket, '-', '_');

      execute format('drop policy if exists h1_e7_t3_%s_owner_select on storage.objects', v_slug);
      execute format(
        'create policy h1_e7_t3_%1$s_owner_select on storage.objects for select to authenticated using (bucket_id = %2$L and app.is_project_owner(app.storage_object_project_id(name)))',
        v_slug,
        v_bucket
      );

      execute format('drop policy if exists h1_e7_t3_%s_owner_insert on storage.objects', v_slug);
      execute format(
        'create policy h1_e7_t3_%1$s_owner_insert on storage.objects for insert to authenticated with check (bucket_id = %2$L and app.is_project_owner(app.storage_object_project_id(name)))',
        v_slug,
        v_bucket
      );

      execute format('drop policy if exists h1_e7_t3_%s_owner_update on storage.objects', v_slug);
      execute format(
        'create policy h1_e7_t3_%1$s_owner_update on storage.objects for update to authenticated using (bucket_id = %2$L and app.is_project_owner(app.storage_object_project_id(name))) with check (bucket_id = %2$L and app.is_project_owner(app.storage_object_project_id(name)))',
        v_slug,
        v_bucket
      );

      execute format('drop policy if exists h1_e7_t3_%s_owner_delete on storage.objects', v_slug);
      execute format(
        'create policy h1_e7_t3_%1$s_owner_delete on storage.objects for delete to authenticated using (bucket_id = %2$L and app.is_project_owner(app.storage_object_project_id(name)))',
        v_slug,
        v_bucket
      );
    end loop;
  exception
    when insufficient_privilege then
      raise notice
        'h1_e7_t3 storage.objects policy rollout skipped (insufficient_privilege): %',
        sqlerrm;
  end;
end;
$$;
