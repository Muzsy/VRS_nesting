# LV8 Density T00 — Task scaffold és master runner előkészítés

## 🎯 Funkció

A feladat célja a végleges LV8 packing density fejlesztési tervhez tartozó agent-delegálható munkalánc scaffoldjának létrehozása. Ez a T00 task **nem implementál engine-logikát**, hanem létrehozza azt a repo-n belüli feladatindexet és master runner dokumentumot, amelyből a későbbi T01–T22 `canvas + YAML + runner` csomagok következetesen elkészíthetők és futtathatók.

A T00 kimenete a későbbi munka forrása:

- `canvases/nesting_engine/lv8_density_task_index.md`
- `codex/prompts/nesting_engine/lv8_density_master_runner.md`
- `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

## Forrás és döntések

A T00 a végleges `development_plan_packing_density_20260515.md` v2.2 tervet követi. A terven nem szabad tartalmilag változtatni. A T00 csak végrehajtható task-index és master-runner dokumentációvá bontja.

A T00-ba beépített végleges döntések:

1. Phase 0 a mérési higiénia, algoritmikus fejlesztés előtt.
2. Phase 0 shadow run három fixture-családja:
   - LV8 család.
   - web_platform / contract_freeze család.
   - kis-synthetic / SA guard: elsődlegesen `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`.
3. Phase 1.0 cache path discovery spike kötelező első al-lépés.
4. Phase 1 nem új cache építése, hanem a meglévő `rust/nesting_engine/src/nfp/cache.rs` audit + hardening.
5. Phase 2 lépcsőzött: 2a bbox-growth, 2b extent penalty, 2c contact bonus opt-in.
6. Phase 3 critical-part-focused lookahead.
7. Phase 3.5 `nfp_place_starting_from` önálló infrastruktúra-fázis.
8. Phase 4 critical-only beam.
9. Phase 5 LNS refinement.
10. `quality_beam_lns` konzervatív; `quality_beam_lns_explore` automatikusan `accept_worse_pct=2.0`, `accept_worse_prob=0.05` értékkel fut.

## Valós repo-kiindulópontok

A T00 készítésekor ellenőrizendő és a master runnerben rögzítendő valós repo-kiindulópontok:

- `AGENTS.md` — elsődleges agent szabályfájl.
- `docs/codex/overview.md` — workflow és DoD.
- `docs/codex/yaml_schema.md` — a goal YAML kizárólagos sémája: root `steps`, minden stepben `name`, `description`, `outputs`, opcionálisan `inputs`.
- `docs/codex/report_standard.md` — report struktúra és DoD → Evidence Matrix.
- `docs/qa/testing_guidelines.md` — teszt minimumok.
- `canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md` — canvas minta.
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.yaml` — YAML minta, de a jelenlegi `docs/codex/yaml_schema.md` szigorúbb root-sémáját kell követni.
- `codex/prompts/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation/run.md` — runner minta.
- `codex/prompts/nesting_engine/engine_v2_nfp_rc_master_runner.md` — master runner minta.
- `rust/nesting_engine/src/nfp/cache.rs` — meglévő NfpCache.
- `rust/nesting_engine/src/placement/nfp_placer.rs` — fő placement loop, candidate sort, stats.
- `rust/nesting_engine/src/multi_bin/greedy.rs` — multi-sheet futás és cache életciklus.
- `vrs_nesting/config/nesting_quality_profiles.py` — quality profile registry.
- `rust/nesting_engine/src/nfp/concave.rs` — `[CONCAVE NFP DIAG]` eprintln pontok.
- `scripts/experiments/lv8_2sheet_claude_search.py` — LV8 benchmark harness.
- `scripts/experiments/lv8_2sheet_claude_validate.py` — legacy AABB validator.
- `worker/cavity_validation.py` — meglévő polygon-aware validációs logika.
- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` — LV8 276 fixture.
- `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` — kis-synthetic / SA guard fixture.

Fontos repo-ellenőrzési tény: a tervben szereplő `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` nem feltétlenül része a snapshotnak. Emiatt T01-ben külön fixture inventory / helyreállítás feladat kell.

---

## 🧠 Fejlesztési részletek

## T00 scope

### T00 feladata

Hozd létre a teljes LV8 density fejlesztési lánc belső repo-indexét és master runnerét.

### T00 nem célja

- Nem implementál Rust engine logikát.
- Nem módosítja a quality profile-okat.
- Nem futtat hosszú benchmarkot.
- Nem hoz létre minden T01–T22 canvas/YAML/runner fájlt.
- Nem dönt újra a végleges terv tartalmáról.
- Nem módosítja a végleges fejlesztési tervet.

### Létrehozandó fájlok

1. `canvases/nesting_engine/lv8_density_task_index.md`
2. `codex/prompts/nesting_engine/lv8_density_master_runner.md`
3. `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
4. `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

A `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log` fájlt a `./scripts/verify.sh` generálja.

---

## `lv8_density_task_index.md` kötelező tartalma

A task index legyen a későbbi canvas+YAML+runner csomagok rövid, gépileg követhető forrása.

Kötelező szekciók:

1. `# LV8 packing density — task index`
2. `## Source of truth`
3. `## Global invariants`
4. `## Real repo anchors`
5. `## Task list`
6. `## Dependency graph`
7. `## Critical path`
8. `## Parallelization notes`
9. `## First package batch`
10. `## Stop conditions`

