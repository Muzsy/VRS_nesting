PASS

## 1) Meta
- Task slug: `h1_e3_t3_project_requirement_management_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e3_t3_project_requirement_management_h1_minimum.yaml`
- Futas datuma: `2026-03-19`
- Branch / commit: `main @ 89e3382 (dirty working tree)`
- Fokusz terulet: `API + Part requirement domain + Smoke`

## 2) Scope

### 2.1 Cel
- H1 minimum project-level `project_part_requirements` create-or-update workflow bevezetese.
- Projekt-owner es part-owner ellenorzes biztositasa write/list muveleteknel.
- Minimalis API contract biztositasa requirement upsert es listazas celra.
- Task-specifikus smoke script biztositasa a sikeres es hibas agakra.

### 2.2 Nem-cel (explicit)
- Run snapshot epites vagy solver-input aggregation.
- Sheet input workflow.
- Inventory/remnant/manufacturing scope.
- Frontend/UI valtoztatas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Task artefaktok:**
  - `canvases/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h1_e3_t3_project_requirement_management_h1_minimum.yaml`
  - `codex/prompts/web_platform/h1_e3_t3_project_requirement_management_h1_minimum/run.md`
  - `codex/codex_checklist/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`
  - `codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`
- **API / service:**
  - `api/services/project_part_requirements.py`
  - `api/routes/project_part_requirements.py`
  - `api/main.py`
- **Smoke:**
  - `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py`

### 3.2 Mit szallit le a task
- Kulon service reteget a `project_part_requirements` domain workflowhoz.
- Create-or-update viselkedest unique `(project_id, part_revision_id)` parra.
- Owner guardot projektre es part revisionhoz tartozo part definitionra.
- Minimalis listazo endpointot projekt requirement rekordokhoz.

### 3.3 Mit NEM szallit le a task
- Nem epit run snapshotot.
- Nem general solver payloadot.
- Nem kezel sheet inputokat.
- Nem ad inventory/remnant/manufacturing workflowt.

### 3.4 Plusz migracio / runtime fuggoseg
- Uj migracio nem kellett.
- Uj runtime-fuggoseg nem kellett.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md` -> PASS

### 4.2 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile api/services/project_part_requirements.py api/routes/project_part_requirements.py api/main.py scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py` -> PASS

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit project part requirement service a meglevo H0 truth fole. | PASS | `api/services/project_part_requirements.py:195` | Kulon service modul kezeli a project requirement workflowot. | Smoke + verify |
| A task a meglevo `app.project_part_requirements` tablara epul, nem legacy schema-ra. | PASS | `api/services/project_part_requirements.py:131`; `api/services/project_part_requirements.py:159`; `api/services/project_part_requirements.py:182`; `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql:49` | Service muveletek a H0 `app.project_part_requirements` truthot hasznaljak. | Smoke + kezi kodellenorzes |
| A service csak a user sajat projektjebe es sajat part revisionjaira enged rogziteni. | PASS | `api/services/project_part_requirements.py:65`; `api/services/project_part_requirements.py:85`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:270`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:282` | Projekt-owner es part-owner guard explicit, idegen branch-ek hibaval ternek vissza. | Task smoke |
| Uj `(project_id, part_revision_id)` parra uj `project_part_requirement` jon letre. | PASS | `api/services/project_part_requirements.py:252`; `api/services/project_part_requirements.py:254`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:214` | Nem letezo par eseten insert ag fut. | Task smoke create branch |
| Meglevo `(project_id, part_revision_id)` par eseten frissites tortenik, nem duplikalas. | PASS | `api/services/project_part_requirements.py:237`; `api/services/project_part_requirements.py:241`; `api/services/project_part_requirements.py:265`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:236` | Letezo rekord update-elodik; duplicate race is update-be fordul. | Task smoke update branch |
| A `required_qty`, `placement_priority`, `placement_policy`, `is_active`, `notes` H1 minimum szinten kezelheto. | PASS | `api/routes/project_part_requirements.py:24`; `api/services/project_part_requirements.py:32`; `api/services/project_part_requirements.py:44`; `api/services/project_part_requirements.py:56`; `api/services/project_part_requirements.py:174` | Request- es service-validacio, majd persistalas lefedi az elvart mezoket. | Task smoke invalid qty/priority/policy |
| Keszul minimalis API endpoint a create-or-update workflowhoz. | PASS | `api/routes/project_part_requirements.py:132`; `api/main.py:16`; `api/main.py:106` | `POST /v1/projects/{project_id}/part-requirements` endpoint bekotve. | Task smoke POST hivasok |
| Keszul minimalis listazo endpoint projekt requirementekhez. | PASS | `api/routes/project_part_requirements.py:159`; `api/services/project_part_requirements.py:305`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:263` | `GET` endpoint visszaadja a projekt requirement listat. | Task smoke list branch |
| Keszul task-specifikus smoke script a sikeres es hibas agakra. | PASS | `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:186`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:214`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:270`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:294`; `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py:319` | Script lefedi create/update/list/foreign project/foreign revision/invalid input agakat. | `python3 scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py` |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md:1`; `codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md:1` | Task checklist es report kitoltve. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.verify.log:1` | Kotelezo gate wrapperrel futtatva. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A task tudatosan csak project requirement truth managementre fokuszal, run/snapshot scope nelkul.
- A `placement_policy` bemenet explicit az `app.placement_policy` enum truth-ra van szukitve.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-19T00:51:25+01:00 → 2026-03-19T00:54:55+01:00 (210s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.verify.log`
- git: `main@89e3382`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/project_part_requirements.py
?? api/services/project_part_requirements.py
?? canvases/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e3_t3_project_requirement_management_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e3_t3_project_requirement_management_h1_minimum/
?? codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md
?? codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.verify.log
?? scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py
```

<!-- AUTO_VERIFY_END -->
