-- Phase 1 storage bootstrap (current canonical):
-- - private source-files bucket
-- - authenticated users can access only project-owned object paths:
--   projects/{project_id}/files/{file_object_id}/...

insert into storage.buckets (id, name, public, file_size_limit)
select 'source-files', 'source-files', false, 52428800
where not exists (
  select 1
  from storage.buckets
  where id = 'source-files'
);

update storage.buckets
set public = false,
    file_size_limit = 52428800
where id = 'source-files';

alter table storage.objects enable row level security;

drop policy if exists source_files_owner_select on storage.objects;
create policy source_files_owner_select on storage.objects
  for select
  to authenticated
  using (
    bucket_id = 'source-files'
    and app.is_project_owner(app.storage_object_project_id(name))
  );

drop policy if exists source_files_owner_insert on storage.objects;
create policy source_files_owner_insert on storage.objects
  for insert
  to authenticated
  with check (
    bucket_id = 'source-files'
    and app.is_project_owner(app.storage_object_project_id(name))
  );

drop policy if exists source_files_owner_update on storage.objects;
create policy source_files_owner_update on storage.objects
  for update
  to authenticated
  using (
    bucket_id = 'source-files'
    and app.is_project_owner(app.storage_object_project_id(name))
  )
  with check (
    bucket_id = 'source-files'
    and app.is_project_owner(app.storage_object_project_id(name))
  );

drop policy if exists source_files_owner_delete on storage.objects;
create policy source_files_owner_delete on storage.objects
  for delete
  to authenticated
  using (
    bucket_id = 'source-files'
    and app.is_project_owner(app.storage_object_project_id(name))
  );
