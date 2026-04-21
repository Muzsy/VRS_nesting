PASS_WITH_NOTES

## 1) Meta
- Task slug: `dxf_prefilter_e3_t3_geometry_import_gate_integration`
- Kapcsolódó canvas: `canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- Kapcsolódó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t3_geometry_import_gate_integration.yaml`
- Futás dátuma: `2026-04-21`
- Branch / commit: `main@022c12d`
- Fókusz terület: `Backend (preflight runtime gate + upload route trigger cleanup)`

## 2) Scope

### 2.1 Cél
- A `complete_upload` route-ból a közvetlen geometry import trigger eltávolítása source DXF finalize esetén.
- A geometry import gate bekötése a meglévő preflight runtime végére, persisted acceptance outcome alapján.
- A geometry import inputjának átállítása a persisted `normalized_dxf` artifact storage truth-ra.
- A meglévő geometry import pipeline megtartása minimális helper-boundary nyitással.
- Determinisztikus unit + smoke bizonyíték a gate szemantikára.

### 2.2 Nem-cél (explicit)
- Új FastAPI endpoint, review workflow, replace/rerun flow, feature flag, UI.
- Új migration vagy külön DB lifecycle status az `imported` bridge miatt.
- Geometry import pipeline duplikálása.
- Explicit preflight artifact list/url/download API.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok
- Backend route:
  - `api/routes/files.py`
- Backend runtime:
  - `api/services/dxf_preflight_runtime.py`
- Backend geometry import service:
  - `api/services/dxf_geometry_import.py`
- Teszt / smoke:
  - `tests/test_dxf_preflight_geometry_import_gate.py`
  - `scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py`
- Codex artefaktok:
  - `codex/codex_checklist/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
  - `codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`

### 3.2 Miért változtak?
A korábbi E3-T2 integrációban a route még közvetlenül a nyers source DXF-re indította a geometry importot, ami megkerülte a preflight acceptance gate-et. Az E3-T3 a trigger helyét áthelyezi a preflight runtime végére, ahol már rendelkezésre áll a persisted acceptance outcome és a `normalized_dxf` artifact ref.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`

### 4.2 Opcionális, feladatfüggő parancsok
- `python3 -m py_compile api/services/dxf_preflight_runtime.py api/services/dxf_geometry_import.py api/routes/files.py tests/test_dxf_preflight_geometry_import_gate.py scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py`
- `python3 -m pytest -q tests/test_dxf_preflight_runtime.py tests/test_dxf_preflight_geometry_import_gate.py` → `17 passed`
- `python3 scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py` → all scenarios passed

### 4.3 Ha valami kimaradt
- Nincs kihagyott kötelező ellenőrzés.
- A `verify.sh` lefutott, de FAIL lett egy pre-existing nesting-engine canonical JSON determinism mismatch miatt (`[RUN] deterministic smoke (10 runs)`), amely nem az E3-T3 route/runtime/geometry-import-gate módosításokból ered.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
| --- | --- | --- | --- | --- |
| A `complete_upload` route source DXF esetén már nem indít közvetlen geometry import background taskot. | PASS | `api/routes/files.py:252`; `tests/test_dxf_preflight_geometry_import_gate.py:187` | A route source DXF ágban már csak 2 `background_tasks.add_task(...)` hívás maradt (validate + preflight). A route teszt explicit ellenőrzi, hogy nincs `import_source_dxf_geometry_revision_async`. | `python3 -m pytest -q tests/test_dxf_preflight_geometry_import_gate.py` |
| A preflight runtime csak `accepted_for_import` esetén triggerel geometry importot. | PASS | `api/services/dxf_preflight_runtime.py:359`; `tests/test_dxf_preflight_geometry_import_gate.py:110` | A runtime a persisted `acceptance_outcome` alapján gate-el: csak `accepted_for_import` folytatódik import triggerrel. | `python3 -m pytest -q tests/test_dxf_preflight_geometry_import_gate.py` |
| A trigger a persisted `normalized_dxf` artifact storage truth-ot használja, nem a nyers source DXF-et. | PASS | `api/services/dxf_preflight_runtime.py:370`; `api/services/dxf_preflight_runtime.py:395`; `tests/test_dxf_preflight_geometry_import_gate.py:120` | A runtime a persisted `artifact_refs` listából keresi a `normalized_dxf` ref-et, és annak `storage_bucket`/`storage_path` értékeit adja át az import helpernek. | `python3 -m pytest -q tests/test_dxf_preflight_geometry_import_gate.py` |
| A legacy `validate_dxf_file_async(...)` task bent marad secondary signalként. | PASS | `api/routes/files.py:253` | A route DXF ága továbbra is regisztrálja a legacy readability validation taskot. | `python3 scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py` |
| A geometry import pipeline nincs duplikálva; csak minimális helper/gate integration készül. | PASS | `api/services/dxf_geometry_import.py:202`; `api/services/dxf_geometry_import.py:294` | A pipeline logika egy generic storage-backed helperbe került, a korábbi source wrapper erre delegál; nincs új párhuzamos import lánc. | `python3 -m py_compile ...` |
| Determinisztikus unit teszt és smoke bizonyítja a gate szemantikát. | PASS | `tests/test_dxf_preflight_geometry_import_gate.py:110`; `scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py:120` | A unit teszt lefedi az accepted/rejected/review/missing-artifact + import exception + route task-regisztráció ágakat; a smoke ugyanezeket scenario szinten lefuttatja. | `pytest` + `smoke` parancsok |
| A standard repo gate wrapperrel fut és a report evidence alapon frissül. | PASS_WITH_NOTES | `codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.verify.log` | A wrapper lefutott és frissítette az AUTO_VERIFY blokkot; az eredmény FAIL a pre-existing canonical JSON determinism smoke miatt. | `./scripts/verify.sh --report ...` |

