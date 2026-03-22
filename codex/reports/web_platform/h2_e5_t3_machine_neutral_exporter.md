# Report — h2_e5_t3_machine_neutral_exporter

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e5_t3_machine_neutral_exporter`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t3_machine_neutral_exporter.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Scripts

## 2) Scope

### 2.1 Cel
- `manufacturing_plan_json` artifact kind bevezetese migratioval + legacy <-> enum bridge frissitessel.
- Dedikalt `api/services/machine_neutral_exporter.py` service a persisted H2 truth + snapshot alapjan.
- Deterministic, canonical JSON export payload eloallitasa owner-scoped runhoz.
- Artifact regisztracio `app.run_artifacts` ala `manufacturing_plan_json` tipussal.
- Task-specifikus smoke script (61/61 PASS) az invariansok bizonyitasara.

### 2.2 Nem-cel (explicit)
- Machine-specific adapter vagy celgep-csalad prototipus.
- `machine_ready_bundle` vagy barmilyen G-code/NC output.
- Postprocessor config geometriai alkalmazasa a toolpathra.
- Worker automatikus export-generator hook.
- Kulon export UI vagy uj dedikalt download endpoint.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260322043000_h2_e5_t3_machine_neutral_exporter.sql`
* **Service:**
  * `api/services/machine_neutral_exporter.py`
* **Scripts:**
  * `scripts/smoke_h2_e5_t3_machine_neutral_exporter.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t3_machine_neutral_exporter.yaml`
  * `codex/prompts/web_platform/h2_e5_t3_machine_neutral_exporter/run.md`
  * `codex/codex_checklist/web_platform/h2_e5_t3_machine_neutral_exporter.md`
  * `codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti a `manufacturing_plan_json` artifact kindot az `app.artifact_kind` enumba (L11-L24), frissiti a `legacy_artifact_type_to_kind` bridge-et (L28-L47) es a `artifact_kind_to_legacy_type` bridge-et (L54-L69), ujra granteli a fuggvenyeket (L73-L74).
* **Service:** Dedikalt machine-neutral exporter (`api/services/machine_neutral_exporter.py`) — owner-scoped run ellenorzes, persisted H2 plan truth + snapshot + opcionalis metrics betoltes, deterministic canonical JSON payload eloallitas, hash-alapu canonical storage path, `run_artifacts` regisztracio `manufacturing_plan_json` tipussal, idempotens delete-then-insert.
* **Smoke:** 13 test csoport, 61/61 assertion PASS — bizonyitja a deterministic payload, idempotens replace, no-write-out-of-scope, no-machine-ready, postprocessor metadata, ownership boundary, export contract invariansokat.

### 3.3 Milyen persisted truthbol epul a machine-neutral export

A service kizarolag az alabbi persisted truth retegekbol dolgozik:
- `app.run_manufacturing_plans` — per-sheet plan truth (H2-E4-T2)
- `app.run_manufacturing_contours` — per-contour plan truth (H2-E4-T2)
- `app.nesting_run_snapshots.manufacturing_manifest_jsonb` — snapshotolt manufacturing/postprocess selection (H2-E5-T2)
- `app.run_manufacturing_metrics` — opcionalis metrics truth (H2-E4-T3)
- `app.run_layout_sheets` — sheet_index adathoz

NEM olvas:
- `project_manufacturing_selection` live truthot
- Preview SVG artifactot
- Raw solver outputot vagy worker run directory-t

### 3.4 `manufacturing_plan_json` artifact kind bevezetese

- Migration: `ALTER TYPE app.artifact_kind ADD VALUE 'manufacturing_plan_json'` (idempotens, DO $$ blokk)
- Bridge: `legacy_artifact_type_to_kind('manufacturing_plan_json')` -> `'manufacturing_plan_json'::app.artifact_kind`
- Reverse bridge: `artifact_kind_to_legacy_type('manufacturing_plan_json', '{}')` -> `'manufacturing_plan_json'` (kind::text fallback)
- GRANT EXECUTE ujra mindket bridge-re

### 3.5 Deterministic JSON + storage/metadata policy

- Canonical JSON serialization: `json.dumps(sort_keys=True, separators=(",",":"))`
- Storage path: `projects/{project_id}/runs/{run_id}/manufacturing_plan_json/{content_sha256}.json`
- Filename: `out/manufacturing_plan.json` (stabil)
- Metadata: `filename`, `size_bytes`, `content_sha256`, `legacy_artifact_type='manufacturing_plan_json'`, `export_scope='h2_e5_t3'`, `export_contract_version`
- Idempotens: delete-then-insert per run (nincs duplikalt artifact)
- Smoke test 2 es 13 bizonyitja a byte-szintu determinizmust es a canonical JSON strukturat

### 3.6 Miert marad gepfuggetlen export scope

Ez a task kizarolag a mar persistalt H2 truth-bol auditalhato, gepfuggetlen export payloadot allit elo. A scope szandekosan szuk:
- Nincs machine-specific adapter vagy G-code/NC emit
- Nincs `machine_ready_bundle` letrehozas
- A postprocessor selection csak metadata-kent kerul be, nincs config alkalmazas
- Nincs worker auto-trigger vagy uj route
- A kesobbi machine-specific adapterek erre az export szerzodestre epithetnek

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md` -> PASS

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/machine_neutral_exporter.py scripts/smoke_h2_e5_t3_machine_neutral_exporter.py` -> PASS
* `python3 scripts/smoke_h2_e5_t3_machine_neutral_exporter.py` -> PASS (61/61)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 `manufacturing_plan_json` artifact kind + bridge | PASS | `supabase/migrations/20260322043000_h2_e5_t3_machine_neutral_exporter.sql:11-24` | `ALTER TYPE app.artifact_kind ADD VALUE 'manufacturing_plan_json'` + bridge frissites L28-L69 | smoke 1: artifact created |
| #2 Dedikalt exporter service | PASS | `api/services/machine_neutral_exporter.py:62-165` | `generate_machine_neutral_export()` publikus entry point | smoke 1: 10 assert |
| #3 Owner-scoped persisted truth export | PASS | `api/services/machine_neutral_exporter.py:282-297` | `_load_run_for_owner()` owner_user_id szures, `_load_manufacturing_plans()` L300, `_load_snapshot()` L268 | smoke 9: ownership violation error |
| #4 Deterministic + canonical payload | PASS | `api/services/machine_neutral_exporter.py:253-262` | `_canonical_json_bytes()` sort_keys=True, separators=(",",":") | smoke 2+13: byte-level identical + canonical JSON |
| #5 Artifact regisztracio `manufacturing_plan_json` | PASS | `api/services/machine_neutral_exporter.py:156-164` | `register_artifact(artifact_kind='manufacturing_plan_json')` | smoke 1+11: register check + metadata |
| #6 Postprocessor metadata, nincs machine emit | PASS | `api/services/machine_neutral_exporter.py:227-249` | `_extract_postprocessor_metadata()` snapshot-bol, metadata only | smoke 3: 8 assert (pp present, no machine) |
| #7 Nincs `machine_ready_bundle` / machine-specific | PASS | source scan | `machine_ready_bundle`, `gcode`, `machine_log` nem talalhato a service-ben | smoke 7: no forbidden artifact kinds |
| #8 Nem olvas live selection, nem ir truth-ba | PASS | source scan + write log | Service nem importal `project_manufacturing_selection`; write log check | smoke 6: no write to forbidden tables |
| #9 Task-specifikus smoke script | PASS | `scripts/smoke_h2_e5_t3_machine_neutral_exporter.py` | 13 test csoport, 61/61 PASS | smoke futtas output |
| #10 Checklist es report evidence-alapon | PASS | `codex/codex_checklist/.../h2_e5_t3_...md`, `codex/reports/.../h2_e5_t3_...md` | Minden DoD pont evidence-cel kitoltve | jelen report |
| #11 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.verify.log` | `./scripts/verify.sh --report ...` PASS (exit 0, 224s) | verify.sh futtas |

