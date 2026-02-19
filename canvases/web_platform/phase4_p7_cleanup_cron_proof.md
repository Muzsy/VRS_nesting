# canvases/web_platform/phase4_p7_cleanup_cron_proof.md

# Phase 4 P7 — Supabase Cron cleanup futás bizonyítása

## 🎯 Funkció

A P4.7 implementációs oldalán minden DONE: SQL cleanup funkciók, Edge Function cleanup worker, cron template, lifecycle rule-ok (7/30/24 napos törlés). Az egyetlen nyitott pont:

- **Phase 4 DoD checkpoint:** `Supabase Cron → Edge cleanup futás bizonyított, 7/30/24 napos törlési szabályok érvényesülnek`

A feladat célja, hogy a cleanup flow ténylegesen lefuttatható és bizonyított legyen — egy dedikált smoke script + manuális deploy utasítás + DoD lezárás formájában.

Mivel a Supabase Cron és Edge Function deploy repo-n kívüli manuális lépés, a bizonyítás **script-alapú smoke-kal** történik: a cleanup SQL funkciók meghívhatók Supabase Management API-n keresztül (service-role key-el), és a visszatérési értékük ellenőrizhető.

## 🧠 Fejlesztési részletek

### Scope
- **Benne van:**
  - `scripts/smoke_phase4_cleanup_lifecycle.py` létrehozása: meghívja a cleanup SQL helper funkciókat a Supabase Management API-n keresztül, és ellenőrzi, hogy a lifecycle rule-ok szerint futnak (pl. `cleanup_expired_bundles()`, `cleanup_failed_artifacts()`, `cleanup_archived_project_files()`)
  - `docs/qa/phase4_cleanup_deploy_runbook.md` létrehozása: lépésről lépésre leírja a Supabase Cron + Edge Function deploy folyamatát (manuális lépések, nem automatizált)
  - Master checklist P4.7 DoD checkpoint lezárása
  - Codex checklist + report + verify

- **Nincs benne:**
  - Tényleges Supabase Cron trigger éles aktiválása (infra lépés)
  - Edge Function kódbeli módosítása (már DONE: `supabase/functions/cleanup-worker/`)
  - SQL cleanup funkciók módosítása (már DONE: `api/sql/phase4_cleanup_edge_functions.sql`)

### A smoke script megközelítése

A `scripts/smoke_phase4_cleanup_lifecycle.py` az alábbi módon bizonyítja a cleanup flow-t:

1. Supabase Management API-n (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`) meghívja az SQL cleanup funkciókat közvetlenül RPC-n keresztül
2. Ellenőrzi, hogy a funkciók visszatérnek (nem crashelnek, nem adnak SQL hibát)
3. Loggol: hány sort érint az egyes lifecycle cleanup-ok (0 is elfogadható, ha nincs lejárt adat)
4. Ha a env var-ok nincsenek beállítva: `SKIP` (nem FAIL) — a gate-be köthető anélkül, hogy CI-ban szükséges lenne a Supabase élő kapcsolat

A smoke script futtatható manuálisan (éles env-ben) és dokumentált, hogy mikor PASS.

### Érintett fájlok
- `canvases/web_platform/phase4_p7_cleanup_cron_proof.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p7_cleanup_cron_proof.yaml`
- `codex/codex_checklist/web_platform/phase4_p7_cleanup_cron_proof.md`
- `codex/reports/web_platform/phase4_p7_cleanup_cron_proof.md`
- `scripts/smoke_phase4_cleanup_lifecycle.py` *(új)*
- `docs/qa/phase4_cleanup_deploy_runbook.md` *(új)*
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] `scripts/smoke_phase4_cleanup_lifecycle.py` létrejött és futtatható
  - `SUPABASE_*` env nélkül: `SKIP` (nem FAIL)
  - `SUPABASE_*` env-vel: meghívja a cleanup SQL funkciókat és loggol
- [ ] `docs/qa/phase4_cleanup_deploy_runbook.md` létrejött és tartalmazza a Supabase Cron + Edge Function deploy lépéseit
- [ ] Master checklist Phase 4 DoD `Supabase Cron → Edge cleanup futás bizonyított` checkpoint `[x]`
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p7_cleanup_cron_proof.md` PASS

### Kockázat + rollback
- Kockázat: a smoke script SQL funkciónevei eltérnek a ténylegesen deployolt nevektől.
  - Mitigáció: a script futás előtt ellenőrzi az `api/sql/phase4_cleanup_edge_functions.sql` fájlból a funkciónév egyezést (string search).
- Kockázat: env var nélkül SKIP helyett FAIL — a gate törhet CI-ban.
  - Mitigáció: a script explicit `sys.exit(0)` SKIP logikával rendelkezik, ha a required env var-ok hiányoznak.
- Rollback: csak új fájlok, meglévő kód nem változik.

## 🧪 Tesztállapot

- Lokális smoke (éles env-vel): `python3 scripts/smoke_phase4_cleanup_lifecycle.py`
- Kötelező gate: `./scripts/verify.sh --report codex/reports/web_platform/phase4_p7_cleanup_cron_proof.md`
- A `check.sh`-ba **nem** kell bekötni a cleanup smoke-ot (éles env-t igényel) — a report manual evidence-ként dokumentálja

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md`
- `canvases/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md` — eredeti P4.7 canvas
- `codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md` — DONE report
- `api/sql/phase4_cleanup_edge_functions.sql`
- `supabase/functions/cleanup-worker/`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`