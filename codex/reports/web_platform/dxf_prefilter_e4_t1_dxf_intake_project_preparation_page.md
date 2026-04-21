PASS_WITH_NOTES

## 1) Meta
- Task slug: `dxf_prefilter_e4_t1_dxf_intake_project_preparation_page`
- Kapcsolódó canvas: `canvases/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- Kapcsolódó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.yaml`
- Futás dátuma: `2026-04-21`
- Branch / commit: `main@c41b31d`
- Fókusz terület: `Mixed (Frontend + Backend read-model)`

## 2) Scope

### 2.1 Cél
- Külön DXF Intake / Project Preparation oldal és route bevezetése.
- Backend oldalon optional file-list preflight summary projection (`include_preflight_summary=true`) hozzáadása.
- Frontend API/types boundary bővítése az optional latest summary mezőhöz.
- ProjectDetail oldalon explicit intake CTA hozzáadása a legacy flow megtartásával.
- Determinisztikus backend unit teszt és smoke bizonyíték készítése.

### 2.2 Nem-cél (explicit)
- NewRunPage prefilter funkciókkal történő bővítése.
- Diagnostics drawer / review modal / replace-rerun / feature flag scope.
- Teljes preflight-runs API család bevezetése.
- Rules-profile settings editor teljes implementációja (E4-T2 scope).

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok
- Backend:
  - `api/routes/files.py`
- Frontend:
  - `frontend/src/lib/types.ts`
  - `frontend/src/lib/api.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/pages/DxfIntakePage.tsx`
  - `frontend/src/pages/ProjectDetailPage.tsx`
- Tesztek / smoke:
  - `tests/test_project_files_preflight_summary.py`
  - `scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py`
- Codex artefaktok:
  - `codex/codex_checklist/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
  - `codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`

### 3.2 Miért változtak?
A backend E3 után már automatikus upload→preflight láncot futtat, de ennek nem volt dedikált frontend belépési pontja. Az E4-T1 ehhez új intake oldalt és minimális read-modelt ad úgy, hogy a legacy NewRun wizard scope-ja érintetlen maradjon, és a meglévő file-list fogyasztók kompatibilitása is megmaradjon.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`

