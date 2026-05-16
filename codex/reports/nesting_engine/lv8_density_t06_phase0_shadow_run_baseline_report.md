# Report — lv8_density_t06_phase0_shadow_run_baseline_report

**Státusz:** PASS_WITH_NOTES

Phase 0 shadow baseline matrix script + teszt + artefakt pipeline elkészült és futott.
A matrix döntése: **`DEFER_HARD_CUT`**.

## 1) Meta

- Task slug: `lv8_density_t06_phase0_shadow_run_baseline_report`
- Canvas: [canvases/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md](../../../canvases/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md)
- Goal YAML: [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t06_phase0_shadow_run_baseline_report.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t06_phase0_shadow_run_baseline_report.yaml)
- Checklist: [codex/codex_checklist/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md](../../codex_checklist/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md)
- Checkpoint alias: [codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md](lv8_density_phase0_shadow_baseline.md)

## 2) Előfeltételek (T01–T05)

Minden kötelező report fájl létezik:

- `lv8_density_t01_phase0_fixture_inventory.md` → OK
- `lv8_density_t02_phase0_quality_profile_shadow_switch.md` → OK
- `lv8_density_t03_phase0_nfp_diag_gate.md` → OK
- `lv8_density_t04_phase0_engine_stats_export.md` → OK
- `lv8_density_t05_phase0_polygon_validation_gate.md` → OK

## 3) Fixture + Profile Inventory

- profile-párok (`get_phase0_shadow_profile_pairs()`):
  - `quality_default -> quality_default_no_sa_shadow`
  - `quality_aggressive -> quality_aggressive_no_sa_shadow`
- fixture elérhetőség:
  - `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` → present
  - `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` → present
  - `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` → present
  - contract-freeze anchorok → present
- inventory artifact:
  - `tmp/lv8_density_phase0_shadow_runs/fixture_profile_inventory.json`

## 4) Implementáció és teszt

- Új script:
  - [scripts/experiments/lv8_phase0_shadow_run_matrix.py](../../../scripts/experiments/lv8_phase0_shadow_run_matrix.py)
- Új teszt:
  - [tests/test_lv8_phase0_shadow_run_matrix.py](../../../tests/test_lv8_phase0_shadow_run_matrix.py)
- Célzott ellenőrzések:
  - `python3 -m py_compile scripts/experiments/lv8_phase0_shadow_run_matrix.py` → OK
  - `python3 -m pytest tests/test_lv8_phase0_shadow_run_matrix.py -q` → `5 passed`
  - `python3 -m py_compile scripts/experiments/lv8_2sheet_claude_search.py` → OK
  - `python3 -m py_compile scripts/experiments/lv8_polygon_validator.py` → OK

## 5) Shadow Matrix Futtatás

Lefutott matrix script:

- parancs: `python3 scripts/experiments/lv8_phase0_shadow_run_matrix.py --out-root tmp/lv8_density_phase0_shadow_runs --time-limit-sec 60 --seed 42 --include-lv8-179 auto --run-contract-freeze-smoke 1`
- eredmény artifactok:
  - `tmp/lv8_density_phase0_shadow_runs/runs.jsonl`
  - `tmp/lv8_density_phase0_shadow_runs/phase0_shadow_matrix.json`
  - `tmp/lv8_density_phase0_shadow_runs/phase0_shadow_matrix.md`
  - `tmp/lv8_density_phase0_shadow_runs/hard_cut_decision.json`

Per-run matrix kivonat (`phase0_shadow_matrix.json`):

| family | pair | pair_pass |
|---|---|---|
| lv8_276 | default vs default_no_sa_shadow | true |
| lv8_276 | aggressive vs aggressive_no_sa_shadow | true |
| sa_guard | default vs default_no_sa_shadow | false |
| sa_guard | aggressive vs aggressive_no_sa_shadow | false |
| lv8_179 | default vs default_no_sa_shadow | true |
| lv8_179 | aggressive vs aggressive_no_sa_shadow | false |
| web_platform_contract_freeze | regression_gate | PASS |

Contract-freeze row:

- `shadow_profile_applicability = "not_applicable"`
- `regression_gate = "PASS"`

## 6) Hard-cut Döntés

- hard_cut_decision: `DEFER_HARD_CUT`
- reason: `at_least_one_engine_pair_failed`

Indok: a `sa_guard` és `lv8_179/aggressive` párokban a no-SA shadow nem érte el a legacy SA profil eredményeit, ezért hard-cut nem engedélyezhető.

## 7) DoD → Evidence Matrix

| DoD | Státusz | Evidence |
|---|---|---|
| Repo szabály + előfeltétel ellenőrzés | PASS | 2) szekció; T01–T05 reportok jelen |
| Fixture/profile matrix újraellenőrzés | PASS | `fixture_profile_inventory.json`, 3) szekció |
| Shadow matrix script | PASS | `scripts/experiments/lv8_phase0_shadow_run_matrix.py` |
| Shadow matrix tesztek | PASS | `tests/test_lv8_phase0_shadow_run_matrix.py`, 5 passed |
| Célzott ellenőrzések | PASS | py_compile + pytest parancsok zöldek |
| Phase0 shadow matrix futtatás + artefaktok | PASS_WITH_NOTES | matrix artifactok kész; run időkeretben rövidített (60s) |
| Aggregált baseline report + alias | PASS | ez a report + `lv8_density_phase0_shadow_baseline.md` |
| Repo gate verify | PENDING | AUTO_VERIFY blokk frissíti |

## 8) Advisory Notes

1. A teljes 600s időlimites benchmark-mátrix ebben a futásban nem lett végigvárva; gyorsított (60s) run történt.
2. Emiatt a task státusz `PASS_WITH_NOTES`, nem `PASS`.
3. A hard-cut döntés ettől függetlenül helyesen `DEFER_HARD_CUT`.
4. A contract-freeze regression gate PASS, de nem profile-aware összehasonlítás.

## 9) T07 Indulási Feltétel

T07 indulhat, de no-SA hard-cut nélkül. A teljes hard-cut jóváhagyáshoz hosszabb, teljes evidence futás szükséges.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-17T00:57:05+02:00 → 2026-05-17T01:00:17+02:00 (192s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.verify.log`
- git: `main@97e82b5`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
?? codex/codex_checklist/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t06_phase0_shadow_run_baseline_report.yaml
?? codex/prompts/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report/
?? codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
?? codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
?? codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.verify.log
?? scripts/experiments/lv8_phase0_shadow_run_matrix.py
?? tests/test_lv8_phase0_shadow_run_matrix.py
```

<!-- AUTO_VERIFY_END -->
