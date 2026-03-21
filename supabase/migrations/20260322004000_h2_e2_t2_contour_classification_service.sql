-- H2-E2-T2 contour classification service:
-- Introduces app.geometry_contour_classes table for storing per-contour
-- classification results derived from manufacturing_canonical derivatives.
-- Pattern: mirrors H2 detailed roadmap section 4 (geometry_contour_classes).

-- 1) Create the geometry_contour_classes table
create table if not exists app.geometry_contour_classes (
  id uuid primary key default gen_random_uuid(),
  geometry_derivative_id uuid not null references app.geometry_derivatives(id) on delete cascade,
  contour_index integer not null,
  contour_kind text not null,
  feature_class text not null default 'default',
  is_closed boolean,
  area_mm2 numeric(18,4),
  perimeter_mm numeric(18,4),
  bbox_jsonb jsonb not null default '{}'::jsonb,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (geometry_derivative_id, contour_index)
);

-- 2) Index for derivative lookups
create index if not exists idx_geometry_contour_classes_derivative_id
  on app.geometry_contour_classes(geometry_derivative_id);

-- 3) RLS policy: owner can manage their own contour classes via derivative chain
alter table app.geometry_contour_classes enable row level security;

-- Read: authenticated users can read contour classes for derivatives they can see
create policy geometry_contour_classes_select_policy
  on app.geometry_contour_classes for select to authenticated
  using (
    exists (
      select 1
        from app.geometry_derivatives gd
        join app.geometry_revisions gr on gr.id = gd.geometry_revision_id
       where gd.id = geometry_contour_classes.geometry_derivative_id
         and gr.created_by = app.current_user_id()
    )
  );

-- Insert: authenticated users can insert classification for their own derivatives
create policy geometry_contour_classes_insert_policy
  on app.geometry_contour_classes for insert to authenticated
  with check (
    exists (
      select 1
        from app.geometry_derivatives gd
        join app.geometry_revisions gr on gr.id = gd.geometry_revision_id
       where gd.id = geometry_contour_classes.geometry_derivative_id
         and gr.created_by = app.current_user_id()
    )
  );

-- Update: authenticated users can update classification for their own derivatives
create policy geometry_contour_classes_update_policy
  on app.geometry_contour_classes for update to authenticated
  using (
    exists (
      select 1
        from app.geometry_derivatives gd
        join app.geometry_revisions gr on gr.id = gd.geometry_revision_id
       where gd.id = geometry_contour_classes.geometry_derivative_id
         and gr.created_by = app.current_user_id()
    )
  );

-- Delete: authenticated users can delete classification for their own derivatives
create policy geometry_contour_classes_delete_policy
  on app.geometry_contour_classes for delete to authenticated
  using (
    exists (
      select 1
        from app.geometry_derivatives gd
        join app.geometry_revisions gr on gr.id = gd.geometry_revision_id
       where gd.id = geometry_contour_classes.geometry_derivative_id
         and gr.created_by = app.current_user_id()
    )
  );
