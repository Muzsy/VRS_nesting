# Report — h2_e5_t5_masodik_machine_specific_adapter_qtplasmac

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e5_t5_masodik_machine_specific_adapter_qtplasmac`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.yaml`
* **Futtas datuma:** 2026-03-29
* **Branch / commit:** main
* **Fokusz terulet:** Service | Scripts

## 2) Scope

### 2.1 Cel
- A meglevo Hypertherm-only machine-specific adaptert minimalisan, regresszio nelkul boviteni ket-targetes dispatch-csal.
- Masodik konkret celgep-csalad: `linuxcnc_qtplasmac` / `basic_manual_material_rs274ngc`.
- Per-sheet `machine_program` artifactok `.ngc` kiterjesztessel.
- A `manufacturing_plan_json` artifact primer bemenet.

### 2.2 Nem-cel (explicit)
- Uj lead-in/out rendszer vagy technology pack.
- Uj artifact kind bevezetese.
- Globalis SQL seed a postprocessor profilokra.
- `M190`/`M66` auto material-change workflow.
- `machine_ready_bundle`, zip, generic fallback emitter.
- Worker auto-trigger, frontend/export UI.
- Write manufacturing truth vagy postprocessor truth tablaba.
- Altalanos plugin-framework vagy dinamikus adapter-registry.

## 3) Valtozasok osszefoglaloja (Change summary)

### 3.1 Erintett fajlok

* **Services:**
  * `api/services/machine_specific_adapter.py` (bovitett — ket-targetes dispatch + QtPlasmaC emitter)
* **Scripts:**
  * `scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py` (uj, 78 assertion)
* **Docs:**
  * `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md` (T5 bejegyzes)
  * `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md` (T5 hivatkozas)
  * `canvases/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.yaml`
  * `codex/prompts/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac/run.md`
  * `codex/codex_checklist/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
  * `codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`

### 3.2 Miert valtoztak?

A H2 optionalis postprocess ag masodik celgep-csalad adaptere (QtPlasmaC) keszult el. A meglevo Hypertherm adapter regresszio nelkul megmaradt, a dispatch a snapshotolt `adapter_key` + `output_format` alapjan tortenik.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md` -> PASS

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/machine_specific_adapter.py` -> PASS
* `python3 -m py_compile scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py` -> PASS
* `python3 scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py` -> PASS (78/78)
* `python3 scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py` -> PASS (62/62, Hypertherm regresszio nelkul)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-29T10:48:04+02:00 → 2026-03-29T10:51:44+02:00 (220s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.verify.log`
- git: `main@e725e54`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 .gitignore                                         |   1 +
 api/services/machine_specific_adapter.py           | 311 ++++++++++++++++++---
 .../roadmap/dxf_nesting_platform_h2_reszletes.md   |   1 +
 ...ng_platform_implementacios_backlog_task_tree.md |  12 +-
 frontend/src/pages/AuthPage.tsx                    | 175 ++++++++----
 scripts/run_web_platform.sh                        |   3 +-
 worker/main.py                                     |   5 +-
 7 files changed, 407 insertions(+), 101 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .gitignore
 M api/services/machine_specific_adapter.py
 M docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md
 M docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
 M frontend/src/pages/AuthPage.tsx
 M scripts/run_web_platform.sh
 M worker/main.py
