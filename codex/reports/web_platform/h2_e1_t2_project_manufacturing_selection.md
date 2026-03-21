PASS

## 1) Meta
- Task slug: `h2_e1_t2_project_manufacturing_selection`
- Kapcsolodo canvas: `canvases/web_platform/h2_e1_t2_project_manufacturing_selection.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h2_e1_t2_project_manufacturing_selection.yaml`
- Futas datuma: `2026-03-21`
- Branch / commit: `main @ 93c5431 (dirty working tree)`
- Fokusz terulet: `Mixed (DB schema + API service/route + smoke)`

## 2) Scope

### 2.1 Cel
- Projekt-szintu manufacturing profile version selection truth bevezetese.
- Egy projektre create-or-replace selection viselkedes biztositas.
- Minimum GET / PUT / DELETE API contract bevezetese project manufacturing selectionra.
- Project owner scope + manufacturing version owner scope + inaktiv version vedelme.
- Minimalis technology/manufacturing konzisztencia ellenorzes a valos schema `thickness_mm` mezojere tamaszkodva.

### 2.2 Nem-cel (explicit)
- Manufacturing profile CRUD domain teljes ujranyitasa.
- Snapshot manufacturing manifest bovitese (`api/services/run_snapshot_builder.py` erintetlen).
- Manufacturing resolver / plan builder / preview / postprocess / export scope.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- Task artefaktok:
  - `canvases/web_platform/h2_e1_t2_project_manufacturing_selection.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h2_e1_t2_project_manufacturing_selection.yaml`
  - `codex/prompts/web_platform/h2_e1_t2_project_manufacturing_selection/run.md`
  - `codex/codex_checklist/web_platform/h2_e1_t2_project_manufacturing_selection.md`
  - `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md`