## 6) Külön kiemelések (run.md követelmények)

- Miért kellett kivenni a geometry importot a route-ból: a route-ból indított nyers source import megkerülte a T6 acceptance gate-et, így a preflight verdict gyakorlati hatása nem érvényesült.
- Hogyan kapcsolódik a gate a persisted acceptance outcome-hoz: a runtime a `persist_preflight_run(...)` visszatérési shape-jéből olvassa az `acceptance_outcome` értéket, és ennek alapján dönt import/skip ágról.
- Miért a `normalized_dxf` artifact a bemenet: ez az E3-T1 persistence által rögzített canonical artifact truth; ezért nincs raw source fallback accepted outcome mellett sem.
- Hogyan marad bent a legacy validation: a route DXF ágában a `validate_dxf_file_async(...)` változatlanul háttértask marad secondary readability jelként.
- Import failure boundary: a runtime az import helper kivételeit `warning` loggal elnyeli, így nem törik el a `complete_upload` HTTP választ.
- Mi marad későbbi scope-ban: E3-T4 replace/rerun flow, E3-T5 feature flag/rollout gate, explicit preflight API/artifact URL/download/review-decision/UI.

## 7) Advisory notes
- A kötelező `verify.sh` futás FAIL-lel zárt, de a hiba forrása ugyanaz a pre-existing nesting-engine canonical JSON determinism mismatch (`run 1` vs `run 4`), amely az E3-T3-ban módosított Python route/runtime/import-gate kódtól független.
- A runtime az import helper hibáit szándékosan swallow-olja (`warning` loggal), így V1-ben nincs retry/polling orchestration. Ez a task scope része.
- A gate `persist_preflight_run(...)` visszatérési shape-re épít (`acceptance_outcome`, `artifact_refs`); ha ennek szerződése változik, az E3-T3 gate helper együtt frissítendő.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **FAIL**
- check.sh exit kód: `1`
- futás: 2026-04-21T21:44:28+02:00 → 2026-04-21T21:47:08+02:00 (160s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.verify.log`
- git: `main@022c12d`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/routes/files.py                   |  13 ----
 api/services/dxf_geometry_import.py   |  29 ++++++++-
 api/services/dxf_preflight_runtime.py | 108 ++++++++++++++++++++++++++++++++++
 3 files changed, 136 insertions(+), 14 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M api/services/dxf_geometry_import.py
 M api/services/dxf_preflight_runtime.py
?? canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t3_geometry_import_gate_integration.yaml
?? codex/prompts/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration/
?? codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md
?? codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.verify.log
?? scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py
?? tests/test_dxf_preflight_geometry_import_gate.py
```

**FAIL tail (utolsó ~60 sor a logból)**

```text
     Running tests/nfp_regression.rs (rust/nesting_engine/target/debug/deps/nfp_regression-5131f86e54918046)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 3 filtered out; finished in 0.00s

     Running tests/orbit_next_event_trace_smoke.rs (rust/nesting_engine/target/debug/deps/orbit_next_event_trace_smoke-5826a14285065327)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.00s

[NEST] Baseline nesting_engine smoke
[NEST][SA] CLI end-to-end smoke
[OK] SA CLI smoke passed: runs=3, determinism_hash=sha256:7232a5a9eb996e567bf857e832ed0cbeee7d39992503579a959cc72329422cd6, sheets_used=1
[NEST][F3-2] part-in-part pipeline smoke
[OK] part-in-part smoke passed: baseline_sheets=2, auto_sheets=1, auto_hash=sha256:90d59df438712f6c5e29071f6c2da7d48f0e108bd9f569486015bb66782b3220
[NEST][H3-T8] deterministic compaction post-pass smoke
[OK] T8 compaction smoke passed: slide_hash=sha256:07bbbf55cd68620a0248110a69fe60d7d72c5d81894e190d34b84cc78171901d, moved=2, extent_delta_mm=(w=-1.599998, h=0.000000), remnant_delta_ppm=-6570
[NEST] hash OK: sha256:4be7b018524e800c128d7da...
[NEST] determinism OK
[NEST] placer=nfp fallback smoke (holes/hole_collapsed -> blf)
warning: --placer nfp fallback to blf (hybrid gating: holes or hole_collapsed)
[NEST] placer=nfp fallback hash OK
[NEST] placer=nfp noholes determinism smoke
[NEST] placer=nfp noholes determinism OK
[NEST][F0] no-worse-than-BLF basic check
[NEST][F0] no-worse-than-BLF OK: nfp=2, blf=2
[NEST][F1] wrapper contract smoke (placed>=1)
[NEST][F1] wrapper contract OK: placed=1
[NEST][F2] touching stress smoke (placed>=1)
[NEST][F2] touching stress OK: placed=3
[NEST][F3] rotation coverage (critical part must be 90 deg)
[NEST][F3] rotation coverage OK: critical part rotation=90
[NEST][F0] placer=nfp determinism gate (3x hash)
[NEST][F0] determinism 3x OK: sha256:b02aeb912a939c5c495c4f97bd55f13dfae1da0cf66165924059e66053e88d4e
[NEST][F4] CFR order hardening determinism gate (3x hash)
[NEST][F4] determinism 3x OK: sha256:18430e4b2122f04c58635031692d77e9e58b08fdeda152c2cbc78164837fb8e5
[NEST][F2-3] NFP placer stats/perf counter gate
[CHECK] f0_sanity: PASS (stats <= baseline max)
[CHECK] f4_cfr_order: PASS (stats <= baseline max)
[OK] NFP placer stats/perf gate passed
[NEST] 0 out-of-bounds OK, placed=10
[NEST] Validator FAIL smoke (expected non-zero on overlap fixture)
FAIL: overlap detected: sheet=0 rect_100x50#0 vs rect_100x50#1
[NEST] Validator PASS smoke (baseline output)
PASS: nesting_engine_v2 solution is valid
 input=/home/muszy/projects/VRS_nesting/poc/nesting_engine/sample_input_v2.json
 output=/tmp/nesting_engine_baseline_out_smcGk4.json
[NEST] CLI smoke (nest-v2)
[nesting-engine-runner] run_dir=/home/muszy/projects/VRS_nesting/runs/20260421T194658Z_d9834691
[nesting-engine-runner] cmd=/home/muszy/projects/VRS_nesting/rust/nesting_engine/target/release/nesting_engine nest
[NEST] CLI determinism OK
[NEST] Canonical JSON determinism smoke
[BUILD] nesting_engine release
    Finished `release` profile [optimized] target(s) in 0.06s
[RUN] deterministic smoke (10 runs)
ERROR: determinism mismatch between run 1 and run 4
  baseline: /tmp/nesting_engine_determinism_baseline.json
  mismatched: /tmp/nesting_engine_determinism_mismatch.json
```

<!-- AUTO_VERIFY_END -->
