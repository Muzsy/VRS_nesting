# Report — lv8_density_t00_task_scaffold_and_master_runner

**Státusz:** PASS_WITH_NOTES

A `./scripts/verify.sh` (Step 8) zöld — `check.sh` exit 0, pytest
`302 passed`, mypy `Success: no issues found in 26 source files`, Sparrow
build + IO smoketest + DXF smoke + multisheet + vrs_solver determinisztika +
timeout/perf guard mind PASS, 224s teljes futási idő.

A `notes` rész: a Step 8 első futása pre-existing baseline regresszióval
piros volt (`tests/test_dxf_preflight_acceptance_gate.py::test_t6_rejected_when_validator_probe_rejects`),
amely nem T00 scope. A user kifejezett utasítására ("javítsd a hibákat, amíg a
verify.sh és a check.sh zöld nem lesz") **kontrollált scope-tágítással**
megtörtént a root-cause fix az `api/services/dxf_preflight_acceptance_gate.py`
fájlban (12 sor új kód a `_resolve_outcome` `validator_rejected` ágában —
szimmetrikus a meglévő `_nested_holes_demoted` mintával). Ez a változás
megsérti a T00 canvas tilalmát ("Tilos Python production kódot módosítani"),
ezért a státusz `PASS` helyett `PASS_WITH_NOTES`. A változás teljes kontextusa
a 3.2-ben, a DoD #7 sor pedig PASS_WITH_NOTES-ra állítva.

## 1) Meta

- **Task slug:** `lv8_density_t00_task_scaffold_and_master_runner`
- **Kapcsolódó canvas:**
  `canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- **Kapcsolódó goal YAML:**
  `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml`
- **Futás dátuma:** 2026-05-16
- **Branch / commit:** `main` @ `5598554`
- **Fókusz terület:** Docs (Codex scaffold)

## 2) Scope

### 2.1 Cél

1. Létrehozni a végleges LV8 packing density fejlesztési lánc indexét
   (`canvases/nesting_engine/lv8_density_task_index.md`).
2. Létrehozni a hozzá tartozó master runnert
   (`codex/prompts/nesting_engine/lv8_density_master_runner.md`).
3. Létrehozni a T00 task checklistet és reportot a Report Standard v2 szerint.
4. Auditálni a végleges tervben hivatkozott valós repo-anchorok meglétét.
5. Lezárni a sanity tokeneket és a production diff guard-ot, majd futtatni a
   standard repo gate-et.

### 2.2 Nem-cél (explicit)

1. Nem implementál Rust engine logikát.
2. Nem hoz létre T01–T22 canvas / YAML / runner fájlt.
3. Nem módosítja a quality profile-okat (`nesting_quality_profiles.py`).
4. Nem futtat hosszú benchmarkot.
5. Nem dönt újra a végleges fejlesztési terv tartalmáról.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

- **Canvas / index:**
  - `canvases/nesting_engine/lv8_density_task_index.md` (új, 418 sor)
- **Codex prompts:**
  - `codex/prompts/nesting_engine/lv8_density_master_runner.md` (új, 332 sor)
- **Codex checklist:**
  - `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md` (új)
- **Codex reports:**
  - `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md` (új, ez a fájl)
  - `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log`
    (a `./scripts/verify.sh` írja Step 8-ban)
- **API (scope-tágítás, user-explicit instrukció):**
  - `api/services/dxf_preflight_acceptance_gate.py` (+12 sor: `_resolve_outcome`
    `validator_rejected` ága mostantól `validator_probe_rejected` családot
    appendel a `blocking_reasons`-be, szimmetrikusan a nested-holes demotion
    pattern-nel).

A T00 saját canvas + YAML + runner csomag korábbi taskban már a helyén volt:

- `canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml`
- `codex/prompts/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner/run.md`

### 3.2 Miért változtak?

- **Canvas / index:** a végleges fejlesztési terv (v2.2) gépileg követhető
  T01–T22 indexének hiánya megakadályozta a packaging taskok determinisztikus
  delegálását.
- **Master runner:** az agent-delegálható futás eddig nem rendelkezett a teljes
  láncon átívelő sorrend, hard rules, checkpointok, phase gate-ek és benchmark
  mátrix dokumentációval.
- **Checklist + report:** a T00 DoD-jainak ellenőrizhetősége és a verify run
  bekötése a Report Standard v2 szerint.
- **API fix (`dxf_preflight_acceptance_gate.py`):** a Step 8 első futása
  baseline pytest fail-lel állt meg
  (`test_t6_rejected_when_validator_probe_rejects`), mert a
  `_resolve_outcome` a `validator_rejected` ágban csak a status-t és a
  precedence-t adta vissza, de nem appendelte a `validator_probe_rejected`
  családot a `blocking_reasons`-be — pedig a diagnostics renderer
  ([api/services/dxf_preflight_diagnostics_renderer.py:636](api/services/dxf_preflight_diagnostics_renderer.py#L636))
  már várta ezt a családot. A fix szimmetrikus a meglévő nested-holes
  demotion mintával (`review_required_reasons.append(...)`). User kifejezett
  utasítása alapján T00 scope-on kívüli javítás.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
  → **PASS** (`check.sh` exit 0, 224s, lásd AUTO_VERIFY blokk 4.4-ben).
  Tartalmazza: pytest 302 passed, mypy clean (26 file), Sparrow IO smoketest +
  validator, DXF import/export + multisheet smoketestek, `vrs_solver`
  determinisztika + timeout/perf guard.
- Log: `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log`

### 4.2 Opcionális, feladatfüggő parancsok

- **Anchor audit (Step 2):** 10/10 kötelező anchor jelen
  (`rust/nesting_engine/src/nfp/cache.rs`,
  `rust/nesting_engine/src/placement/nfp_placer.rs`,
  `rust/nesting_engine/src/multi_bin/greedy.rs`,
  `vrs_nesting/config/nesting_quality_profiles.py`,
  `rust/nesting_engine/src/nfp/concave.rs`,
  `scripts/experiments/lv8_2sheet_claude_search.py`,
  `scripts/experiments/lv8_2sheet_claude_validate.py`,
  `worker/cavity_validation.py`,
  `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`,
  `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`). Az LV8 179 tmp fixture
  (`tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`) a jelen
  snapshotban jelen volt, de T00 nem támaszkodik rá; T01 inventory feladata
  ellenőrizni / helyreállítani.
- **Sanity tokenek (Step 6):** `T00`, `T01`, `T22`, `Dependency graph`,
  `Critical path` jelen a task indexben; `Baseline preflight`,
  `Global hard rules`, `Execution order`, `Rollback rules` jelen a master
  runnerben.
- **Production diff guard (Step 7):** `git diff --name-only HEAD -- '*.rs' '*.py'
  '*.ts' '*.tsx' | grep -v '^codex/' | grep -v '^canvases/'` → üres halmaz
  (a T00 nem érint Rust/Python/TS production fájlt).

### 4.3 Ha valami kimaradt

Semmilyen kötelező ellenőrzés nem maradt ki. A `./scripts/verify.sh` futása
végigvitte a teljes `./scripts/check.sh` minőségkaput, és minden lépés PASS.

Megjegyzendő, hogy a Step 8 **első** futása piros volt
(`test_t6_rejected_when_validator_probe_rejects` — assertion:
`'validator_probe_rejected' in _families(result["blocking_reasons"])`, az ágban
`[]` érkezett). A user kifejezett utasítása alapján a hibát root-cause javítással
fixáltuk (lásd 3.2 utolsó pont), és ezután a Step 8 második futása **PASS**
(`check.sh` exit 0, 302 pytest pass, mypy clean).

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-16T09:20:34+02:00 → 2026-05-16T09:24:18+02:00 (224s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log`
- git: `main@5598554`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 .claude/scheduled_tasks.lock                  |  1 -
 api/services/dxf_preflight_acceptance_gate.py | 12 ++++++++++++
 2 files changed, 12 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 D .claude/scheduled_tasks.lock
 M api/services/dxf_preflight_acceptance_gate.py
?? canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
?? canvases/nesting_engine/lv8_density_task_index.md
?? codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml
?? codex/prompts/nesting_engine/lv8_density_master_runner.md
?? codex/prompts/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner/
?? codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
?? codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| #1 A task index elkészült és T00–T22-t tartalmazza | PASS | `canvases/nesting_engine/lv8_density_task_index.md:122-144` (task list); a teljes fájl 418 soros, T00–T22 belső szekciókkal | Az index Source of truth, Global invariants, Real repo anchors, Task list (T00…T22), Dependency graph, Critical path, Parallelization notes, First package batch és Stop conditions szekciókat tartalmaz. | Step 6 sanity check (`T00`, `T01`, `T22` tokenek megvannak) |
| #2 A master runner elkészült és önállóan használható | PASS | `codex/prompts/nesting_engine/lv8_density_master_runner.md:1-332` (Cél → Reporting rules) | A runner Cél, Kötelező olvasnivaló, Baseline preflight, Global hard rules, Files and fixtures to verify before start, Execution order, Checkpoints, Per-task runner references, Phase gates, Final benchmark matrix, Rollback rules és Reporting rules szekciókat tartalmazza. | Step 6 sanity check (`Baseline preflight`, `Global hard rules`, `Execution order`, `Rollback rules`) |
| #3 A master runner nem állítja, hogy T01–T22 runner fájlok már léteznek | PASS | `codex/prompts/nesting_engine/lv8_density_master_runner.md` "Per-task runner references" szekciója | Minden T01–T22 sor "expected runner path" + "Status: to be created by its own package task" formátumban. Csak a T00 jelölve `present`-ként. | Step 6 sanity check + manuális diff |
| #4 Minden hivatkozott valós repo anchor ellenőrzött | PASS | Step 2 audit output (10/10 OK) | Az anchor lista 1:1-ben szerepel a canvas "Valós repo-kiindulópontok" szekciójában, és az index Real repo anchors táblázatában. Egyik sem hiányzik. | `for p in …; do test -e "$p" && echo "OK $p"; done` |
| #5 A YAML séma a `docs/codex/yaml_schema.md` szerinti root `steps` struktúrát használja | PASS | `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml:1-106` | Root kulcs `steps`, minden stepben `name`, `description`, `outputs`; opcionális `inputs` ott, ahol az audit lépésekben szükséges. Az utolsó step a "Repo gate (automatikus verify)". | Step 1 séma olvasás |
| #6 A report és checklist elkészült | PASS | Ez a fájl + `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md` + AUTO_VERIFY blokk a 4.4 alatt | A report Report Standard v2 szerint strukturált. A Step 8 második futása **PASS** (`check.sh` exit 0, 224s, 302 pytest pass, mypy clean, Sparrow + DXF + multisheet + determinisztika smoketestek zöldek). | `./scripts/verify.sh --report …` (lásd 4.1 és 4.4) |
| #7 Nincs production engine kódmódosítás | PASS_WITH_NOTES | `git diff --stat`: `api/services/dxf_preflight_acceptance_gate.py | 12 ++++++++++++` | Eredetileg PASS volt (Step 7 első futása üres halmaz). A user kifejezett utasítása alapján egy kontrollált, T00 scope-on **kívüli** Python production fix bekerült (`dxf_preflight_acceptance_gate.py:411-422` környékére): a `_resolve_outcome` `validator_rejected` ága mostantól appendel egy `validator_probe_rejected` családot a `blocking_reasons`-be. A változás semmilyen Rust engine, quality profile, runner vagy multi_bin fájlt nem érint, és kizárólag a baseline pytest fail miatt szükséges. Innen ered a PASS_WITH_NOTES. | `git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx' \| grep -v '^codex/' \| grep -v '^canvases/'` → `api/services/dxf_preflight_acceptance_gate.py` |

A #6 PASS-ként zár, mert a Step 8 második futása zöld. A #7 PASS_WITH_NOTES,
mert a verify zöldre hozásához szükséges volt egy minimális, kontrollált
Python production fix a T00 saját canvas tilalmán kívül — kizárólag a user
kifejezett utasítása alapján, és nem érint sem Rust engine kódot, sem quality
profile-t. Az érintett scope (`api/services/dxf_preflight_acceptance_gate.py`)
nem szerepel az LV8 density anchorok között.

## 6) IO contract / minták

Nem releváns ehhez a taskhoz: a Sparrow IO contract és a `poc/` minták nem
módosultak. A T00 csak Codex artefaktokat (`canvases/`, `codex/`) érint.

## 7) Doksi szinkron

- Master runner és index a `docs/codex/overview.md` workflow szerint épül,
  a `docs/codex/yaml_schema.md` szigorúbb root sémáját követve (csak `steps`).
- A report a `docs/codex/report_standard.md` v2 struktúráját követi.
- A `docs/qa/testing_guidelines.md` minőségkapu követelménye (`./scripts/verify.sh`)
  Step 8-ban kerül lefuttatásra.

## 8) Advisory notes (max 5)

- A Step 8 zöldre hozása megkövetelt egy minimális Python production fixet
  a T00 saját canvas tilalmán kívül (`api/services/dxf_preflight_acceptance_gate.py`).
  A fix kontrollált scope-tágítás, user-explicit instrukción alapul, és nem
  érint sem Rust engine kódot, sem quality profile-t. A scope-tágítás
  átvezetésre érdemes lehet a canvas tilalmi listáján (jövőbeli T0x-szerű
  scaffold taskoknál érdemes előre engedni "blocking baseline regression fix"
  kategóriát, vagy explicit nevesíteni, hogy az ilyen javítás külön taskba
  kerül).
- A canvas megemlíti, hogy a `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`
  fixture nem feltétlenül létezik. A T00 snapshotban jelen volt; T01 inventorynak
  ettől függetlenül kötelező ellenőriznie és nem támaszkodni a meglétére.
  A T01 fixture inventory táblába érdemes egy `PRESENT_BUT_TRANSIENT` jelölés
  ehhez, hogy ne keveredjen a stabil `tests/fixtures/...` családdal.
- A master runner Final benchmark matrix táblázata sablon; a tényleges
  density-delta értékeket csak T22 reportja töltheti be polygon-aware
  validation gate után.
- A T13 (Phase 2c contact bonus) aktivációs feltétele Phase 2a+2b gap; ez a
  döntés a T12 reportjából automatikusan következik, nem külön döntés.
- Az `engine_v2_nfp_rc_master_runner.md` minta részletesebb bash sniplet-ekkel
  dolgozott. A T00 master runner-ben szándékosan nem ismételjük az egyes task
  CHECKPOINT bash-eit — azok a per-task runnerben (`codex/prompts/...<TASK>/run.md`)
  lesznek a packaging során, hogy a master runner egyetlen forrásban tartsa a
  sorrendet és a hard rules-t.

## 9) Follow-ups

1. **DXF preflight acceptance gate fix utólagos rendbetétele** — a Step 8 zöldre
   hozásához szükséges minimális Python production fix
   (`api/services/dxf_preflight_acceptance_gate.py` `_resolve_outcome`
   `validator_rejected` ága + `validator_probe_rejected` családbejegyzés) jelenleg
   a T00 commit-jával együtt él. Érdemes külön commitba vagy külön Codex
   task / PR-ba kiemelni, hogy a git history a scope-okat tisztán mutassa.
   Kockázat: ha egyetlen commitban marad, jövőbeli git blame zavaros lehet a
   "scaffold T00" üzenettől; nyereség: tiszta history.
2. **T01 packaging** — fixture inventory canvas + YAML + runner.
   Kockázat: ha az LV8 179 fixture újra eltűnik, Phase 0 baseline elcsúszik;
   nyereség: stabil fixture státusz Phase 0 előtt.
3. **T02–T05 packaging waveként** — párhuzamosítható, Phase 0 lefedéshez.
   Kockázat: külön agentre delegálva a polygon-aware validation gate közös
   bekötése elcsúszhat; nyereség: gyorsabb Phase 0 lezárás.
4. **T06 packaging** — Phase 0 shadow run baseline aggregálás, hogy
   CHECKPOINT-1 mérhetővé váljon.
5. **`development_plan_packing_density_20260515.md` referencia tárolása** a
   repóban (jelenleg külső dokumentum). Kockázat: drift; nyereség: 1:1 audit
   bázis az index és a terv között.
