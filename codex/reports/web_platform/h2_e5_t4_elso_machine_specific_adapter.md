# Report — h2_e5_t4_elso_machine_specific_adapter

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e5_t4_elso_machine_specific_adapter`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml`
* **Futtas datuma:** 2026-03-25
* **Branch / commit:** main
* **Fokusz terulet:** Service | Scripts

## 2) Scope

### 2.1 Cel
- Elso konkret celgepre irt machine-specific adapter: `hypertherm_edge_connect` / `basic_plasma_eia_rs274d`.
- A `manufacturing_plan_json` artifact primer bemenetkent, a snapshotolt postprocessor selection + `config_jsonb` alkalmazasaval per-sheet `machine_program` artifactok eloallitasa.
- A meglevo `machine_program` artifact kindot hasznalja custom `legacy_artifact_type` metadata-val.

### 2.2 Nem-cel (explicit)
- Uj lead-in/out rendszer vagy technology pack.
- Uj artifact kind bevezetese.
- Globalis SQL seed a postprocessor profilokra.
- `machine_ready_bundle`, zip, generic fallback emitter.
- Worker auto-trigger, frontend/export UI.
- Write manufacturing truth vagy postprocessor truth tablaba.

## 3) Valtozasok osszefoglaloja (Change summary)

### 3.1 Erintett fajlok

* **Services:**
  * `api/services/machine_specific_adapter.py` (uj, 842 sor)
* **Scripts:**
  * `scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py` (uj, 62 teszt)
* **Docs:**
  * `canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` (frissitett)
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml` (frissitett)
  * `codex/prompts/web_platform/h2_e5_t4_elso_machine_specific_adapter/run.md` (frissitett)
  * `codex/codex_checklist/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` (frissitett)
  * `codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` (frissitett)

### 3.2 Miert valtoztak?

A BLOCKED allapot feloldodott a konkret target freeze kitoltesevel. Uj adapter service es smoke script keszult.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` -> PASS

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/machine_specific_adapter.py` -> PASS
* `python3 -m py_compile scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py` -> PASS
* `python3 scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py` -> PASS (62/62)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-25T23:50:13+01:00 → 2026-03-25T23:53:45+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.verify.log`
- git: `main@f24d276`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 .../h2_e5_t4_elso_machine_specific_adapter.md      | 470 ++++++++++++++-------
 .../h2_e5_t4_elso_machine_specific_adapter.md      |  29 +-
 ...vas_h2_e5_t4_elso_machine_specific_adapter.yaml |  77 ++--
 .../h2_e5_t4_elso_machine_specific_adapter/run.md  | 124 ++++--
 .../h2_e5_t4_elso_machine_specific_adapter.md      | 121 +++---
 5 files changed, 535 insertions(+), 286 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md
 M codex/codex_checklist/web_platform/h2_e5_t4_elso_machine_specific_adapter.md
 M codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml
 M codex/prompts/web_platform/h2_e5_t4_elso_machine_specific_adapter/run.md
 M codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md
?? api/services/machine_specific_adapter.py
?? codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.verify.log
?? scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix (kotelezo)

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt |
| -------- | ------: | ------------------------ | ---------- | ---------------- |
| #1 Explicit target: `hypertherm_edge_connect` / `basic_plasma_eia_rs274d` | PASS | `api/services/machine_specific_adapter.py:53-55` | `TARGET_ADAPTER_KEY`, `TARGET_OUTPUT_FORMAT`, `TARGET_LEGACY_ARTIFACT_TYPE` konstansok | smoke Test 17 |
| #2 Optionalis H2 ag, nem blocker | PASS | canvas + report "Miert igy?" szekciok | A task dokumentacioja explicit jelzi az optionalis jelleget | — |
| #3 Primer bemenet: persisted `manufacturing_plan_json` artifact | PASS | `api/services/machine_specific_adapter.py:122-131` | `_load_export_artifact` + `_download_export_payload` | smoke Test 1, 7 |
| #4 Geometry feloldas csak `run_manufacturing_contours` + `geometry_derivatives` | PASS | `api/services/machine_specific_adapter.py:479-540` | `_build_geometry_cache`: plan_id + contour_index -> geometry_derivative_id -> derivative_jsonb | smoke Test 1, 14 |
| #5 `config_jsonb` szukitett boundary enforce | PASS | `api/services/machine_specific_adapter.py:61-82, 766-773` | `_ALLOWED_CONFIG_BLOCKS`, `_REQUIRED_CONFIG_BLOCKS`, `_validate_config_boundary` | smoke Test 10 |
| #6 Nincs uj lead-in/out rendszer | PASS | `api/services/machine_specific_adapter.py:323-331` | Csak mapping/fallback a persisted lead descriptorokra | smoke Test 4, 5 |
| #7 Nincs uj artifact kind; `machine_program` + custom legacy type | PASS | `api/services/machine_specific_adapter.py:56` | `_ARTIFACT_KIND = "machine_program"` | smoke Test 2, 12 |
| #8 Nincs globalis SQL seed | PASS | nincs migration fajl | Smoke fixture-ok in-memory | — |
| #9 Dedikalt `api/services/machine_specific_adapter.py` | PASS | `api/services/machine_specific_adapter.py:96` | `generate_machine_programs_for_run` entry point | smoke Test 1 |
| #10 Task-specifikus smoke | PASS | `scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py` | 17 test blokk, 62 assertion, mind PASS | smoke PASS |
| #11 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.verify.log` | exit code 0, AUTO_VERIFY blokk kitoltve | verify.sh |

## 6) Miert igy?

- **Miert a `manufacturing_plan_json` artifact a primer bemenet?** A H2 mainline export chain (H2-E5-T3) mar eloallitja a gepfuggetlen export payloadot. Az adapter erre epit, nem live project selectionre vagy raw solver outputra.
- **Hogyan oldjuk fel a canonical geometryt?** A `manufacturing_plan_json` payload `plan_id` + `contour_index` alapjan `run_manufacturing_contours.geometry_derivative_id` -> `geometry_derivatives.derivative_jsonb` (`manufacturing_canonical`) lookup.
- **Miert a meglevo `machine_program` kindot hasznaljuk?** A `machine_program` artifact kind mar letezik az enum-ban. Uj kind bevezetese felesleges migration lenne.
- **Miert nincs globalis SQL seed?** A `postprocessor_profiles` es `postprocessor_profile_versions` owner-scoped truth. Globalis seed ismeretlen owner ala tilos.
- **Miert marad ki a reszletes lead-in/out rendszer?** A task scope: adapter-side mapping/fallback a persisted lead descriptorokra, nem uj lead geometria tervezese.
- **A task tovabbra is optionalis H2 ag.** A T4 hianya nem minositi vissza a H2 mainline PASS allapotat.
- **Konkret target:** `hypertherm_edge_connect / basic_plasma_eia_rs274d`.

## 8) Advisory notes

- A timing/feed/kerf parameter konyvtar nem resze ennek a tasknak; a `config_jsonb` csak szuk adapter-konfig blokkokat tartalmaz.
- A smoke in-memory fixture-oket hasznal, nem valos Supabase/HTTP utvonalat.
- Az adapter idempotens: ujrafutaskor a korabbi `machine_program` artifactokat torol es ujrairja.

## 9) Follow-ups

- Tovabbi celgep-csalad adapterek (pl. XPR embedded-process) kulon taskban.
- Valos Supabase integracio teszt az adapter-pathra.
- Frontend export UI bekotes a `machine_program` artifactokhoz.
