PASS

## 1) Meta
- Task slug: `dxf_prefilter_e4_t2_preflight_settings_panel`
- Kapcsolódó canvas: `canvases/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
- Kapcsolódó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t2_preflight_settings_panel.yaml`
- Futás dátuma: `2026-04-21`
- Branch / commit: `main@9d12536`
- Fókusz terület: `Mixed (Frontend + Backend preflight bridge)`

## 2) Scope

### 2.1 Cél
- A DXF Intake oldalon valódi, szerkeszthető preflight settings panel bevezetése.
- Frontend upload finalize payload optional `rules_profile_snapshot_jsonb` bridge bekötése.
- Backend `complete_upload` route optional snapshot fogadása és runtime task felé továbbítása.
- Runtime pipeline `rules_profile=None` hardcode megszüntetése, tényleges rules-profile plumbing.
- Determinisztikus unit + smoke bizonyíték készítése a panel -> payload -> route -> runtime láncra.

### 2.2 Nem-cél (explicit)
- Named rules-profile CRUD, profile lista, owner/version domain.
- Project-level persisted settings API.
- `canonical_layer_colors` teljes editor.
- Diagnostics drawer / review modal / detailed runs table / accepted->parts flow / replace-rerun.
- `NewRunPage.tsx` legacy wizard bővítése.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok
- Backend:
  - `api/routes/files.py`
  - `api/services/dxf_preflight_runtime.py`
- Frontend:
  - `frontend/src/pages/DxfIntakePage.tsx`
  - `frontend/src/lib/api.ts`
  - `frontend/src/lib/types.ts`
- Tesztek / smoke:
  - `tests/test_dxf_preflight_runtime.py`
  - `tests/test_project_file_complete_preflight_settings.py`
  - `scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py`
- Codex artefaktok:
  - `codex/codex_checklist/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
  - `codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`

### 3.2 Miért változtak?
- Az E2 service-lánc már képes rules-profile mezőket fogyasztani, de az intake UI és upload-route eddig nem adott át snapshotot, ezért a runtime hardcoded `None` módban futott.
- Az E4-T2 minimális, current-code truth szerinti lépése ezért az upload-session szintű settings panel + payload bridge + runtime plumbing volt, teljes rules-profile domain nyitása nélkül.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`

### 4.2 Opcionális, feladatfüggő parancsok
- `python3 -m py_compile api/routes/files.py api/services/dxf_preflight_runtime.py tests/test_dxf_preflight_runtime.py tests/test_project_file_complete_preflight_settings.py scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py` → OK
- `python3 -m pytest -q tests/test_dxf_preflight_runtime.py tests/test_project_file_complete_preflight_settings.py` → `14 passed`
- `python3 scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py` → all scenarios passed
- `npm --prefix frontend run build` → success (`tsc -b && vite build`)

