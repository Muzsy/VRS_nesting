-- H1-E3 audit fix: atomic sheet revision insert + definition current_revision_id update.
-- Mirrors the part-side pattern (create_part_revision_atomic) to eliminate
-- the two-step HTTP POST/PATCH race in sheet_creation.py.
-- The SELECT FOR UPDATE on sheet_definitions serialises concurrent inserts,
-- eliminating the revision_no race without application-level retries.

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
  -- Acquire an exclusive row lock on the sheet_definition for the duration of
  -- this transaction. All concurrent callers for the same definition queue
  -- here, making the revision_no MAX+1 computation safe without retries.
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

  -- Safe under the exclusive lock: no concurrent transaction can insert a
  -- revision for this definition between this read and our insert below.
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
    'draft',
    p_width_mm,
    p_height_mm,
    p_grain_direction,
    p_source_label,
    p_notes
  )
  returning * into v_revision;

  -- Update current_revision_id in the same transaction. Both writes are
  -- atomic: either both succeed or neither is visible to other sessions.
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