### Task list kötelező elemei

A task index tartalmazza legalább ezeket a taskokat, mindegyiknél:

- task_id
- phase
- rövid cél
- fő érintett fájlok
- függőségek
- kötelező outputok
- acceptance gate röviden

#### Kötelező taskok

```text
T00  lv8_density_t00_task_scaffold_and_master_runner
T01  lv8_density_t01_phase0_fixture_inventory
T02  lv8_density_t02_phase0_quality_profile_shadow_switch
T03  lv8_density_t03_phase0_nfp_diag_gate
T04  lv8_density_t04_phase0_engine_stats_export
T05  lv8_density_t05_phase0_polygon_validation_gate
T06  lv8_density_t06_phase0_shadow_run_baseline_report
T07  lv8_density_t07_phase1_0_cache_path_discovery_spike
T08  lv8_density_t08_phase1_cache_stats_hardening
T09  lv8_density_t09_phase1_shape_id_cache_key_verification
T10  lv8_density_t10_phase1_cache_usage_audit_and_benchmark
T11  lv8_density_t11_phase2a_bbox_growth_scoring
T12  lv8_density_t12_phase2b_extent_penalty_scoring
T13  lv8_density_t13_phase2c_contact_bonus_scoring_optional
T14  lv8_density_t14_phase3_criticality_queue
T15  lv8_density_t15_phase3_critical_lookahead
T16  lv8_density_t16_phase3_5_nfp_place_starting_from
T17  lv8_density_t17_phase4_critical_beam_b4
T18  lv8_density_t18_phase5_lns_core_acceptance
T19  lv8_density_t19_phase5_lns_destroy_repair
T20  lv8_density_t20_phase5_quality_profiles_lns
T21  lv8_density_t21_adr_0002_sa_deprecation
T22  lv8_density_t22_final_benchmark_matrix_and_release_closure
```

### Dependency graph kötelező tartalma

Minimum:

```text
T00 -> T01
T01 -> T02, T03, T04, T05
T02 + T03 + T04 + T05 -> T06
T06 -> T07
T07 -> T08, T09
T08 + T09 -> T10
T10 -> T11 -> T12
T12 -> T14 -> T15
T16 depends on T10, can run after Phase 1 but before T17/T19
T15 + T16 -> T17
T16 + T18 -> T19
T17 + T19 -> T20
T20 -> T22
T21 can start after T06, final before T22
```

### Critical path kötelező tartalma

```text
T00 → T01 → T02/T03/T04/T05 → T06 → T07 → T08/T09 → T10 → T11 → T12 → T14 → T15 → T16 → T17 → T18/T19 → T20 → T22
```

T13 optional, de akkor kerül a kritikus útba, ha Phase 2a+2b nem éri el a Phase 3-hoz szükséges baseline-t.

---

## `lv8_density_master_runner.md` kötelező tartalma

A master runner legyen egy önállóan használható futtatási dokumentum, amelyből egy agent végig tudja vinni vagy részletekben tudja futtatni a fejlesztési láncot.

Kötelező szekciók:

1. `# LV8 Density Master Runner`
2. `## Cél`
3. `## Kötelező olvasnivaló`
4. `## Baseline preflight`
5. `## Global hard rules`
6. `## Files and fixtures to verify before start`
7. `## Execution order`
8. `## Checkpoints`
9. `## Per-task runner references`
10. `## Phase gates`
11. `## Final benchmark matrix`
12. `## Rollback rules`
13. `## Reporting rules`

### Kötelező hard rules

