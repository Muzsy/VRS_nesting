# Runner — lv8_density_t05_phase0_polygon_validation_gate

## Feladat

Végrehajtandó task: **T05 — Phase 0 polygon-aware validation gate**.

A cél egy kötelező polygon-aware benchmark validation gate létrehozása és bekötése a T04 utáni LV8 benchmark harness summary outputjába. A legacy AABB validator maradhat diagnosztikának, de nem lehet binding PASS gate.

## Kötelező források

Olvasd el először:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/nesting_engine/lv8_density_task_index.md
codex/reports/nesting_engine/development_plan_packing_density_20260515.md
canvases/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t05_phase0_polygon_validation_gate.yaml
codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
```

Ha a T04 report nem `PASS` vagy `PASS_WITH_NOTES`, állj meg és írj `FAIL/BLOCKED` T05 reportot. Ne módosíts production kódot.

## Scope

Engedélyezett production módosítások:

```text
scripts/experiments/lv8_polygon_validator.py
scripts/experiments/lv8_2sheet_claude_search.py
tests/test_lv8_density_polygon_validator.py
tests/test_lv8_density_polygon_validation_summary.py
```

Engedélyezett artefaktok:

```text
codex/codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.verify.log
```

Tilos módosítani:

```text
rust/nesting_engine/src/**
worker/cavity_validation.py
vrs_nesting/config/nesting_quality_profiles.py
```

Ha mégis ezek valamelyikének módosítása tűnik szükségesnek, ne javítsd automatikusan; állj meg, és dokumentáld `FAIL/BLOCKED` reportban.

## Végrehajtási lépések

### 1) Előfeltétel és audit

Ellenőrizd:

```bash
ls scripts/experiments/lv8_2sheet_claude_validate.py
ls worker/cavity_validation.py
ls scripts/benchmark_cavity_v2_lv8.py
ls scripts/experiments/lv8_2sheet_claude_search.py
```

Auditáld:

- `scripts/experiments/lv8_2sheet_claude_validate.py` docstringjét és outputját.
- `worker/cavity_validation.py::validate_cavity_plan_v2` szignatúráját.
- `scripts/benchmark_cavity_v2_lv8.py` `validate_cavity_plan_v2()` hívási mintáját.
- `scripts/experiments/lv8_2sheet_claude_search.py` T04 utáni `summary` összerakását.

A reportban rögzítsd: legacy AABB validator = non-binding diagnostic.

### 2) Implementáld a polygon validátort

Hozd létre:

```text
scripts/experiments/lv8_polygon_validator.py
```

Javasolt CLI:

```bash
python3 scripts/experiments/lv8_polygon_validator.py \
  --fixture <fixture.json> \
  --prepacked-input <run_dir>/prepacked_solver_input.json \
  --solver-stdout <run_dir>/solver_stdout.json \
  --cavity-plan <run_dir>/cavity_plan.json \
  --required-instances 276 \
  --spacing-mm 10 \
  --margin-mm 10 \
  --out <run_dir>/polygon_validation.json
```

Output JSON minimális séma:

```json
{
  "validation_kind": "polygon-aware",
  "valid_polygon_gate": true,
  "quantity_ok": true,
  "placed_instances": 276,
  "required_instances": 276,
  "unplaced_count": 0,
  "sheets_used": 2,
  "boundary_count": 0,
  "overlap_count": 0,
  "clearance_count": 0,
  "missing_geometry_count": 0,
  "cavity_validation_available": true,
  "cavity_validation_issue_count": 0,
  "issues_sample": [],
  "legacy_aabb_validator": false
}
```

A top-level sheet validation használjon polygonokat, ne AABB-t végső döntéshez. Shapely használható.

Figyelj a solver koordináta-konvencióra. Ne találj ki új transzformációt: nézd meg a legacy validator és a worker cavity validator transzformációját, majd a reportban rögzítsd a választást.

### 3) Kösd be a harnessbe

Módosítsd:

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

A `run_one()` végén:

- hozd létre `<out_dir>/polygon_validation.json`,
- tedd a summaryba:

```python
"polygon_validation": polygon_validation,
"valid_quantity_gate": quantity_gate,
"valid_polygon_gate": polygon_validation.get("valid_polygon_gate"),
```

A végső valid logika:

```python
valid = completion_gate and quantity_gate and polygon_validation.get("valid_polygon_gate") is True
```

A legacy AABB validator nem lehet binding gate.

### 4) Tesztek

Hozz létre:

```text
tests/test_lv8_density_polygon_validator.py
tests/test_lv8_density_polygon_validation_summary.py
```

Minimum esetek:

1. valid non-overlap fixture,
2. polygon overlap invalid,
3. boundary / margin violation invalid,
4. clearance / spacing violation invalid,
5. summary `valid=false`, ha `valid_polygon_gate=false`.

A tesztek ne futtassanak hosszú LV8 benchmarkot és ne igényeljenek Rust buildet.

## Kötelező ellenőrzések

Futtasd:

```bash
python3 -m py_compile scripts/experiments/lv8_polygon_validator.py
python3 -m pytest tests/test_lv8_density_polygon_validator.py -q
python3 -m pytest tests/test_lv8_density_polygon_validation_summary.py -q
```

Majd:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
```

Ha a két tesztfájl összevonva készült, a reportban írd le a tényleges parancsot.

## Report és checklist

Hozd létre:

```text
codex/codex_checklist/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
```

A report kötelezően tartalmazza:

- státusz: PASS / PASS_WITH_NOTES / FAIL / BLOCKED,
- validációs útvonal audit,
- választott polygon transzformációs konvenció,
- output JSON séma,
- harness summary valid gate diff,
- célzott tesztek eredménye,
- DoD → Evidence Matrix,
- AUTO_VERIFY blokk,
- legfeljebb 5 advisory note,
- T06 follow-up.

## STOP feltételek

Állj meg és írj `FAIL/BLOCKED` reportot, ha:

- T04 nem PASS/PASS_WITH_NOTES,
- nem tudsz polygon-aware gate-et létrehozni,
- a validator csak AABB-t használna binding döntéshez,
- Rust vagy worker validation módosítás lenne szükséges T05-ben,
- a summary `valid` továbbra is true lehet polygon gate failure mellett.
