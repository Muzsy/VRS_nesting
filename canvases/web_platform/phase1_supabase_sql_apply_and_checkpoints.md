# canvases/web_platform/phase1_supabase_sql_apply_and_checkpoints.md

# Phase 1 Supabase SQL apply and checkpoint sync

## Funkcio
A feladat a Phase 1 SQL schema + RLS tenyleges alkalmazasa a Supabase DB-n,
allapotellenorzes script keszitese, es a master checklist Phase 1 pontjainak
frissitese a valosan teljesitett elemekkel.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `api/sql/phase1_schema.sql` es `api/sql/phase1_rls.sql` futtatasa a Supabase DB-n (`DATABASE_URL` alapjan);
  - `scripts/smoke_phase1_supabase_schema_state.py` ellenorzo script letrehozasa;
  - master checklist frissitese a Phase 1 valosan teljesitett checkpointokra.
- Nincs benne:
  - bucket/provisioning teljes automatizalasa Supabase management API-val;
  - Phase 2 worker vagy frontend feladatok.

### Erintett fajlok
- `canvases/web_platform/phase1_supabase_sql_apply_and_checkpoints.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase1_supabase_sql_apply_and_checkpoints.yaml`
- `codex/codex_checklist/web_platform/phase1_supabase_sql_apply_and_checkpoints.md`
- `codex/reports/web_platform/phase1_supabase_sql_apply_and_checkpoints.md`
- `scripts/smoke_phase1_supabase_schema_state.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] A Phase 1 schema SQL sikeresen lefut a Supabase DB-n.
- [ ] A Phase 1 RLS SQL sikeresen lefut a Supabase DB-n.
- [ ] Van smoke script, ami ellenorzi a kotelezo tablakat es az RLS allapotot.
- [ ] A master checklistben a bizonyitottan kesz Phase 1 pontok be vannak pipalva.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase1_supabase_sql_apply_and_checkpoints.md` PASS.

### Kockazat + rollback
- Kockazat: a Supabase DB-ben mar letezo objektumoknal SQL incompatibilitas lehet.
- Mitigacio: idempotens `if exists/if not exists` SQL, verify utani smoke allapotellenorzes.
- Rollback: policyk/drop es migration rollback kulon SQL-ben oldhato; checklist/report visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase1_supabase_sql_apply_and_checkpoints.md`
- Feladat-specifikus:
  - `python3 scripts/smoke_phase1_supabase_schema_state.py`

## Kapcsolodasok
- `api/sql/phase1_schema.sql`
- `api/sql/phase1_rls.sql`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
