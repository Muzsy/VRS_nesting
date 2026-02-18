# canvases/web_platform/phase1_auth_profile_provisioning_and_smoke_hardening.md

# Phase 1 auth profile provisioning + smoke hardening

## Funkcio
A feladat celja a Phase 1 auth hianyossag stabil lezarsa: automatikus
`auth.users -> public.users` provisioning SQL triggerrel, valamint a Phase 1
smoke script determinisztikus javitasa (kezi profile insert kivezetese).

## Fejlesztesi reszletek

### Scope
- Benne van:
  - auth profile provisioning SQL (`public.users` mirror) trigger/function;
  - schema smoke bovitese trigger/function jelenlet ellenorzessel;
  - API auth/projects/files smoke refaktor a kezi `public.users` insert
    workaround kivezetesere;
  - checklist/report dokumentacio frissites a valos allapot szerint.
- Nincs benne:
  - uj `/v1/auth/*` endpoint csomag;
  - Phase 2+ worker/frontend/security implementacio.

### Erintett fajlok
- `canvases/web_platform/phase1_auth_profile_provisioning_and_smoke_hardening.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase1_auth_profile_provisioning_and_smoke_hardening.yaml`
- `codex/codex_checklist/web_platform/phase1_auth_profile_provisioning_and_smoke_hardening.md`
- `codex/reports/web_platform/phase1_auth_profile_provisioning_and_smoke_hardening.md`
- `api/sql/phase1_auth_user_profile_trigger.sql`
- `api/sql/phase1_rls.sql`
- `scripts/smoke_phase1_supabase_schema_state.py`
- `scripts/smoke_phase1_api_auth_projects_files_validation.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] `auth.users` INSERT/UPDATE/DELETE esetekre letrejon/szinkronban maradjon/torlodjon a `public.users` sor.
- [ ] Schema smoke ellenorzi a trigger/function jelenletet.
- [ ] API smoke nem hasznal kezi `public.users` insert workaroundot.
- [ ] Master checklist allapot szovegesen konzisztens marad a nyitott login/signup DoD ponttal.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase1_auth_profile_provisioning_and_smoke_hardening.md` PASS.

### Kockazat + rollback
- Kockazat: trigger sql hibas jogosultsaggal vagy schema hivatkozassal fut.
- Mitigacio: idempotens SQL + schema smoke token/jelenlet ellenorzes.
- Rollback: trigger/function drop, smoke script visszaallitas, report/checklist revizio.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase1_auth_profile_provisioning_and_smoke_hardening.md`

## Kapcsolodasok
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md`
