-- H1-E3-T1 part creation service minimum schema expansion:
-- explicit geometry revision + selected nesting derivative binding on part revisions.

alter table app.geometry_derivatives
  drop constraint if exists uq_geometry_derivatives_id_geometry_revision;

alter table app.geometry_derivatives
  add constraint uq_geometry_derivatives_id_geometry_revision
  unique (id, geometry_revision_id);

alter table app.part_revisions
  add column if not exists source_geometry_revision_id uuid,
  add column if not exists selected_nesting_derivative_id uuid;

alter table app.part_revisions
  drop constraint if exists fk_part_revisions_source_geometry_revision;

alter table app.part_revisions
  add constraint fk_part_revisions_source_geometry_revision
  foreign key (source_geometry_revision_id)
  references app.geometry_revisions(id)
  on delete set null;

alter table app.part_revisions
  drop constraint if exists fk_part_revisions_selected_nesting_derivative;

alter table app.part_revisions
  add constraint fk_part_revisions_selected_nesting_derivative
  foreign key (selected_nesting_derivative_id)
  references app.geometry_derivatives(id)
  on delete set null;

alter table app.part_revisions
  drop constraint if exists fk_part_revisions_selected_derivative_same_geometry;

alter table app.part_revisions
  add constraint fk_part_revisions_selected_derivative_same_geometry
  foreign key (selected_nesting_derivative_id, source_geometry_revision_id)
  references app.geometry_derivatives(id, geometry_revision_id)
  on delete set null;

alter table app.part_revisions
  drop constraint if exists chk_part_revisions_geometry_derivative_binding_pair;

alter table app.part_revisions
  add constraint chk_part_revisions_geometry_derivative_binding_pair
  check (
    (source_geometry_revision_id is null and selected_nesting_derivative_id is null)
    or (source_geometry_revision_id is not null and selected_nesting_derivative_id is not null)
  );

create index if not exists idx_part_revisions_source_geometry_revision_id
  on app.part_revisions(source_geometry_revision_id);

create index if not exists idx_part_revisions_selected_nesting_derivative_id
  on app.part_revisions(selected_nesting_derivative_id);
