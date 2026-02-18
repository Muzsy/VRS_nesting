-- Phase 1 auth profile provisioning: auth.users <-> public.users sync

create or replace function public.handle_auth_user_profile_sync()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'INSERT' then
    insert into public.users (id, email, display_name, tier, quota_runs_per_month)
    values (
      new.id,
      coalesce(new.email, ''),
      coalesce(new.raw_user_meta_data->>'display_name', new.raw_user_meta_data->>'full_name'),
      'free',
      50
    )
    on conflict (id) do update
      set email = excluded.email,
          display_name = coalesce(excluded.display_name, public.users.display_name);
    return new;
  end if;

  if tg_op = 'UPDATE' then
    insert into public.users (id, email, display_name, tier, quota_runs_per_month)
    values (
      new.id,
      coalesce(new.email, ''),
      coalesce(new.raw_user_meta_data->>'display_name', new.raw_user_meta_data->>'full_name'),
      'free',
      50
    )
    on conflict (id) do update
      set email = excluded.email,
          display_name = coalesce(excluded.display_name, public.users.display_name);
    return new;
  end if;

  if tg_op = 'DELETE' then
    delete from public.users where id = old.id;
    return old;
  end if;

  return null;
end;
$$;

drop trigger if exists on_auth_user_profile_sync on auth.users;
create trigger on_auth_user_profile_sync
  after insert or update or delete on auth.users
  for each row
  execute function public.handle_auth_user_profile_sync();
