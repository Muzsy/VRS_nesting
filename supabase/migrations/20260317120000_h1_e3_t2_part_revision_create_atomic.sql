-- H1-E3-T2: atomic part revision insert + definition current_revision_id update
-- Replaces the two-step HTTP POST/PATCH in part_creation.py (H3 audit finding).
-- The SELECT FOR UPDATE on part_definitions serialises concurrent inserts,
-- eliminating the revision_no race without application-level retries.

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
as $$
declare
  v_definition  app.part_definitions%rowtype;
  v_next_rev_no integer;
  v_revision    app.part_revisions%rowtype;
begin
  -- Acquire an exclusive row lock on the part_definition for the duration of
  -- this transaction. All concurrent callers for the same definition queue
  -- here, making the revision_no MAX+1 computation safe without retries.
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

  -- Safe under the exclusive lock: no concurrent transaction can insert a
  -- revision for this definition between this read and our insert below.
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
    'draft',
    p_source_geometry_revision_id,
    p_selected_nesting_derivative_id,
    p_source_label,
    p_source_checksum_sha256,
    p_notes
  )
  returning * into v_revision;

  -- Update current_revision_id in the same transaction. Both writes are
  -- atomic: either both succeed or neither is visible to other sessions.
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
