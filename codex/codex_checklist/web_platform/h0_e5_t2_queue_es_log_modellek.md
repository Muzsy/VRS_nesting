# Codex checklist - h0_e5_t2_queue_es_log_modellek

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- [x] A migracio letrehozza az `app.run_queue` tablat
- [x] A migracio letrehozza az `app.run_logs` tablat
- [x] A queue tabla kapcsolodik az `app.nesting_runs` es `app.nesting_run_snapshots` tablavilaghoz
- [x] A queue tabla hasznalja az `app.run_attempt_status` enumot
- [x] A queue tabla formalizalja a queue-level allapotot (`pending`/`leased`/`done`/`error`/`cancel_requested`/`cancelled`)
- [x] A queue tabla tartalmaz lease/heartbeat/retry mezoket
- [x] A log tabla append-only kulon log event tarolo
- [x] A task nem hoz letre kulon `run_attempts` tablat
- [x] A migracio nem hoz letre result/artifact/projection tablakat
- [x] A task nem vezet be RLS policyt
- [x] Minimal docs szinkron megtortent a queue/lease/log iranyhoz
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