- Tilos silent BLF fallback quality pathon.
- Tilos a végleges fejlesztési terv tartalmi módosítása.
- Tilos nem létező fájlra hivatkozni ellenőrzés nélkül.
- Tilos a `PlacementResult` output kontraktus törése.
- Tilos a `NestSheet` fixture-séma törése.
- Tilos `search/sa.rs` törlése Phase 0-ban.
- Tilos `quality_beam_lns` és `quality_beam_lns_explore` eredményeit aggregálni.
- Tilos long benchmark eredményt polygon-aware validation gate nélkül PASS-ként kezelni.

### Kötelező preflight parancsok

```bash
python3 --version
cargo --version
ls AGENTS.md
ls docs/codex/yaml_schema.md
ls docs/codex/report_standard.md
ls tests/fixtures/nesting_engine/ne2_input_lv8jav.json
ls poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
cargo check -p nesting_engine
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
```

Ha bármelyik kritikus fájl hiányzik: STOP, reportba írni.

### Per-task runner references

A master runner ne állítsa, hogy a T01–T22 runner fájlok már léteznek. A helyes forma:

```text
T01 expected runner path: codex/prompts/nesting_engine/lv8_density_t01_phase0_fixture_inventory/run.md
Status: to be created by its own package task.
```

---

## Checklist fájl kötelező tartalma

A `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md` legyen pipálható DoD lista.

Minimum pontok:

- [ ] AGENTS.md beolvasva.
- [ ] docs/codex/yaml_schema.md beolvasva.
- [ ] Valós repo anchor fájlok ellenőrizve.
- [ ] `lv8_density_task_index.md` létrehozva.
- [ ] Task index tartalmaz T00–T22 taskokat.
- [ ] Dependency graph és critical path szerepel.
- [ ] `lv8_density_master_runner.md` létrehozva.
- [ ] Master runner tartalmaz preflight, hard rules, checkpoints, rollback rules szekciókat.
- [ ] Nem történt Rust/Python production kódmódosítás.
- [ ] `./scripts/verify.sh --report ...` lefutott vagy futtatási akadály dokumentált.
- [ ] Report DoD → Evidence Matrix kitöltve.

---

## Report fájl kötelező tartalma

A report a `docs/codex/report_standard.md` szerint készüljön.

Minimum bizonyítékok:

- `canvases/nesting_engine/lv8_density_task_index.md` sorsávval.
- `codex/prompts/nesting_engine/lv8_density_master_runner.md` sorsávval.
- `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md` sorsávval.
- Verify log vagy futtatási akadály.

---

## 🧪 Tesztállapot

### Kötelező ellenőrzések

```bash
# Repo szabályfájlok
ls AGENTS.md
ls docs/codex/overview.md
ls docs/codex/yaml_schema.md
ls docs/codex/report_standard.md
ls docs/qa/testing_guidelines.md

# Létrehozott T00 outputok
ls canvases/nesting_engine/lv8_density_task_index.md
ls codex/prompts/nesting_engine/lv8_density_master_runner.md
ls codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
ls codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md

# Tartalom sanity check
python3 - <<'PY'
from pathlib import Path
idx = Path('canvases/nesting_engine/lv8_density_task_index.md').read_text()
runner = Path('codex/prompts/nesting_engine/lv8_density_master_runner.md').read_text()
for token in ['T00', 'T01', 'T22', 'Dependency graph', 'Critical path']:
    assert token in idx, f'missing in task index: {token}'
for token in ['Baseline preflight', 'Global hard rules', 'Execution order', 'Rollback rules']:
    assert token in runner, f'missing in master runner: {token}'
print('T00 content sanity PASS')
PY

# Production kód nem módosult
if git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx' | grep -v '^codex/' | grep -v '^canvases/' ; then
  echo 'STOP: unexpected production code diff'
  exit 1
fi

# Standard gate
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
```

### Elfogadási feltételek

- [ ] A task index elkészült és T00–T22-t tartalmazza.
- [ ] A master runner elkészült és önállóan használható.
- [ ] A master runner nem állítja, hogy T01–T22 runner fájlok már léteznek.
- [ ] Minden hivatkozott valós repo anchor ellenőrzött.
- [ ] A YAML séma a `docs/codex/yaml_schema.md` szerinti root `steps` struktúrát használja.
- [ ] A report és checklist elkészült.
- [ ] Nincs production engine kódmódosítás.

---

## 🌍 Lokalizáció

Nem releváns. A dokumentáció magyar nyelvű, illeszkedve a meglévő canvasok többségi stílusához.

---

## 📎 Kapcsolódások

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`
- `codex/prompts/nesting_engine/engine_v2_nfp_rc_master_runner.md`
- `rust/nesting_engine/src/nfp/cache.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `vrs_nesting/config/nesting_quality_profiles.py`
