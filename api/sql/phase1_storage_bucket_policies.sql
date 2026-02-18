-- Phase 1 storage bootstrap: private bucket + owner scoped object policies

insert into storage.buckets (id, name, public, file_size_limit)
select 'vrs-nesting', 'vrs-nesting', false, 52428800
where not exists (
  select 1
  from storage.buckets
  where id = 'vrs-nesting'
);

update storage.buckets
set public = false,
    file_size_limit = 52428800
where id = 'vrs-nesting';

alter table storage.objects enable row level security;

drop policy if exists vrs_nesting_owner_select on storage.objects;
create policy vrs_nesting_owner_select on storage.objects
  for select
  using (
    storage.objects.bucket_id = 'vrs-nesting'
    and auth.role() = 'authenticated'
    and (
      (
        split_part(storage.objects.name, '/', 1) = 'users'
        and split_part(storage.objects.name, '/', 2) = auth.uid()::text
        and split_part(storage.objects.name, '/', 3) = 'projects'
        and split_part(storage.objects.name, '/', 5) = 'files'
        and split_part(storage.objects.name, '/', 6) <> ''
        and exists (
          select 1
          from public.projects p
          where p.id::text = split_part(storage.objects.name, '/', 4)
            and p.owner_id = auth.uid()
        )
      )
      or
      (
        split_part(storage.objects.name, '/', 1) = 'runs'
        and split_part(storage.objects.name, '/', 2) <> ''
        and split_part(storage.objects.name, '/', 3) = 'artifacts'
        and exists (
          select 1
          from public.runs r
          join public.projects p on p.id = r.project_id
          where r.id::text = split_part(storage.objects.name, '/', 2)
            and p.owner_id = auth.uid()
        )
      )
    )
  );

drop policy if exists vrs_nesting_owner_insert on storage.objects;
create policy vrs_nesting_owner_insert on storage.objects
  for insert
  with check (
    storage.objects.bucket_id = 'vrs-nesting'
    and auth.role() = 'authenticated'
    and (
      (
        split_part(storage.objects.name, '/', 1) = 'users'
        and split_part(storage.objects.name, '/', 2) = auth.uid()::text
        and split_part(storage.objects.name, '/', 3) = 'projects'
        and split_part(storage.objects.name, '/', 5) = 'files'
        and split_part(storage.objects.name, '/', 6) <> ''
        and exists (
          select 1
          from public.projects p
          where p.id::text = split_part(storage.objects.name, '/', 4)
            and p.owner_id = auth.uid()
        )
      )
      or
      (
        split_part(storage.objects.name, '/', 1) = 'runs'
        and split_part(storage.objects.name, '/', 2) <> ''
        and split_part(storage.objects.name, '/', 3) = 'artifacts'
        and exists (
          select 1
          from public.runs r
          join public.projects p on p.id = r.project_id
          where r.id::text = split_part(storage.objects.name, '/', 2)
            and p.owner_id = auth.uid()
        )
      )
    )
  );

drop policy if exists vrs_nesting_owner_update on storage.objects;
create policy vrs_nesting_owner_update on storage.objects
  for update
  using (
    storage.objects.bucket_id = 'vrs-nesting'
    and auth.role() = 'authenticated'
    and (
      (
        split_part(storage.objects.name, '/', 1) = 'users'
        and split_part(storage.objects.name, '/', 2) = auth.uid()::text
        and split_part(storage.objects.name, '/', 3) = 'projects'
        and split_part(storage.objects.name, '/', 5) = 'files'
        and split_part(storage.objects.name, '/', 6) <> ''
        and exists (
          select 1
          from public.projects p
          where p.id::text = split_part(storage.objects.name, '/', 4)
            and p.owner_id = auth.uid()
        )
      )
      or
      (
        split_part(storage.objects.name, '/', 1) = 'runs'
        and split_part(storage.objects.name, '/', 2) <> ''
        and split_part(storage.objects.name, '/', 3) = 'artifacts'
        and exists (
          select 1
          from public.runs r
          join public.projects p on p.id = r.project_id
          where r.id::text = split_part(storage.objects.name, '/', 2)
            and p.owner_id = auth.uid()
        )
      )
    )
  )
  with check (
    storage.objects.bucket_id = 'vrs-nesting'
    and auth.role() = 'authenticated'
    and (
      (
        split_part(storage.objects.name, '/', 1) = 'users'
        and split_part(storage.objects.name, '/', 2) = auth.uid()::text
        and split_part(storage.objects.name, '/', 3) = 'projects'
        and split_part(storage.objects.name, '/', 5) = 'files'
        and split_part(storage.objects.name, '/', 6) <> ''
        and exists (
          select 1
          from public.projects p
          where p.id::text = split_part(storage.objects.name, '/', 4)
            and p.owner_id = auth.uid()
        )
      )
      or
      (
        split_part(storage.objects.name, '/', 1) = 'runs'
        and split_part(storage.objects.name, '/', 2) <> ''
        and split_part(storage.objects.name, '/', 3) = 'artifacts'
        and exists (
          select 1
          from public.runs r
          join public.projects p on p.id = r.project_id
          where r.id::text = split_part(storage.objects.name, '/', 2)
            and p.owner_id = auth.uid()
        )
      )
    )
  );

drop policy if exists vrs_nesting_owner_delete on storage.objects;
create policy vrs_nesting_owner_delete on storage.objects
  for delete
  using (
    storage.objects.bucket_id = 'vrs-nesting'
    and auth.role() = 'authenticated'
    and (
      (
        split_part(storage.objects.name, '/', 1) = 'users'
        and split_part(storage.objects.name, '/', 2) = auth.uid()::text
        and split_part(storage.objects.name, '/', 3) = 'projects'
        and split_part(storage.objects.name, '/', 5) = 'files'
        and split_part(storage.objects.name, '/', 6) <> ''
        and exists (
          select 1
          from public.projects p
          where p.id::text = split_part(storage.objects.name, '/', 4)
            and p.owner_id = auth.uid()
        )
      )
      or
      (
        split_part(storage.objects.name, '/', 1) = 'runs'
        and split_part(storage.objects.name, '/', 2) <> ''
        and split_part(storage.objects.name, '/', 3) = 'artifacts'
        and exists (
          select 1
          from public.runs r
          join public.projects p on p.id = r.project_id
          where r.id::text = split_part(storage.objects.name, '/', 2)
            and p.owner_id = auth.uid()
        )
      )
    )
  );
