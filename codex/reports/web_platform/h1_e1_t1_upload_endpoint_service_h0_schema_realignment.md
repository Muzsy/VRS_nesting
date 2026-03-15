PASS

## 1) Meta
- Task slug: `h1_e1_t1_upload_endpoint_service_h0_schema_realignment`
- Kapcsolodo canvas: `canvases/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.yaml`
- Futas datuma: `2026-03-15`
- Branch / commit: `main @ 8f81ca1 (dirty working tree)`
- Fokusz terulet: `API + Storage contract + Smoke`

## 2) Scope

### 2.1 Cel
- A `projects` endpointek H0 `app.projects` truth-ra igazítása (`owner_user_id`, `lifecycle`).
- A `files` endpointek H0 `app.file_objects` truth-ra igazítása.
- A source upload path policy H0-kanonikus mintára váltása.
- Legacy `project_files`/`owner_id`/`archived_at` upload-flow függés kivezetése.
- Task-specifikus smoke script biztosítása a H0-aligned flow bizonyítására.

### 2.2 Nem-cel
- Geometry import/revision pipeline tényleges bekötése.
- Új domain migráció bevezetése.
- Run/queue/worker réteg módosítása.
- Teljes legacy phase1/phase2 takarítás.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Task artefaktok:**
  - `canvases/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.yaml`
  - `codex/prompts/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment/run.md`
  - `codex/codex_checklist/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
  - `codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
- **API / service:**
  - `api/routes/projects.py`
  - `api/routes/files.py`
  - `api/services/dxf_validation.py`
  - `api/config.py`
- **Smoke:**
  - `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py`

### 3.2 Miert valtoztak?
- A route-ok eddig legacy phase1 táblákra és mezőkre támaszkodtak, ez nem volt H0 source-of-truth kompatibilis.
- A módosítások célja a H1 ingest belépési pontok H0 modellhez igazítása minimális invazivitással.
- A smoke script feladata a H0-aligned endpoint viselkedés automatikus regresszióellenőrzése.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md` -> PASS

### 4.2 Opcionális, feladatfuggo ellenorzes
- `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` -> PASS
- `python3 -m py_compile api/routes/projects.py api/routes/files.py api/services/dxf_validation.py api/config.py scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` -> PASS

### 4.3 Ha valami kimaradt
- Nincs kihagyott kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| A `projects` endpointok H0-s `app.projects` mezőkre épülnek. | PASS | `api/routes/projects.py:26`; `api/routes/projects.py:67`; `api/routes/projects.py:83`; `api/routes/projects.py:159` | A response és CRUD filter/payload is `owner_user_id`+`lifecycle` mezőkkel és `app.projects` táblával működik. | `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` |
| A `files` endpointok H0-s `app.file_objects` mezőkre épülnek. | PASS | `api/routes/files.py:55`; `api/routes/files.py:140`; `api/routes/files.py:214`; `api/routes/files.py:254`; `api/routes/files.py:291` | A file flow `app.file_objects` mezőkön és táblán ír/olvas/töröl. | `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` |
| A source upload path a H0 storage policy szerinti `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}` mintát használja. | PASS | `api/routes/files.py:163`; `api/routes/files.py:198`; `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py:294` | Upload-url és complete ellenőrzés is a kanonikus prefixet használja, smoke explicit validálja. | `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` |
| Az upload flow nem használja többé a `project_files` táblát. | PASS | `api/routes/files.py:140`; `api/routes/files.py:228`; `api/routes/files.py:259`; `api/routes/files.py:292`; `api/services/dxf_validation.py:14` | Files route és validation helper sem referál `project_files` táblára. | `rg -n "project_files" api/routes/files.py api/services/dxf_validation.py` |
| Az upload flow nem használja többé a `owner_id` vagy `archived_at` mezőlogikát. | PASS | `api/routes/projects.py:28`; `api/routes/projects.py:89`; `api/routes/projects.py:159`; `api/routes/files.py:118` | `owner_user_id` + `lifecycle` logika váltotta a legacy ownership/archive mezőket. | `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` |
| A DXF validációs háttérhívás nem próbál nem létező legacy oszlopokat frissíteni. | PASS | `api/services/dxf_validation.py:14`; `api/services/dxf_validation.py:38` | A helper csak letöltés+parse+log, nincs DB update `validation_status`/`validation_error` mezőkre. | `python3 -m py_compile api/services/dxf_validation.py` |
| Készül task-specifikus smoke script, ami bizonyítja a H0-aligned project + upload flow működését. | PASS | `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py:1`; `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py:244`; `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py:353` | A script endpoint-szinten végigfuttatja project create/archive + upload-url + complete/list/delete flowt H0 mezőkkel. | `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` |
| A checklist és report evidence-alapon ki van töltve. | PASS | `codex/codex_checklist/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md:1`; `codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md:1` | A checklist pipálhatóan, a report DoD->Evidence táblával készült. | Kézi ellenőrzés |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md` PASS. | PASS | `codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.verify.log:1` | Kötelező gate wrapperrel futtatva, AUTO_VERIFY blokk frissült. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A `files` complete request-ben megmaradt minimális backward-compat mezőkezelés (`file_type`, `storage_key`) csak request oldali átmeneti mappingként, DB-ben már kizárólag H0 mezőkbe ír.
- A run/runs_configs endpointok a repó más taskjaihoz tartozó legacy `project_files` referenciái ebben a taskban tudatosan out-of-scope.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-15T16:17:59+01:00 → 2026-03-15T16:21:27+01:00 (208s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.verify.log`
- git: `main@8f81ca1`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/config.py                  |   2 +-
 api/routes/files.py            | 154 +++++++++++++++++++++++++----------------
 api/routes/projects.py         |  46 ++++++------
 api/services/dxf_validation.py |  33 ++++-----
 4 files changed, 131 insertions(+), 104 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/config.py
 M api/routes/files.py
 M api/routes/projects.py
 M api/services/dxf_validation.py
?? canvases/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md
?? codex/codex_checklist/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.yaml
?? codex/prompts/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment/
?? codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md
?? codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.verify.log
?? scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py
```

<!-- AUTO_VERIFY_END -->
