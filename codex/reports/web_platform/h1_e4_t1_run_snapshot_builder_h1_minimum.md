PASS

## 1) Meta
- Task slug: `h1_e4_t1_run_snapshot_builder_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml`
- Futas datuma: `2026-03-19`
- Branch / commit: `main @ 37006e9 (dirty working tree)`
- Fokusz terulet: `Run snapshot builder service + Smoke + Codex artefaktok`

## 2) Scope

### 2.1 Cel
- H1 minimum run snapshot builder service bevezetese explicit owner/project guarddal.
- Technology/part/sheet truth determinisztikus osszeolvasasa H0/H1 canonical tablavilagbol.
- H0 snapshot-structure kompatibilis payload eloallitasa stabil `snapshot_hash_sha256`-val.
- Task-specifikus smoke script keszitese sikeres es hibas agakra.

### 2.2 Nem-cel (explicit)
- `POST /runs` route atalakitasa vagy uj run route bevezetese.
- `app.nesting_runs`, `app.nesting_run_snapshots`, `app.run_queue` insert logika.
- Worker lease/retry, solver futtatas, result normalizer, artifact workflow.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Task artefaktok:**
  - `canvases/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml`
  - `codex/prompts/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum/run.md`
  - `codex/codex_checklist/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`
  - `codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`
- **Service:**
  - `api/services/run_snapshot_builder.py`
- **Smoke:**
  - `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py`

### 3.2 Mit szallit le a task
- Explicit `build_run_snapshot_payload(...)` service-t, amely owner-projekt guard utan osszeallitja a snapshot manifest blokkokat.
- Determinisztikus technology setup kivalasztast (`approved`, default preferencia, ambiguas guard).
- Aktiv project part requirement + sheet input validaciot, valamint solverre alkalmas part revision/derivative guardot.
- Determinisztikus snapshot hash kepzest canonical JSON serializacioval.

### 3.3 Mit NEM szallit le a task
- Nem vezet be run create/queue/worker futasi logikat.
- Nem modositja a legacy `api/routes/runs.py` route-ot.
- Nem general solver outputot es nem tolt projection/artifact tablakat.

### 3.4 Plusz migracio / runtime fuggoseg
- Uj migracio nem kellett.
- Uj runtime fuggoseg nem kellett.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md` -> PASS

### 4.2 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile api/services/run_snapshot_builder.py scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py` -> PASS

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit `api/services/run_snapshot_builder.py` service. | PASS | `api/services/run_snapshot_builder.py:422` | A `build_run_snapshot_payload` kulon service modulban valositja meg a snapshot builder workflowt. | Smoke + verify |
| A task a meglevo H0/H1 tablavilagra epul, nem legacy run modellre. | PASS | `api/services/run_snapshot_builder.py:107`; `api/services/run_snapshot_builder.py:124`; `api/services/run_snapshot_builder.py:147`; `api/services/run_snapshot_builder.py:249`; `api/services/run_snapshot_builder.py:349` | A service kizarolag `app.projects`, `app.project_settings`, `app.project_technology_setups`, `app.project_part_requirements`, `app.part_*`, `app.project_sheet_inputs`, `app.sheet_*`, `app.geometry_derivatives` tablakat olvas. | Smoke + kodellenorzes |
| A builder osszeolvassa a projekt-level technology selectiont. | PASS | `api/services/run_snapshot_builder.py:135`; `api/services/run_snapshot_builder.py:442`; `api/services/run_snapshot_builder.py:480` | Approved setup selection + default preferencia + technology manifest kitoltes megtortenik. | Smoke: missing technology setup |
| A builder osszeolvassa az aktiv project part requirementeket. | PASS | `api/services/run_snapshot_builder.py:236`; `api/services/run_snapshot_builder.py:246`; `api/services/run_snapshot_builder.py:448` | Aktiv part requirement rekordokbol epul a `parts_manifest_jsonb`. | Smoke: missing active requirement |
| A builder osszeolvassa az aktiv project sheet inputokat. | PASS | `api/services/run_snapshot_builder.py:336`; `api/services/run_snapshot_builder.py:346`; `api/services/run_snapshot_builder.py:454` | Aktiv sheet input rekordokbol epul a `sheets_manifest_jsonb`. | Smoke: missing active sheet input |
| A snapshotban minden solver-input relevans part/sheet/technology adat megjelenik H1 minimum szinten. | PASS | `api/services/run_snapshot_builder.py:299`; `api/services/run_snapshot_builder.py:384`; `api/services/run_snapshot_builder.py:471`; `api/services/run_snapshot_builder.py:480`; `api/services/run_snapshot_builder.py:494`; `api/services/run_snapshot_builder.py:520` | A service a kulcs manifest blokkokat (`project/technology/parts/sheets/geometry/solver/manufacturing`) explicit kitolti es visszaadja. | Smoke success branch |
| A builder csak solverre alkalmas part revision + derivative referenciat enged tovabb. | PASS | `api/services/run_snapshot_builder.py:265`; `api/services/run_snapshot_builder.py:278`; `api/services/run_snapshot_builder.py:286`; `api/services/run_snapshot_builder.py:292` | Csak `approved` lifecycle + explicit, `nesting_canonical` derivative + geometry lineage konzisztencia mehet tovabb. | Smoke: part not approved + derivative missing |
| A builder determinisztikus `snapshot_hash_sha256` erteket kepez. | PASS | `api/services/run_snapshot_builder.py:413`; `api/services/run_snapshot_builder.py:417`; `api/services/run_snapshot_builder.py:508`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:93`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:293` | Stabil rendezes + canonical JSON + SHA256 hash miatt ugyanarra az inputra stabil hash jon vissza. | Smoke deterministic hash branch |
| A task nem vezet be run route-ot, queue insertet vagy worker logikat. | PASS | `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml:23`; `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml:24`; `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml:25` | A task output scope csak service + smoke + dokumentacios artefaktok; run route/queue/worker file nem resze. | Verify AUTO block diff/stat |
| Keszul task-specifikus smoke a sikeres es hibas agakra. | PASS | `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:266`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:293`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:302`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:316`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:331`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:346`; `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py:360` | A smoke lefedi a kért success + deterministic + missing technology/requirement/sheet + invalid part revision/derivative agat. | `python3 scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py` |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md:1`; `codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md:1` | A task checklist es report elkeszult DoD evidenciakkal. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.verify.log:1` | A kotelezo gate wrapperrel futott, a report AUTO_VERIFY blokk frissult. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A builder H1 minimum szinten csak snapshot payloadot epit; run insert/queue/worker integracio kovetkezo taskok (H1-E4-T2/T3).
- A service determinisztikus hash-e az input truth stabilitasara epul; termelesben ez a snapshot deduplikacio alapja lehet.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-19T18:43:51+01:00 → 2026-03-19T18:47:22+01:00 (211s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.verify.log`
- git: `main@37006e9`
- módosított fájlok (git status): 8

**git status --porcelain (preview)**

```text
?? api/services/run_snapshot_builder.py
?? canvases/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum/
?? codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md
?? codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.verify.log
?? scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py
```

<!-- AUTO_VERIFY_END -->
