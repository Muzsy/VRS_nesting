# Report — dxf_prefilter_e3_t5_feature_flag_and_rollout_gate

**Státusz:** PASS

## 1) Meta

- **Task slug:** `dxf_prefilter_e3_t5_feature_flag_and_rollout_gate`
- **Kapcsolódó canvas:** `canvases/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.yaml`
- **Futás dátuma:** 2026-04-23
- **Branch / commit:** main
- **Fókusz terület:** Mixed (Backend config/route + Frontend build-time gate)

## 2) Scope

### 2.1 Cél

- Env-level canonical backend feature flag (`API_DXF_PREFLIGHT_REQUIRED`) bevezetése a `Settings` rétegben.
- Flag OFF esetén a `complete_upload` source DXF finalize legacy direct geometry import fallbackra áll vissza.
- A `replace_file` route feature OFF esetén gate-elve van.
- Build-time Vite mirror flag (`VITE_DXF_PREFLIGHT_ENABLED`) a frontend DXF Intake route/CTA kapuzásához.
- Task-specifikus unit teszt és smoke.

### 2.2 Nem-cél

- Project-level persisted rollout mező vagy migration.
- Runtime API config endpoint a frontendnek.
- DxfIntakePage belső fallback UX újraírása.
- Review/download/artifact route scope.
- E4-T5/T6/T7 UX.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **API config:**
  - `api/config.py`
- **API route:**
  - `api/routes/files.py`
- **Frontend:**
  - `frontend/src/lib/featureFlags.ts` (új)
  - `frontend/src/App.tsx`
  - `frontend/src/pages/ProjectDetailPage.tsx`
- **Tesztek:**
  - `tests/test_dxf_preflight_feature_flag_gate.py` (új)
  - `scripts/smoke_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.py` (új)
- **Codex artefaktok:**
  - `codex/codex_checklist/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
  - `codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`

### 3.2 Miért változtak?

**API config:** A `Settings` dataclass kap egy `dxf_preflight_required: bool` mezőt, amely az `API_DXF_PREFLIGHT_REQUIRED` env var-ból töltődik (alias: `DXF_PREFLIGHT_REQUIRED`), default: `True`.

**API route:** A `complete_upload` source DXF branch flag-alapon választ a `run_preflight_for_upload` és az `import_source_dxf_geometry_revision_async` között. A `replace_file` route flag OFF esetén 409-et dob.

**Frontend:** Új `featureFlags.ts` helper a `VITE_DXF_PREFLIGHT_ENABLED` build-time flag olvasásához. App.tsx és ProjectDetailPage.tsx a flagtől függ.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md` → **PASS**
- `python3 -m pytest tests/test_dxf_preflight_feature_flag_gate.py -v` → 22 passed
- `python3 scripts/smoke_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.py` → ALL SCENARIOS PASSED

## 5) Miért env-level canonical gate a helyes current-code V1 irány

A repoban nincs project-level settings domain és nincs runtime API config endpoint a frontendnek. Az egyetlen current-code grounded megoldás ezért egy env-level backend gate, amely a meglévő `Settings` rétegbe illeszkedik — az összes többi `API_*` bool flag (pl. `API_ENABLE_SECURITY_HEADERS`) ugyanezt a mintát követi. Project-level rollout gate egy jövőbeli scope, amely külön migration és settings domain létrehozását igényelné.

## 6) Hogyan tér vissza a rendszer legacy direct geometry import útra

Az `import_source_dxf_geometry_revision_async` helper már a repoban van (E2/H1 origin). A `complete_upload` source DXF branch flag OFF esetén ezt hívja meg background taskként a `run_preflight_for_upload` helyett. A fallback logika nem duplikálódik a route-ban — csak a meglévő helper kap background task hívást.

## 7) Miért gate-elt replacement flow a helyes rollout szemantika

Ha a prefilter lane ki van kapcsolva, a `replace_file` route egy replacement upload slotot nyitna meg, amelynek `complete_upload` finalize-ja ezután a legacy geometry import utat járná be. Ez ellentmondana a replacement flow céljának (preflight újrafuttatás), és félrevezető állapotba hozná a rendszert. Ezért flag OFF esetén a replace route 409 Conflict hibával válaszol, nem nyit upload slotot.

## 8) Miért build-time mirror flag a frontend visibility gate

A repoban nincs runtime config API endpoint a frontendnek. Az egyetlen current-code V1 megoldás egy Vite build-time env var (`VITE_DXF_PREFLIGHT_ENABLED`), amely szinkronban van a backend `API_DXF_PREFLIGHT_REQUIRED` flag-gel. Ez nem egy új product domain — csak minimális rollout visibility kapu a DXF Intake route/CTA kapuzásához.

## 9) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Kapcsolódó teszt |
|---|---|---|---|
| `Settings` kap `dxf_preflight_required: bool` | PASS | `api/config.py:54` | `test_settings_dxf_preflight_required_*` (15 test) |
| Flag ON: `complete_upload` validate + preflight task | PASS | `api/routes/files.py:562-584` | `test_complete_upload_flag_on_registers_preflight_task` |
| Flag OFF: `complete_upload` validate + legacy import task | PASS | `api/routes/files.py:585-597` | `test_complete_upload_flag_off_registers_legacy_import_task` |
| Flag OFF: `replace_file` gate-elve (HTTP 409) | PASS | `api/routes/files.py:700-705` | `test_replace_file_flag_off_raises_http_error` |
| DXF Intake route/CTA frontend gate | PASS | `frontend/src/lib/featureFlags.ts`, `App.tsx:23`, `ProjectDetailPage.tsx:212-218` | smoke scenario 1–4 |
| Nincs új project settings domain vagy migration | PASS | migration fájl nem jött létre | — |
| Unit teszt + smoke elkészült | PASS | `tests/test_dxf_preflight_feature_flag_gate.py` (22 test), `scripts/smoke_dxf_prefilter_e3_t5_*.py` (4 scenario) | — |
| `./scripts/verify.sh` PASS | PASS | AUTO_VERIFY_START blokk: **PASS**, exit 0 | — |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-23T21:54:07+02:00 → 2026-04-23T21:56:56+02:00 (169s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.verify.log`
- git: `main@733eef4`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 api/config.py                                      |  6 +++
 api/routes/files.py                                | 46 ++++++++++++++++------
 frontend/src/App.tsx                               |  3 +-
 frontend/src/pages/ProjectDetailPage.tsx           | 17 ++++----
 tests/test_dxf_preflight_api_end_to_end.py         |  2 +-
 tests/test_dxf_preflight_geometry_import_gate.py   |  2 +-
 tests/test_dxf_preflight_replace_flow.py           |  1 +
 ...est_project_file_complete_preflight_settings.py |  2 +-
 8 files changed, 55 insertions(+), 24 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/config.py
 M api/routes/files.py
 M frontend/src/App.tsx
 M frontend/src/pages/ProjectDetailPage.tsx
 M tests/test_dxf_preflight_api_end_to_end.py
 M tests/test_dxf_preflight_geometry_import_gate.py
 M tests/test_dxf_preflight_replace_flow.py
 M tests/test_project_file_complete_preflight_settings.py
?? canvases/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.yaml
?? codex/prompts/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate/
?? codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md
?? codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.verify.log
?? frontend/src/lib/featureFlags.ts
?? scripts/smoke_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.py
?? tests/test_dxf_preflight_feature_flag_gate.py
```

<!-- AUTO_VERIFY_END -->
