PASS

## 1) Meta
- Task slug: `h0_e6_t2_rls_policy_alapok`
- Kapcsolodo canvas: `canvases/web_platform/h0_e6_t2_rls_policy_alapok.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t2_rls_policy_alapok.yaml`
- Futas datuma: `2026-03-15`
- Branch / commit: `main @ d764117 (dirty working tree)`
- Fokusz terulet: `Schema + Security + Docs`

## 2) Scope

### 2.1 Cel
- Alap H0 RLS policy bevezetese az `app.*` tablavilagon ownership/project-bound logikaval.
- Minimal `storage.objects` policy bevezetese a kanonikus bucket inventoryra (`source-files`, `geometry-artifacts`, `run-artifacts`).
- Service-role boundary konkret rogzitese docs source-of-truth formaban.
- Minimal architecture + roadmap docs szinkron a H0-E6-T2 iranyhoz.

### 2.2 Nem-cel
- Auth auto-provisioning trigger.
- Worker vagy API implementacio.
- Bucket provisioning script.
- H1/H2 szintu teljes jogosultsagi rendszer.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e6_t2_rls_policy_alapok.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t2_rls_policy_alapok.yaml`
- `codex/prompts/web_platform/h0_e6_t2_rls_policy_alapok/run.md`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `docs/web_platform/architecture/h0_security_rls_alapok.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e6_t2_rls_policy_alapok.md`
- `codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md`

### 3.2 Miert valtoztak?
- A H0-E6-T1 docs-only bucket/path szerzodes utan kellett a tenyleges baseline enforcement.
- A H0 futasi, geometry, project es storage vilag ownership szabalyait mar schema-szinten vedeni kell.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges policy osszegzes (H0-E6-T2)

### 5.1 Helper fuggvenyek
- `app.current_user_id()`
- `app.is_project_owner(project_uuid uuid)`
- `app.owns_part_definition(part_definition_uuid uuid)`
- `app.owns_sheet_definition(sheet_definition_uuid uuid)`
- `app.can_access_geometry_revision(geometry_revision_uuid uuid)`
- `app.can_access_run(run_uuid uuid)`
- `app.storage_object_project_id(object_name text)`

### 5.2 Tablankenti policy matrix (rovid)
- Self-row: `app.profiles`.
- Owner-only: `app.projects`, `app.part_definitions`, `app.part_revisions`, `app.sheet_definitions`, `app.sheet_revisions`.
- Project-owner: `app.project_settings`, `app.project_technology_setups`, `app.project_part_requirements`, `app.project_sheet_inputs`, `app.file_objects`, `app.geometry_revisions`, `app.nesting_runs`.
- Geometry/project-bound: `app.geometry_validation_reports`, `app.geometry_review_actions`, `app.geometry_derivatives`.
- Run/project-bound read-only: `app.nesting_run_snapshots`, `app.run_queue`, `app.run_logs`, `app.run_artifacts`, `app.run_layout_*`, `app.run_metrics`.
- Authenticated read-only: `app.technology_presets`.

### 5.3 User-oldali write vs read-only
- User-oldali write marad: profiles self, projects owner, project child CRUD, part/sheet owner CRUD, `nesting_runs` owner CRUD.
- User-oldalon read-only: `technology_presets`, `nesting_run_snapshots`, `run_queue`, `run_logs`, `run_artifacts`, `run_layout_*`, `run_metrics`, `geometry_derivatives`.

### 5.4 Storage objects policy
- `source-files`: authenticated owner-bound `select` + `insert`.
- `geometry-artifacts`: authenticated owner-bound `select`.
- `run-artifacts`: authenticated owner-bound `select`.
- `anon`: nincs policy.
- Path gate: `projects/{project_id}/...` + owner check.

### 5.5 Service-role boundary
- Worker/output irasi oldal service-role boundary marad (`run_queue`, `run_logs`, `run_artifacts`, `run_layout_*`, `run_metrics`, storage output write).
- H0-ban a user-oldali snapshot/output hozzaferes olvasasra korlatozott.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql` fajl. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:1` | A H0-E6-T2 migraciofajl letrejott. | Kezi ellenorzes |
| A migracio bekapcsolja a RLS-t a fo `app.*` tablavilagon. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:130` | A fo H0 `app.*` tablavilagra explicit `enable row level security` kerult. | `./scripts/verify.sh --report ...` |
| `anon` nem kap uzleti tabla-hozzaferest. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:164`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:702` | Uzleti policyk `to authenticated`; explicit `anon` policy nincs. | `./scripts/verify.sh --report ...` |
| `app.profiles` self-row policy alatt all. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:160` | Self-row select/insert/update/delete policyk keszultek. | `./scripts/verify.sh --report ...` |
| `app.projects` owner-only policy alatt all. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:193` | Owner-only CRUD policy a `projects` tablara. | `./scripts/verify.sh --report ...` |
| A projekthez kotott child tablavilag project-owner policy alatt all. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:222`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:338` | Project child tablavilag `app.is_project_owner(project_id)` alapu policyt kapott. | `./scripts/verify.sh --report ...` |
| A `part_*` / `sheet_*` definicio es revision vilag owner-only policy alatt all. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:429`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:487` | Owner/parent-owner alapu policyk mindket domainben. | `./scripts/verify.sh --report ...` |
| A `geometry_validation_reports`, `geometry_review_actions`, `geometry_derivatives` geometry/project alapu policy alatt allnak. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:549`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:573` | Geometry access helperrel project-ownerhez kotott olvasasi/insert szabalyok. | `./scripts/verify.sh --report ...` |
| A `nesting_run_snapshots` es output tablavilag run/project alapu read-only policy alatt all user oldalrol. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:584`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:633` | Snapshot+output tablavilag csak `select` policyt kapott user oldalra. | `./scripts/verify.sh --report ...` |
| A `technology_presets` authenticated read-only. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:644` | `authenticated` select policy van, write policy nincs. | `./scripts/verify.sh --report ...` |
| Minimal `storage.objects` policy letrejon a kanonikus bucket inventoryra. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:655`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:657`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:679`; `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:690` | A 3 kanonikus bucketre policy definicio keszult. | `./scripts/verify.sh --report ...` |
| Letrejon a `docs/web_platform/architecture/h0_security_rls_alapok.md` fajl. | PASS | `docs/web_platform/architecture/h0_security_rls_alapok.md:1` | A dedikalt security/RLS source-of-truth dokumentum letrejott. | Kezi ellenorzes |
| A docs egyertelmuen leirja a service-role boundaryt. | PASS | `docs/web_platform/architecture/h0_security_rls_alapok.md:79` | Kulon fejezet rogzitette a service-role irasi hatart. | Kezi ellenorzes |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret H0-E6-T2 irannyal. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:1245`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:913` | Mindket forrasban megjelent a H0-E6-T2 policy summary + hivatkozas. | Kezi ellenorzes |
| A task nem vezet be auth auto-provisioning triggert. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:704`; `docs/web_platform/architecture/h0_security_rls_alapok.md:13` | Az auto-provisioning explicit out-of-scope maradt. | `./scripts/verify.sh --report ...` |
| A task nem vezet be worker vagy API implementaciot. | PASS | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql:703`; `docs/web_platform/architecture/h0_security_rls_alapok.md:14` | A migracio/docs csak policy+docs scope-ban maradt. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md:84` | A matrix minden DoD ponthoz konkret bizonyitekot ad. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md` PASS. | PASS | `codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.verify.log:1` | A kotelezo gate PASS loggal igazolt. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A policy-csomag H0 minimal baseline; H1-ben tovabbi finomitas (pl. collab/membership, granular write policy) varhato.
- A storage policy jelenleg szigoruan a kanonikus H0 bucket inventoryra celzott; bovitest csak kovetkezo taskban erdemes nyitni.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-15T09:18:03+01:00 → 2026-03-15T09:21:28+01:00 (205s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.verify.log`
- git: `main@d764117`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 ...dxf_nesting_platform_architektura_es_supabase_schema.md | 14 +++++++++++++-
 .../roadmap/dxf_nesting_platform_h0_reszletes.md           | 13 ++++++++++++-
 2 files changed, 25 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e6_t2_rls_policy_alapok.md
?? codex/codex_checklist/web_platform/h0_e6_t2_rls_policy_alapok.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e6_t2_rls_policy_alapok.yaml
?? codex/prompts/web_platform/h0_e6_t2_rls_policy_alapok/
?? codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md
?? codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.verify.log
?? docs/web_platform/architecture/h0_security_rls_alapok.md
?? supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql
```

<!-- AUTO_VERIFY_END -->