### 4.2 Opcionális, feladatfüggő parancsok
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_summary.py scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py` → OK
- `python3 -m pytest -q tests/test_project_files_preflight_summary.py` → `4 passed`
- `python3 scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py` → all scenarios passed
- `npm --prefix frontend run build` → success (`tsc -b && vite build`)

### 4.3 Ha valami kimaradt
- Nincs kihagyott kötelező ellenőrzés.
- A `verify.sh` lefutott, de FAIL lett egy pre-existing nesting-engine canonical JSON determinism mismatch miatt (`[RUN] deterministic smoke (10 runs)`), amely nem az E4-T1 frontend/API projection módosításokból ered.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
| --- | --- | --- | --- | --- |
| Létrejött külön `DXF Intake / Project Preparation` oldal és route. | PASS | `frontend/src/App.tsx:23`; `frontend/src/pages/DxfIntakePage.tsx:98` | Az App routerben új útvonal van: `/projects/:projectId/dxf-intake`, a page pedig külön komponensként megjelent. | `python3 scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py` |
| Az új oldal canonical `source_dxf` upload nyelvezetet használ. | PASS | `frontend/src/pages/DxfIntakePage.tsx:157`; `frontend/src/pages/DxfIntakePage.tsx:176`; `frontend/src/pages/DxfIntakePage.tsx:256` | A signed URL és finalize hívások `file_type: "source_dxf"` értékkel mennek, és UI szövegben is Source DXF terminológia szerepel. | `npm --prefix frontend run build` |
| Az oldal explicit kommunikálja, hogy a preflight automatikusan indul upload után. | PASS | `frontend/src/pages/DxfIntakePage.tsx:258`; `frontend/src/pages/DxfIntakePage.tsx:192` | Az intake oldal kimondja az auto-preflight működést és a completion státuszban is ezt jelzi. | `python3 scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py` |
| A `ProjectDetailPage`-ról van egyértelmű belépési pont az intake oldalra. | PASS | `frontend/src/pages/ProjectDetailPage.tsx:210` | Új CTA gomb navigál a `/projects/:projectId/dxf-intake` oldalra, a legacy New run wizard megtartása mellett. | `python3 scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py` |
| A file-list endpoint minimal latest preflight summary projectiont tud adni optional kapcsolóval. | PASS | `api/routes/files.py:331`; `api/routes/files.py:350`; `api/routes/files.py:115` | Bevezetett optional query param: `include_preflight_summary`; true esetén per-file legfrissebb summary merge-elődik minimális mezőkkel. | `python3 -m pytest -q tests/test_project_files_preflight_summary.py` |
| A frontend types/api boundary támogatja az új summary shape-et. | PASS | `frontend/src/lib/types.ts:39`; `frontend/src/lib/api.ts:62`; `frontend/src/lib/api.ts:168` | Új optional `ProjectFileLatestPreflightSummary` típus és normalizáló került be, valamint a list helper tudja a query kapcsolót. | `npm --prefix frontend run build` |
| A page file-szintű statuszlistát jelenít meg, de nem nyitja meg a diagnostics/review/settings részletes scope-ot. | PASS | `frontend/src/pages/DxfIntakePage.tsx:295`; `frontend/src/pages/DxfIntakePage.tsx:289` | Csak latest státusz tábla és read-only defaults blokk van; nincs diagnostics drawer, review modal vagy settings editor. | `python3 scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py` |
| A task-specifikus backend teszt és smoke bizonyítja a minimal UI-enabling szerződést. | PASS | `tests/test_project_files_preflight_summary.py:78`; `scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py:76` | A pytest lefedi false/true/missing/latest/optional mező ágakat; smoke ellenőrzi projection contractot, intake route-ot és ProjectDetail CTA-t. | `pytest` + smoke parancsok |
| A standard repo gate wrapperrel fut és a report evidence alapon frissül. | PASS_WITH_NOTES | `codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.verify.log` | A wrapper lefutott és frissítette az AUTO_VERIFY blokkot; az eredmény FAIL a pre-existing canonical JSON determinism mismatch miatt. | `./scripts/verify.sh --report ...` |

## 6) Külön kiemelések (run.md követelmények)
- Miért kellett külön intake oldal, és miért nem NewRunPage foltozás: a `NewRunPage.tsx` továbbra is run wizard scope-ban marad; az intake oldal külön ingest/preparation entrypointot ad a prefilter flow-hoz.
- Auto-preflight truth megjelenése: az intake oldalon explicit szöveg jelzi, hogy upload finalize után automatikusan indul a preflight, nincs manuális start gomb.
- Miért csak optional file-list summary projection készült: a feladat minimális page-enabling read-modelt kér; teljes preflight-runs API family nincs nyitva.
- ProjectDetail kompatibilitás: a meglévő oldal és gombok megmaradtak, csak új intake CTA került be.
- Backend unit teszt + smoke lefedettség: a projection branch-ek és a route/CTA jelenlét is determinisztikusan ellenőrzött.
- Mi marad későbbi scope-ban: E4-T2 settings editor, E4-T3 részletes runs/badges, E4-T4 diagnostics/review UI.

## 7) Advisory notes
- A file-list projection a legfrissebb run kiválasztásához a `run_seq.desc` rendezésre támaszkodik; ez a jelenlegi E3 persistence modellhez illeszkedik.
- Az intake oldal szándékosan read-only defaults blokkot ad a settings helyett; ez E4-T2-ben bővíthető editorra.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **FAIL**
- check.sh exit kód: `1`
- futás: 2026-04-21T22:15:37+02:00 → 2026-04-21T22:18:19+02:00 (162s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.verify.log`
- git: `main@c41b31d`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 api/routes/files.py                      | 71 +++++++++++++++++++++++++++++++-
 frontend/src/App.tsx                     |  2 +
 frontend/src/lib/api.ts                  | 30 +++++++++++++-
 frontend/src/lib/types.ts                |  9 ++++
 frontend/src/pages/ProjectDetailPage.tsx |  7 ++++
 5 files changed, 115 insertions(+), 4 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M frontend/src/App.tsx
 M frontend/src/lib/api.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/ProjectDetailPage.tsx
?? canvases/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.yaml
?? codex/prompts/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page/
?? codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md
?? codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.verify.log
?? frontend/src/pages/DxfIntakePage.tsx
?? scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py
?? tests/test_project_files_preflight_summary.py
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
 output=/tmp/nesting_engine_baseline_out_NTxFkv.json
[NEST] CLI smoke (nest-v2)
[nesting-engine-runner] run_dir=/home/muszy/projects/VRS_nesting/runs/20260421T201807Z_22098675
[nesting-engine-runner] cmd=/home/muszy/projects/VRS_nesting/rust/nesting_engine/target/release/nesting_engine nest
[NEST] CLI determinism OK
[NEST] Canonical JSON determinism smoke
[BUILD] nesting_engine release
    Finished `release` profile [optimized] target(s) in 0.06s
[RUN] deterministic smoke (10 runs)
ERROR: determinism mismatch between run 1 and run 6
  baseline: /tmp/nesting_engine_determinism_baseline.json
  mismatched: /tmp/nesting_engine_determinism_mismatch.json
```

<!-- AUTO_VERIFY_END -->
