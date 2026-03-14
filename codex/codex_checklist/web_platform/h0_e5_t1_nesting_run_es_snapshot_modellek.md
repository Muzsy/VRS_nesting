# Codex checklist - h0_e5_t1_nesting_run_es_snapshot_modellek

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- [x] A migracio letrehozza az `app.nesting_runs` tablat
- [x] A migracio letrehozza az `app.nesting_run_snapshots` tablat
- [x] A run tabla az `app.run_request_status` enumot hasznalja
- [x] A snapshot tabla az `app.run_snapshot_status` enumot hasznalja
- [x] A run es snapshot rekordok 1:1 kapcsolatban vannak
- [x] A snapshot tabla tartalmaz hash-et es strukturalt manifest mezoket
- [x] A snapshot append-only szemantikaju (`updated_at` nelkul)
- [x] A migracio nem hoz letre queue/log/result/artifact/projection tablakat
- [x] A task nem vezet be RLS policyt
- [x] Minimal docs szinkron megtortent a run request/snapshot iranyhoz
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