?? .codex
?? canvases/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md
?? codex/codex_checklist/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.yaml
?? codex/prompts/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac/
?? codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md
?? codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.verify.log
?? scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix (kotelezo)

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt |
| -------- | ------: | ------------------------ | ---------- | ---------------- |
| #1 Explicit target: `linuxcnc_qtplasmac` / `basic_manual_material_rs274ngc` | PASS | `api/services/machine_specific_adapter.py:63-65` | `QTPLASMAC_ADAPTER_KEY`, `QTPLASMAC_OUTPUT_FORMAT`, `QTPLASMAC_LEGACY_ARTIFACT_TYPE` konstansok | smoke Test 16 |
| #2 Roadmapban megjelenik optionalis T5 | PASS | `dxf_nesting_platform_implementacios_backlog_task_tree.md` H2-E5-T5 blokk | Task tree-ben es H2 reszletes doksiban | — |
| #3 Hypertherm target regresszio nelkul megmaradt | PASS | T4 smoke 62/62, T5 smoke Test 4 (12 assertion) | A ket-targetes dispatch nem torte meg a Hypertherm emittert | smoke Test 4, T4 smoke |
| #4 Primer bemenet: persisted `manufacturing_plan_json` artifact | PASS | `api/services/machine_specific_adapter.py:_load_export_artifact` + `_download_export_payload` | Nincs live selection, raw solver, preview SVG olvasa | smoke Test 1, 7 |
| #5 Canonical geometry feloldas persisted truth-bol | PASS | `api/services/machine_specific_adapter.py:_build_geometry_cache` | plan_id + contour_index -> geometry_derivative_id -> derivative_jsonb | smoke Test 1, 13 |
| #6 Per-sheet `machine_program` artifact `.ngc` kiterjesztessel | PASS | smoke Test 1, 2 | 1 sheet = 1 upload + 1 register, `.ngc` filename | smoke Test 1, 3 |
| #7 Target-specifikus legacy type metadata | PASS | smoke Test 2 | `legacy_artifact_type='linuxcnc_qtplasmac_basic_manual_material'` | smoke Test 2 |
| #8 Deterministic storage path, filename, hash | PASS | smoke Test 3 | Byte-level identical ketszeri futtatasra | smoke Test 3 |
| #9 Nincs uj artifact kind | PASS | `_ARTIFACT_KIND = "machine_program"` | Meglevo enum | smoke Test 11 |
| #10 Nincs globalis SQL seed | PASS | nincs migration fajl | In-memory fixture-ok | — |
| #11 Nincs write forbidden truth tablakba | PASS | smoke Test 10 | 6 forbidden tabla ellenorizve | smoke Test 10 |
| #12 Nincs `M190`/`M66` auto material-change | PASS | smoke Test 12 | `M190` es `M66` absent az outputbol | smoke Test 12 |
| #13 Nincs uj lead-in/out rendszer | PASS | adapter mapping/fallback only | Csak persisted lead descriptor mapping | smoke Test 13 |
| #14 Smoke ellenorzi pozitiv + regresszio + boundary | PASS | `scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py` | 17 test blokk, 78 assertion, mind PASS | smoke PASS |
| #15 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.verify.log` | check.sh exit 0, AUTO_VERIFY blokk kitoltve | verify.sh |

## 6) Miert igy?

- **Miert a `manufacturing_plan_json` artifact a primer bemenet?** A H2 mainline export chain (H2-E5-T3) mar eloallitja a gepfuggetlen export payloadot. Az adapter erre epit, nem live project selectionre vagy raw solver outputra.
- **Hogyan oldjuk fel a canonical geometryt a persisted truthbol?** A `manufacturing_plan_json` payload `plan_id` + `contour_index` alapjan `run_manufacturing_contours.geometry_derivative_id` -> `geometry_derivatives.derivative_jsonb` (`manufacturing_canonical`) lookup.
- **Miert a meglevo `machine_program` kindot hasznaljuk uj enum helyett?** A `machine_program` artifact kind mar letezik. Uj kind bevezetese felesleges migration lenne. A target megkulonboztetese a `metadata_jsonb.legacy_artifact_type` mezon keresztul tortenik.
- **Miert nincs globalis SQL seed?** A `postprocessor_profiles` es `postprocessor_profile_versions` owner-scoped truth. Globalis seed ismeretlen owner ala tilos.
- **Miert marad ki a reszletes lead-in/out rendszer?** A task scope: adapter-side mapping/fallback a persisted lead descriptorokra, nem uj lead geometria tervezese.
- **Miert marad ki az `M190`/`M66` auto material-change workflow?** Ez a task basic manual-material QtPlasmaC adapterrol szol. Az automatikus material-change kulon scope es komplexitas, kulon taskban kezelendo.
- **A task tovabbra is optionalis H2 ag.** A T5 hianya nem minositi vissza a H2 mainline PASS allapotat.
- **A Hypertherm targetet regresszio nelkul meg kellett tartani.** A ket-targetes dispatch a snapshotolt `adapter_key` + `output_format` alapjan mukodik, nem torte meg a meglevo Hypertherm emittert.
- **Konkret uj target:** `linuxcnc_qtplasmac / basic_manual_material_rs274ngc`.

## 8) Advisory notes

- A timing/feed/kerf parameter konyvtar nem resze ennek a tasknak; a `config_jsonb` csak szuk adapter-konfig blokkokat tartalmaz.
- A smoke in-memory fixture-oket hasznal, nem valos Supabase/HTTP utvonalat.
- Az adapter idempotens: ujrafutaskor a korabbi `machine_program` artifactokat per-target legacy type alapjan torol es ujrairja.
- A ket target (Hypertherm + QtPlasmaC) egymas mellett mukodik, nem zavarja egymast.

## 9) Follow-ups

- Tovabbi celgep-csalad adapterek kulon taskban.
- Valos Supabase integracio teszt az adapter-pathra.
- Frontend export UI bekotes a `machine_program` artifactokhoz.
- Kesobbi `M190`/`M66` auto material-change QtPlasmaC adapter kulon taskban.
