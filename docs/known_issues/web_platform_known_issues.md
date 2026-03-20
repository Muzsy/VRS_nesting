# docs/known_issues/web_platform_known_issues.md

> Elo dokumentum. Az auditok/futasok altal feltart, de meg nem vegleg lezart
> web platform problemak nyilvantartasa.
>
> Allapotok: OPEN | IN_PROGRESS (task slug) | RESOLVED (task slug, datum)
> Azonosito-konvencio: KI-NNN (Known Issue, sorszam)

---

## P1 - Magas prioritas

### KI-001 Hosted Supabase owner-limit miatt storage.objects policy DDL megbukik
**Allapot:** RESOLVED (`h0_e6_t2_rls_policy_alapok_storage_policy_rollout_split`, 2026-03-15)  
**Forras:** Migration apply hiba, 2026-03-15  
**Terulet:** `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`, `storage.objects`

Hosted Supabase projektben a migracio futtato role (`postgres`) nem tulajdonosa
a `storage.objects` tablanak (`owner = supabase_storage_admin`), emiatt a
kovetkezo DDL-ek megbuknak:
- `alter table storage.objects enable row level security`
- `drop/create policy ... on storage.objects`

Tipikus hiba:
`ERROR: must be owner of table objects`

Veglegesitett allapot:
- A migracio split indokoltan megmaradt: az `app.*` RLS policyk SQL migraciobol mentek fel,
  a `storage.objects` DDL/policy szegmens kulon provisioningre maradt.
- Hosted Supabase-ben a kanonikus bucket inventory (`source-files`, `geometry-artifacts`,
  `run-artifacts`) letrehozva, mindharom bucket `private`.
- A H0 minimal storage policy matrix funkcionalisan el:
  - `source-files`: authenticated `select` + `insert`, owner/project-bound path szaballyal;
  - `geometry-artifacts`: authenticated `select`, owner/project-bound;
  - `run-artifacts`: authenticated `select`, owner/project-bound;
  - `anon`: policy nelkul.
- A storage oldali rollout manualis Dashboard/Studio provisioninggel tortent, nem a
  `20260314113000` migracio storage szegmensenek futtatasaval.

Megjegyzes:
- A policynevek hosted oldalon roviditettek lehetnek (Supabase nevhossz-limit), a
  functionalis szabalyok az iranyadok.

---

### KI-002 FastAPI API input validation es error hardening hianyossagok
**Allapot:** RESOLVED (`api_input_validation_hardening_followup`, 2026-03-18)  
**Forras:** `tmp/audit_report/fastAPI_API_layer_input_validation_audit.md`  
**Terulet:** `api/routes/*`, `api/auth.py`, `api/main.py`

Lezart pontok:
- Supabase hibareszletek kliens fele szivargasanak megszuntetese (sanitized `detail`, szerveroldali logolas).
- Request modellek szigoritasa (`extra="forbid"` alapmodell).
- UUID alapu path/body input validacio bevezetese.
- Hianyzo boundok (sheet meretek, quantity, artifact lista, parts_config lista).
- Hianyzo pagination/limit potlasa (`project files`, `run artifacts`).
- `status` query filter allowlistre szukitese.
- `x-request-id` / `x-correlation-id` header sanitization.

Megjegyzes:
- A kapcsolodo OpenAPI dokumentacio frissitve: `docs/api_openapi_schema.json`.

---

## P3 - Alacsony prioritas

### KI-004 Legacy H1-E2-T1 smoke script contract drift (`part_raw.v1` vs `normalized_geometry.v1`)
**Allapot:** OPEN  
**Forras:** H1-E7-T2 audit futas, 2026-03-20  
**Terulet:** `scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`, `api/services/dxf_geometry_import.py`

A legacy H1-E2-T1 smoke script a geometry revision `canonical_format_version`
mezore a regi `part_raw.v1` erteket varja, mikozben a jelenlegi canonical
pipeline valos formata `normalized_geometry.v1`.

Kovetkezmeny:
- A script futasa reprodukalhatoan `canonical_format_version mismatch` hibaval all meg.
- A hiba nem blokkolja a H1 minimum pipeline-t (pilot smoke + H1-E7-T2 regression smoke PASS),
  de dokumentacios/teszt adossag, mert egy regi task-smoke mar nem reprezentalja a valos contractot.

Tervezett kezeles:
- H2 elott a legacy smoke scriptet a jelenlegi canonical contracthoz kell igazitani,
  vagy explicit deprecate allapotba kell helyezni egyertelmu utmutatassal.

### KI-003 API tabla prefix mix (`app.*` vs compatibility `public.*` view-k)
**Allapot:** RESOLVED (`h1_e3_t4_multi_tenant_isolation_hardening`, 2026-03-18)  
**Forras:** `tmp/audit_report/fastAPI_API_layer_input_validation_audit.md` (ISSUE-12)  
**Terulet:** `api/routes/run_configs.py`, `api/routes/runs.py`, `supabase/migrations/20260318103000_h1_e3_t3_security_and_schema_bridge_fixes.sql`

Lezart allapot:
- A `run_configs` es `runs` route-ok teljesen `app.*` tablakat hasznalnak
  (`app.projects`, `app.file_objects`, `app.run_configs`, `app.nesting_runs`,
  `app.run_queue`, `app.run_artifacts`).
- A bridge `public.*` retegre epulo API oldali dependencia megszunt ezen a
  teruleten.

Megjegyzes:
- A compatibility view-k tovabbra is jelen lehetnek backward compatibility miatt,
  de az API route implementacio ezen a modulon mar nem ezekre tamaszkodik.

---
