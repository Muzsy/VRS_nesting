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

## P2 - Advisory (H2 closure audit, 2026-03-24)

### KI-005 Manufacturing metrics timing proxy szintetikus default ertekek
**Allapot:** OPEN (advisory, nem blokkolo)
**Forras:** H2-E6-T2 audit, 2026-03-24
**Terulet:** `api/services/manufacturing_metrics_calculator.py`

A `manufacturing_metrics_calculator` szintetikus default idozitesi ertekekkel
dolgozik (cut=50mm/s, rapid=200mm/s, pierce=0.5s). Ezek dokumentalt,
reprodukalhato proxy ertekek, nem valos gepkalibracio.

Ez H2 scope-ban helyes es vart viselkedes. Valos gep/anyag-specifikus
kalibracios modellt a H3 vagy kesobbi scope-ban erdemes bevezetni.

### KI-006 H2-E5-T4 optionalis machine-specific adapter nem implementalt
**Allapot:** OPEN (szandekos, nem blokkolo)
**Forras:** H2-E6-T2 audit, 2026-03-24
**Terulet:** H2 task tree (optionalis ag)

A `H2-E5-T4` elso machine-specific adapter a task tree-ben explicit optionalis
agkent szerepel. A H2 mainline closure PASS feltetelei kozott nem szerepel.
A machine-neutral export (H2-E5-T3) stabil es igazolt.

---

## P3 - Alacsony prioritas

### KI-004 Legacy H1-E2-T1 smoke script contract drift (`part_raw.v1` vs `normalized_geometry.v1`)
**Allapot:** RESOLVED (smoke script igazitva, 2026-03-20)
**Forras:** H1-E7-T2 audit futas, 2026-03-20
**Terulet:** `scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`, `api/services/dxf_geometry_import.py`

A legacy H1-E2-T1 smoke script a geometry revision `canonical_format_version`
mezore a regi `part_raw.v1` erteket varta, mikozben a jelenlegi canonical
pipeline valos formata `normalized_geometry.v1`.

Megoldas:
- A smoke script frissitve a jelenlegi `normalized_geometry.v1` contractra:
  `canonical_format_version`, `outer_ring`, `hole_rings` ellenorzesek igazitva.

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
