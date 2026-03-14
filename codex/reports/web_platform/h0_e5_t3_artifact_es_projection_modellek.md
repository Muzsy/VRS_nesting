PASS

## 1) Meta
- Task slug: `h0_e5_t3_artifact_es_projection_modellek`
- Kapcsolodo canvas: `canvases/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t3_artifact_es_projection_modellek.yaml`
- Futas datuma: `2026-03-14`
- Branch / commit: `main @ 285c8f7 (dirty working tree)`
- Fokusz terulet: `Schema + Docs`

## 2) Scope

### 2.1 Cel
- H0-E5-T3 migracio letrehozasa az `app.run_artifacts`, `app.run_layout_sheets`, `app.run_layout_placements`, `app.run_layout_unplaced`, `app.run_metrics` tablakkal.
- Az artifact (`run_artifacts`) es projection (`run_layout_*`) reteg fizikailag kulonvalasztasa.
- Run-level osszegzett metrika tarolo (`app.run_metrics`) formalizalasa.
- Az `app.artifact_kind` enum gyakorlati hasznalata.

### 2.2 Nem-cel
- Kulon `app.run_results` tabla.
- Storage bucket policy.
- RLS policy.
- API / worker implementacio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e5_t3_artifact_es_projection_modellek.yaml`
- `codex/prompts/web_platform/h0_e5_t3_artifact_es_projection_modellek/run.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`
- `codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md`

### 3.2 Miert valtoztak?
- A T1/T2 futasi gerinc utan kellett az output oldali artifact+projection+metrics tablavilag stabil letetele.
- A T3 docs-sync celja a stale `public.run_layout_*` / `public.run_metrics` es `run_results` maradvanyok korrigalasa volt.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges schema inventory (T3 scope)

### 5.1 `app.run_artifacts` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `run_id uuid not null references app.nesting_runs(id) on delete cascade`
- `snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null`
- `artifact_kind app.artifact_kind not null`
- `storage_bucket text not null`
- `storage_path text not null`
- `metadata_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`

### 5.2 `app.run_layout_sheets` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `run_id uuid not null references app.nesting_runs(id) on delete cascade`
- `sheet_index integer not null`
- `sheet_revision_id uuid references app.sheet_revisions(id) on delete set null`
- `width_mm numeric(12,3)`
- `height_mm numeric(12,3)`
- `utilization_ratio numeric(8,5)`
- `metadata_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`

### 5.3 `app.run_layout_placements` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `run_id uuid not null references app.nesting_runs(id) on delete cascade`
- `sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade`
- `placement_index integer not null`
- `part_revision_id uuid references app.part_revisions(id) on delete set null`
- `quantity integer not null default 1`
- `transform_jsonb jsonb not null`
- `bbox_jsonb jsonb not null default '{}'::jsonb`
- `metadata_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`

### 5.4 `app.run_layout_unplaced` oszlopok
- `id uuid primary key default gen_random_uuid()`
- `run_id uuid not null references app.nesting_runs(id) on delete cascade`
- `part_revision_id uuid references app.part_revisions(id) on delete set null`
- `remaining_qty integer not null`
- `reason text`
- `metadata_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`

### 5.5 `app.run_metrics` oszlopok
- `run_id uuid primary key references app.nesting_runs(id) on delete cascade`
- `placed_count integer not null default 0`
- `unplaced_count integer not null default 0`
- `used_sheet_count integer not null default 0`
- `utilization_ratio numeric(8,5)`
- `remnant_value numeric(14,2)`
- `metrics_jsonb jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`

### 5.6 Integritas es indexek
- `app.run_artifacts`: nem ures `storage_bucket`/`storage_path` check, `idx_run_artifacts_run`.
- `app.run_layout_sheets`: `sheet_index >= 0`, `unique (run_id, sheet_index)`, `idx_run_layout_sheets_run`.
- `app.run_layout_placements`: `placement_index >= 0`, `quantity > 0`, `unique (sheet_id, placement_index)`, `idx_run_layout_placements_sheet_id_placement_index`, `idx_run_layout_placements_run`.
- `app.run_layout_unplaced`: `remaining_qty > 0`, `idx_run_layout_unplaced_run`.
- `app.run_metrics`: `placed_count >= 0`, `unplaced_count >= 0`, `used_sheet_count >= 0`.

### 5.7 Kulon kiemelt modellpontok
- Az artifact reteg (`app.run_artifacts`) kulon marad a projection retegtol (`app.run_layout_*`).
- A run-level eredmeny H0-ban `app.run_metrics` + `app.run_layout_*` + `app.run_artifacts` osszetett modell.
- A task szandekosan NEM hoz letre kulon `app.run_results` tablat.
- A task szandekosan NEM vezet be storage policyt vagy RLS policyt.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql` fajl. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:1` | A T3 migraciofajl letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_artifacts` tablata. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:4` | Az artifact tabla letrejott enum tipussal. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_layout_sheets` tablata. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:20` | A sheet projection tabla letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_layout_placements` tablata. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:37` | A placement projection tabla letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_layout_unplaced` tablata. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:61` | Az unplaced projection tabla letrejott. | `./scripts/verify.sh --report ...` |
| A migracio letrehozza az `app.run_metrics` tablata. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:76` | A run-level metrics tabla letrejott. | `./scripts/verify.sh --report ...` |
| Az artifact tabla hasznalja az `app.artifact_kind` enumot. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:8` | Az `artifact_kind` oszlop enum tipussal szerepel. | `./scripts/verify.sh --report ...` |
| Az artifact es projection reteg fizikailag kulon marad. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:4`; `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:20` | Kulon tablaban jelenik meg az artifact es a projection reteg. | `./scripts/verify.sh --report ...` |
| A task nem hoz letre kulon `app.run_results` tablat. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:88`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:204` | A migracio explicit note-olja, a docs is tisztazza. | `./scripts/verify.sh --report ...` |
| A task nem ad hozza storage bucket policyt vagy RLS policyt. | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql:89` | Policy SQL nincs; explicit out-of-scope note szerepel. | `./scripts/verify.sh --report ...` |
| A `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`, a `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret H0-E5-T3 irannyal. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:159`; `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:1094`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:812` | A T3 output modell es no-`run_results` irany doksiban tisztazott. | `./scripts/verify.sh --report ...` |
| A docsban a stale `public.run_layout_*`, `public.run_metrics` es `run_results` maradvanyok a T3-kozelben helyre vannak teve. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:1099`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:812` | A T3 SQL blokk `app.*` prefixre lett igazitva, stale hivatkozas javitva. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md:124` | A matrix minden DoD ponthoz konkret bizonyitekot ad. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md` PASS. | PASS | `codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.verify.log:1` | A kotelezo gate PASS loggal igazolt. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A `run_artifacts` tabla jelenleg nem erositi globalis `(storage_bucket, storage_path)` unique constrainttel a storage oldali semantikakat; ez kesobbi policy-taskban pontosithato.
- A docs SQL blokkok T3-ra lettek igazitva, de teljes dokumentacio-wide konzisztencia audit kulon feladatban erdemes.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-14T11:14:39+01:00 → 2026-03-14T11:18:08+01:00 (209s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.verify.log`
- git: `main@285c8f7`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 ...ing_platform_architektura_es_supabase_schema.md | 103 ++++++++++++---------
 .../h0_snapshot_first_futasi_es_adatkontraktus.md  |  18 ++--
 .../roadmap/dxf_nesting_platform_h0_reszletes.md   |  34 ++++++-
 3 files changed, 100 insertions(+), 55 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e5_t3_artifact_es_projection_modellek.md
?? codex/codex_checklist/web_platform/h0_e5_t3_artifact_es_projection_modellek.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e5_t3_artifact_es_projection_modellek.yaml
?? codex/prompts/web_platform/h0_e5_t3_artifact_es_projection_modellek/
?? codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md
?? codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.verify.log
?? supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql
```

<!-- AUTO_VERIFY_END -->
