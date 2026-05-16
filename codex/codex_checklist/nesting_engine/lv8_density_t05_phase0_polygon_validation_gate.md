# T05 Checklist — lv8_density_t05_phase0_polygon_validation_gate

Pipálható DoD lista a canvas
[lv8_density_t05_phase0_polygon_validation_gate.md](../../../canvases/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
([codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md](../../reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md)).

## Repo szabályok és T0x előzmények

- [x] `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
      `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md` beolvasva.
- [x] T00–T04 reportok ellenőrizve, T04 státusz: PASS.
- [x] T05 canvas + YAML beolvasva.

## Audit

- [x] `lv8_2sheet_claude_validate.py` auditálva: `validation_kind = "AABB-conservative"`,
      nem binding gate — diagnosztikai szerepe megmarad.
- [x] `worker/cavity_validation.py::validate_cavity_plan_v2` szignatúrája és
      `_build_placed_polygon` koordináta-konvenciója auditálva.
- [x] `scripts/benchmark_cavity_v2_lv8.py` hívási mintája auditálva (`strict=False`).
- [x] `lv8_2sheet_claude_search.py` T04 utáni összesítése auditálva.
- [x] Koordináta-konvenció döntés rögzítve: rotate → normalize → translate
      (cavity_validation.py konvenciója, nem a legacy AABB validator konvenciója).

## Polygon validator implementáció

- [x] `scripts/experiments/lv8_polygon_validator.py` létrehozva.
- [x] `_build_placed_polygon()`: affinity.rotate(origin=(0,0)) → normalize
      (shift min_x/min_y → 0) → affinity.translate — egyezik `cavity_validation.py`-val.
- [x] Top-level ellenőrzések: MISSING_OUTER_POINTS, BOUNDARY_VIOLATION,
      POLYGON_OVERLAP (`area > _EPS=1e-3`), CLEARANCE_VIOLATION.
- [x] Cavity plan v2 híváslánc: `validate_cavity_plan_v2(strict=False)` bekötve.
- [x] `valid_polygon_gate`: minden counter == 0 esetén True.
- [x] Output JSON séma: `validation_kind`, `valid_polygon_gate`, `quantity_ok`,
      `placed_instances`, `required_instances`, `unplaced_count`, `sheets_used`,
      `boundary_count`, `overlap_count`, `clearance_count`, `missing_geometry_count`,
      `cavity_validation_available`, `cavity_validation_issue_count`,
      `cavity_validation_issues_sample`, `issues_sample`, `legacy_aabb_validator`.
- [x] `legacy_aabb_validator: false` minden esetben.
- [x] `python3 -m py_compile scripts/experiments/lv8_polygon_validator.py` → OK.

## Harness bekötés

- [x] `lv8_2sheet_claude_search.py` módosítva: `_EXPERIMENTS_DIR` sys.path-ba,
      `from lv8_polygon_validator import validate as _polygon_validate`.
- [x] `completion_gate` és `quantity_gate` változók elkülönítve.
- [x] `_polygon_validate()` hívás bekötve a `run_one()` végén.
- [x] `polygon_validation.json` kiírva az `out_dir`-be.
- [x] Summary: `valid_quantity_gate`, `valid_polygon_gate`, `polygon_validation` mezők.
- [x] Végső `valid` logika: `completion_gate and quantity_gate and
      polygon_validation.get("valid_polygon_gate") is True`.
- [x] Legacy AABB validator nem binding gate — megmaradt nem-binding diagnosztikának.

## Tesztek

- [x] `tests/test_lv8_density_polygon_validator.py` létrehozva (13 teszt):
      TestValidNonOverlap, TestPolygonOverlap, TestBoundaryViolation,
      TestClearanceViolation, TestMissingGeometry, TestPolygonTransform.
- [x] `tests/test_lv8_density_polygon_validation_summary.py` létrehozva (12 teszt):
      TestSummaryValidGate, TestSummaryStructure, TestPolygonGateIsBinding.
- [x] `python3 -m pytest tests/test_lv8_density_polygon_validator.py -q` → 13 passed.
- [x] `python3 -m pytest tests/test_lv8_density_polygon_validation_summary.py -q` → 12 passed.
- [x] Hosszú LV8 benchmark nem futott, Rust build nem szükséges.

## Scope compliance

- [x] `rust/nesting_engine/src/**` — nem módosítva.
- [x] `worker/cavity_validation.py` — nem módosítva.
- [x] `vrs_nesting/config/nesting_quality_profiles.py` — nem módosítva.
