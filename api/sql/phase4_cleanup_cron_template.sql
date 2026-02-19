-- Phase 4 P4.7 Cron -> Edge cleanup template
-- Fill placeholders before execution.

-- Example unschedule (idempotent):
-- select cron.unschedule('vrs_cleanup_every_15m');

select cron.schedule(
  'vrs_cleanup_every_15m',
  '*/15 * * * *',
  $$
  select net.http_post(
    url := 'https://<PROJECT_REF>.functions.supabase.co/cleanup-worker',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer <EDGE_FUNCTION_BEARER_TOKEN>'
    ),
    body := '{}'::jsonb
  );
  $$
);
