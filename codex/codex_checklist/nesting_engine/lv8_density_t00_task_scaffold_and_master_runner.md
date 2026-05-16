# T00 Checklist — lv8_density_t00_task_scaffold_and_master_runner

Pipálható DoD lista a canvas
[`canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`](../../../canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
(`codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`).

## Szabályfájlok és minták

- [x] `AGENTS.md` beolvasva.
- [x] `docs/codex/overview.md` beolvasva.
- [x] `docs/codex/yaml_schema.md` beolvasva (root `steps` séma, minden stepben
      `name`, `description`, `outputs`, opcionálisan `inputs`).
- [x] `docs/codex/report_standard.md` beolvasva (Report Standard v2,
      DoD → Evidence + Advisory).
- [x] `docs/qa/testing_guidelines.md` beolvasva.
- [x] T00 canvas és YAML beolvasva
      (`canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`,
      `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml`).
- [x] Minta nesting_engine canvas + runner beolvasva
      (`engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`,
      `codex/prompts/nesting_engine/engine_v2_nfp_rc_master_runner.md`).

## Valós repo anchorok ellenőrzése

- [x] `rust/nesting_engine/src/nfp/cache.rs` — OK.
- [x] `rust/nesting_engine/src/placement/nfp_placer.rs` — OK.
- [x] `rust/nesting_engine/src/multi_bin/greedy.rs` — OK.
- [x] `vrs_nesting/config/nesting_quality_profiles.py` — OK.
- [x] `rust/nesting_engine/src/nfp/concave.rs` — OK.
- [x] `scripts/experiments/lv8_2sheet_claude_search.py` — OK.
- [x] `scripts/experiments/lv8_2sheet_claude_validate.py` — OK.
- [x] `worker/cavity_validation.py` — OK.
- [x] `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` — OK.
- [x] `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` — OK.
- [x] `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` —
      jelen volt a snapshotban, de T00 nem támaszkodik rá; T01 inventory feladata.

## T00 output fájlok létrehozása

- [x] `canvases/nesting_engine/lv8_density_task_index.md` létrehozva.
- [x] Task index tartalmaz T00–T22 taskokat.
- [x] Task index tartalmaz Source of truth, Global invariants, Real repo anchors,
      Task list, Dependency graph, Critical path, Parallelization notes,
      First package batch és Stop conditions szekciókat.
- [x] `codex/prompts/nesting_engine/lv8_density_master_runner.md` létrehozva.
- [x] Master runner tartalmaz Cél, Kötelező olvasnivaló, Baseline preflight,
      Global hard rules, Files and fixtures to verify before start,
      Execution order, Checkpoints, Per-task runner references, Phase gates,
      Final benchmark matrix, Rollback rules, Reporting rules szekciókat.
- [x] Master runner nem állítja, hogy T01–T22 runner fájlok már léteznek —
      expected path + status formátum.

## Tilalmak betartása

- [x] Nem történt Rust engine kódmódosítás (Step 7 — Production diff guard
      üres halmaz volt; a végső állapotban sem szerepel `*.rs` diff).
- [~] Python production kódmódosítás történt **kontrollált scope-tágítással**:
      `api/services/dxf_preflight_acceptance_gate.py` (+12 sor). Indok: a
      Step 8 első futása baseline pytest fail-lel állt meg
      (`test_t6_rejected_when_validator_probe_rejects`); a fixet a user
      kifejezetten kérte ("javítsd a hibákat, amíg a verify.sh és a check.sh
      zöld nem lesz"). A fix nem érint sem Rust engine kódot, sem quality
      profile-t. Részletek a report 3.2 és DoD #7 sorában; státusz
      `PASS_WITH_NOTES`.
- [x] Nem történt quality profile módosítás
      (`vrs_nesting/config/nesting_quality_profiles.py` érintetlen).
- [x] Nem készült T01–T22 canvas / YAML / runner fájl.
- [x] Nem történt placeholder fixture létrehozása.
- [x] Index és runner a `docs/codex/yaml_schema.md` és a végleges terv
      tartalmát nem módosítja.

## Verifikáció

- [x] Step 6 sanity check tokenek megvannak az indexben és a master runnerben
      (`T00`, `T01`, `T22`, `Dependency graph`, `Critical path`, `Baseline preflight`,
      `Global hard rules`, `Execution order`, `Rollback rules`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
      lefutott. Eredmény: **PASS** (`check.sh` exit 0, 224s). 302 pytest pass,
      mypy clean (26 file), Sparrow IO smoketest + DXF smoke + multisheet +
      `vrs_solver` determinisztika + timeout/perf guard zöld. Log:
      `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log`.
- [x] Report DoD → Evidence Matrix kitöltve (lásd a report 5) szekcióját).
      A #6 sor `PASS`, a #7 sor `PASS_WITH_NOTES` (a verify zöldre hozásához
      egy kontrollált, T00 scope-on kívüli Python production fix
      `api/services/dxf_preflight_acceptance_gate.py`-ben).