## 8) Advisory notes

- A machine-neutral export payload a `h2_e5_t3_v1` export contract verzioval indul. A kesobbi adapterek erre a stabil szerzodestre epithetnek.
- A postprocessor selection metadata-kent kerul az exportba, de nincs config alkalmazas vagy machine-specific emit — ez a kesobbi adapter task scope-ja.
- A metrics bekerules opcionalis: ha a runhoz nincs `run_manufacturing_metrics`, a payload `manufacturing_metrics` kulcs nelkul keszul.
- A generic `run_artifacts` list/download flow valtozatlanul kezeli az uj `manufacturing_plan_json` tipust a bridge frissites utan.

## 9) Follow-ups

- H2-E6+ scope: machine-specific adapter, amely a machine-neutral exportra epit.
- H2-E6+ scope: worker auto-trigger az export generalashoz.
- H2-E6+ scope: `machine_ready_bundle` letrehozas adapter-specifikus outputtal.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T18:42:19+01:00 → 2026-03-22T18:46:03+01:00 (224s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.verify.log`
- git: `main@3c74fb3`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? api/services/machine_neutral_exporter.py
?? canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md
?? codex/codex_checklist/web_platform/h2_e5_t3_machine_neutral_exporter.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e5_t3_machine_neutral_exporter.yaml
?? codex/prompts/web_platform/h2_e5_t3_machine_neutral_exporter/
?? codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md
?? codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.verify.log
?? scripts/smoke_h2_e5_t3_machine_neutral_exporter.py
?? supabase/migrations/20260322043000_h2_e5_t3_machine_neutral_exporter.sql
```

<!-- AUTO_VERIFY_END -->
