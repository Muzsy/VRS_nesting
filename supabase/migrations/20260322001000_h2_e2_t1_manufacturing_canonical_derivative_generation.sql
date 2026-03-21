-- H2-E2-T1 manufacturing_canonical derivative generation:
-- Minimal part_revisions schema expansion for manufacturing derivative binding.
-- Pattern: mirrors H1-E3-T1 selected_nesting_derivative_id binding.

-- 1) Add selected_manufacturing_derivative_id column
alter table app.part_revisions
  add column if not exists selected_manufacturing_derivative_id uuid;

-- 2) FK to geometry_derivatives(id)
alter table app.part_revisions
  drop constraint if exists fk_part_revisions_selected_manufacturing_derivative;

alter table app.part_revisions
  add constraint fk_part_revisions_selected_manufacturing_derivative
  foreign key (selected_manufacturing_derivative_id)
  references app.geometry_derivatives(id)
  on delete set null;

-- 3) Same-geometry composite FK:
--    (selected_manufacturing_derivative_id, source_geometry_revision_id)
--    -> geometry_derivatives(id, geometry_revision_id)
--    Reuses the unique constraint uq_geometry_derivatives_id_geometry_revision
--    created in H1-E3-T1.
alter table app.part_revisions
  drop constraint if exists fk_part_revisions_selected_manufacturing_derivative_same_geometry;

alter table app.part_revisions
  add constraint fk_part_revisions_selected_manufacturing_derivative_same_geometry
  foreign key (selected_manufacturing_derivative_id, source_geometry_revision_id)
  references app.geometry_derivatives(id, geometry_revision_id)
  on delete set null;

-- 4) Index for manufacturing derivative lookups
create index if not exists idx_part_revisions_selected_manufacturing_derivative_id
  on app.part_revisions(selected_manufacturing_derivative_id);

-- 5) Update create_part_revision_atomic to accept optional manufacturing derivative id.
--    The old 6-arg signature is dropped and replaced with the new 7-arg version.

-- Drop old grants first (both old and new signatures to be safe)
revoke all on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) from public;
revoke all on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) from authenticated;

create or replace function app.create_part_revision_atomic(
  p_part_definition_id                  uuid,
  p_source_geometry_revision_id         uuid,
  p_selected_nesting_derivative_id      uuid,
  p_selected_manufacturing_derivative_id uuid default null,
  p_source_label                        text default null,
  p_source_checksum_sha256              text default null,
  p_notes                               text default null
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
    selected_manufacturing_derivative_id,
    source_label,
    source_checksum_sha256,
    notes
  ) values (
    p_part_definition_id,
    v_next_rev_no,
    'approved',
    p_source_geometry_revision_id,
    p_selected_nesting_derivative_id,
    p_selected_manufacturing_derivative_id,
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

-- Grant to authenticated (new 7-arg signature)
revoke all on function app.create_part_revision_atomic(uuid, uuid, uuid, uuid, text, text, text) from public;
grant execute on function app.create_part_revision_atomic(uuid, uuid, uuid, uuid, text, text, text) to authenticated;