- DB migration:
  - `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- Backend:
  - `api/services/project_manufacturing_selection.py`
  - `api/routes/project_manufacturing_selection.py`
  - `api/main.py`
- Smoke:
  - `scripts/smoke_h2_e1_t2_project_manufacturing_selection.py`

### 3.2 Mi valtozott es miert
- A migration letrehozza (vagy hardeneli) a project-level manufacturing selection truth-ot, valamint a minimalis manufacturing profile/version tablakat, hogy a selection API valos adatmodellre tudjon epulni.
- A service explicit project-owner es version-owner validaciot vegez, create-or-replace modon upsertel, es `thickness_mm` alapon ellenorzi a technology/manufacturing alapkonzisztenciat.
- Az uj route minimalis, auditálhato GET/PUT/DELETE contractot ad a projekthez rendelt aktiv manufacturing profile version kezelesere.
- A dedikalt smoke script lefedi a fo sikeres es hibas agakat.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzesek
- `python3 -m py_compile api/services/project_manufacturing_selection.py api/routes/project_manufacturing_selection.py api/main.py scripts/smoke_h2_e1_t2_project_manufacturing_selection.py` -> PASS
- `python3 scripts/smoke_h2_e1_t2_project_manufacturing_selection.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| A task repo-hu modon bevezeti vagy bekoti a `project_manufacturing_selection` truth-ot. | PASS | `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql:116`; `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql:221` | A migration bevezeti a selection truth tablajat es hozzaadja az owner-scope RLS policyket. | Migration review |
| Egy projektnek legfeljebb egy aktiv manufacturing selectionje van. | PASS | `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql:117`; `api/services/project_manufacturing_selection.py:273` | A `project_id` primary key + service create-or-replace upsert logika egy projektre egy rekordot tart fenn. | `python3 scripts/smoke_h2_e1_t2_project_manufacturing_selection.py` |
| A selection project owner scope-ban hozhato letre, modositato es torolheto. | PASS | `api/services/project_manufacturing_selection.py:58`; `api/routes/project_manufacturing_selection.py:99`; `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql:228` | Service es route owner-checket futtat, DB policy csak projekt tulajdonosnak enged irast/torlest. | Smoke + verify |
| A selection csak a userhez tartozo ervenyes manufacturing profile versionra mutathat. | PASS | `api/services/project_manufacturing_selection.py:78`; `api/services/project_manufacturing_selection.py:100`; `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql:145` | Owner-scope es inaktiv version validacio service oldalon, DB-ben `owns_manufacturing_profile_version` policy check. | Smoke (foreign + inactive) |
| A task nem nyitja ujra a manufacturing profile CRUD scope-ot. | PASS | `api/routes/project_manufacturing_selection.py:99`; `api/routes/project_manufacturing_selection.py:141` | Kizarolag selection endpointek kerultek be (PUT/GET/DELETE), profile CRUD route nem keszult. | Diff review |
| A task nem nyul a snapshot / plan / preview / postprocess reteghez. | PASS | `api/main.py:16`; `api/services/project_manufacturing_selection.py:232` | A diff csak selection migration/service/route/smoke artefaktokat erint, snapshot/plan modulokhoz nincs kodvaltozas. | Diff review |
| Keszul minimalis GET / PUT / DELETE backend contract. | PASS | `api/routes/project_manufacturing_selection.py:99`; `api/routes/project_manufacturing_selection.py:121`; `api/routes/project_manufacturing_selection.py:141`; `api/main.py:107` | A harom endpoint implementalva van es a router be van kotve az appba. | Smoke |
| A technology/manufacturing alapkonzisztencia ellenorzes csak valos schema mezokre tamaszkodik. | PASS | `api/services/project_manufacturing_selection.py:154`; `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql:41` | Az ellenorzes csak `thickness_mm` osszevetest vegez, katalogus-logika vagy kitalalt join nelkul. | Smoke mismatch ag |
| Keszul task-specifikus smoke script a sikeres es hibas agakra. | PASS | `scripts/smoke_h2_e1_t2_project_manufacturing_selection.py:339`; `scripts/smoke_h2_e1_t2_project_manufacturing_selection.py:384`; `scripts/smoke_h2_e1_t2_project_manufacturing_selection.py:402` | A smoke lefedi create/overwrite/get/delete, idegen projekt/version, inaktiv version es thickness mismatch agakat. | `python3 scripts/smoke_h2_e1_t2_project_manufacturing_selection.py` |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h2_e1_t2_project_manufacturing_selection.md:1`; `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md:58` | A checklist pipalva, a report DoD -> Evidence matrix kitoltve. | Doc review |
| `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md` PASS. | PASS | `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.verify.log:1`; `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md:85` | A kotelezo gate wrapper PASS, AUTO_VERIFY blokk es log frissult. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A migration ugy keszult, hogy T1 altal mar letrehozott tablakat `if not exists`/`add column if not exists` mintaval hardenel, ne duplikaljon.
- A technology/manufacturing konzisztencia jelenleg a biztosan letezo `thickness_mm` mezo osszevetesere korlatozodik.
- Machine/material katalogus-osszevetes nem kerult be, mert a repo jelenlegi schema-ja ehhez nem ad megbizhato katalogus-truthot.

## 7) Follow-ups (opcionalis)
- H2-E4 scope-ban snapshot manufacturing selection bekotes (expliciten nem ennek a tasknak a resze).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-21T21:29:09+01:00 → 2026-03-21T21:32:56+01:00 (227s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.verify.log`
- git: `main@93c5431`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/project_manufacturing_selection.py
?? api/services/project_manufacturing_selection.py
?? canvases/web_platform/h2_e1_t2_project_manufacturing_selection.md
?? codex/codex_checklist/web_platform/h2_e1_t2_project_manufacturing_selection.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e1_t2_project_manufacturing_selection.yaml
?? codex/prompts/web_platform/h2_e1_t2_project_manufacturing_selection/
?? codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md
?? codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.verify.log
?? scripts/smoke_h2_e1_t2_project_manufacturing_selection.py
?? supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql
```

<!-- AUTO_VERIFY_END -->