### 4.3 Ha valami kimaradt
- Nincs kihagyott kötelező vagy célzott ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
| --- | --- | --- | --- | --- |
| A `DxfIntakePage` read-only defaults blokkja valodi preflight settings panelre valtozott. | PASS | `frontend/src/pages/DxfIntakePage.tsx:367`; `frontend/src/pages/DxfIntakePage.tsx:499` | A page-en megjelent a szerkeszthető settings panel a minimális mezőkkel és a `Reset to defaults` művelettel. | `python3 scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py` |
| A panel minimal draft settings alakot tart fenn, deterministic backend-aligned defaults-szal. | PASS | `frontend/src/pages/DxfIntakePage.tsx:19`; `frontend/src/pages/DxfIntakePage.tsx:56`; `frontend/src/lib/types.ts:57` | Explicit draft/snapshot típus és validáló helper van; a defaultok a backend service-defaultokhoz igazodnak. | `npm --prefix frontend run build` |
| A panel altal hasznalt upload flow optional rules-profile snapshotot tud kuldeni a backendnek. | PASS | `frontend/src/pages/DxfIntakePage.tsx:245`; `frontend/src/lib/api.ts:152` | Upload finalize során az intake page optional `rules_profile_snapshot_jsonb` mezőt küld, API boundary típusosan támogatja. | `python3 scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py` |
| A `complete_upload` route optional snapshotot fogad es tovabbad a preflight runtime-nak. | PASS | `api/routes/files.py:43`; `api/routes/files.py:147`; `api/routes/files.py:332` | A request modell új optional mezőt fogad, route minimális JSON-serializability boundary után továbbadja a runtime tasknak. | `python3 -m pytest -q tests/test_project_file_complete_preflight_settings.py` |
| A runtime megszunteti a `rules_profile=None` hardcode-ot, es a snapshotot atvezeti az E2/T7 + persistence lancba. | PASS | `api/services/dxf_preflight_runtime.py:177`; `api/services/dxf_preflight_runtime.py:309`; `api/services/dxf_preflight_runtime.py:341` | A runtime signatura optional rules_profile-t kap, és azt role/gap/dedupe/writer/persist hívásokba továbbítja. | `python3 -m pytest -q tests/test_dxf_preflight_runtime.py` |
| A task nem vezet be named rules profile CRUD-ot vagy project-level settings persistence-t. | PASS | `api/routes/files.py:147`; `frontend/src/pages/DxfIntakePage.tsx:367` | Csak upload-session snapshot bridge készült; nincs profile lista/CRUD, nincs project-level settings endpoint. | Diff review + smoke |
| A task-specifikus backend unit teszt(ek) es smoke bizonyitjak a settings panel -> upload payload -> runtime plumbing szerzodest. | PASS | `tests/test_dxf_preflight_runtime.py:291`; `tests/test_project_file_complete_preflight_settings.py:67`; `scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py:116` | Runtime és route-level branch-ek determinisztikusan tesztelve, smoke lefedi UI/API/route/runtime szerződést. | `pytest` + smoke parancsok |
| A standard repo gate wrapperrel fut es a report evidence alapon frissul. | PASS | `codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.verify.log` | A `verify.sh` lefutott, `check.sh` exit kód `0`, AUTO_VERIFY blokk frissült. | `./scripts/verify.sh --report ...` |

## 6) Külön kiemelések (run.md követelmények)
- Miért a settings panel + upload payload bridge a helyes minimális lépés: a backend E2 service-ek már fogadnak rules-profile slice-ot, de route/runtime eddig nem kapott snapshotot, ezért az upload-session bridge adja a legkisebb működő bekötést domainnyitás nélkül.
- UI-ban befagyasztott defaultok:
  - `strict_mode=false`
  - `auto_repair_enabled=false`
  - `interactive_review_on_ambiguity=true`
  - `max_gap_close_mm=1.0`
  - `duplicate_contour_merge_tolerance_mm=0.05`
  - `cut_color_map=[]`
  - `marking_color_map=[]`
- Most user-facing módon bekötött rules-profile mezők:
  - `strict_mode`
  - `auto_repair_enabled`
  - `interactive_review_on_ambiguity`
  - `max_gap_close_mm`
  - `duplicate_contour_merge_tolerance_mm`
  - `cut_color_map`
  - `marking_color_map`
- Későbbi scope-ban marad:
  - `canonical_layer_colors` editor,
  - named profiles / profile CRUD,
  - project-level settings persistence,
  - diagnostics/review UI.

## 7) Advisory notes
- A route csak minimális mapping/JSON boundaryt validál; policy-részletek továbbra is az E2 service-ek normalizációjában maradnak.
- A legacy `validate_dxf_file_async(...)` secondary signal task változatlanul bent maradt a `complete_upload` flowban.
- A panel-szintű snapshot csak az innen indított új uploadokra érvényes, nem vezet be globális/projekt default állapotot.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-21T22:51:50+02:00 → 2026-04-21T22:54:31+02:00 (161s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.verify.log`
- git: `main@9d12536`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 api/routes/files.py                   |  23 ++++
 api/services/dxf_preflight_runtime.py |  17 ++-
 frontend/src/lib/api.ts               |   2 +
 frontend/src/lib/types.ts             |  20 ++++
 frontend/src/pages/DxfIntakePage.tsx  | 216 +++++++++++++++++++++++++++++++++-
 tests/test_dxf_preflight_runtime.py   |  42 ++++++-
 6 files changed, 311 insertions(+), 9 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M api/services/dxf_preflight_runtime.py
 M frontend/src/lib/api.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/DxfIntakePage.tsx
 M tests/test_dxf_preflight_runtime.py
?? canvases/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t2_preflight_settings_panel.yaml
?? codex/prompts/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel/
?? codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md
?? codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.verify.log
?? scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py
?? tests/test_project_file_complete_preflight_settings.py
```

<!-- AUTO_VERIFY_END -->
