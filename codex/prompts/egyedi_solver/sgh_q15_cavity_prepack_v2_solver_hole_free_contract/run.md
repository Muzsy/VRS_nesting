# Runner — SGH-Q15 Cavity prepack v2 solver-hole-free contract hardening

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q15 replacement taskot.

## Fontos

A korábbi `sgh_q15_cde_hole_cavity_semantics_foundation` csomagot ne használd. Az rossz irány volt.

A fő solver cavity_prepack_v2 után nem kaphat belső furatot/kivágást. Q15 célja a prepack/metadata/validation contract keményítése.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q15_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production módosítás nélkül.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
worker/cavity_prepack.py
worker/cavity_validation.py
worker/result_normalizer.py
worker/main.py
worker/engine_adapter_input.py
canvases/nesting_engine/cavity_v2_t04_plan_v2_contract.md
canvases/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md
canvases/nesting_engine/cavity_v2_t08_exact_nested_validator.md
canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q15_cavity_prepack_v2_solver_hole_free_contract.yaml
```

## Alapállítás

Cavity prepack v2 architektúra:

```text
base input: holes/cavities létezhetnek
prepack: kiválasztja és validálja az internal cavity placementeket
solver input: hole-free outer-only virtual parentek és top-level partok
solver output: virtual parent placementek
normalizer: cavity_plan_v2 alapján visszaállítja internal child placementeket
validator: validate_cavity_plan_v2 ellenőrzi az exact cavity tervet
```

A fő solver nem lehet hole-aware CDE solver.

## Kötelező audit parancs

```bash
rg -n "build_cavity_prepacked_engine_input_v2|validate_prepack_solver_input_hole_free|holes_points_mm\": \[\]|cavity_plan_v2|placement_trees|quantity_delta|validate_cavity_plan_v2|internal_cavity" worker tests docs canvases codex
```

## Implementációs cél

1. `build_cavity_prepacked_engine_input_v2(enabled=True)` után:

```text
out_input["parts"][*]["holes_points_mm"] == []
```

2. Production boundary:

```text
hole-os solver input ne mehessen a fő solverhez silent módon
```

3. Metadata preservation:

```text
virtual_parts
placement_trees
quantity_delta
instance_bases
diagnostics
summary
```

4. Expansion:

```text
virtual parent solver placement -> top_level_parent row + internal_cavity child rows
```

5. Validation:

```text
validate_cavity_plan_v2 fut és fail esetén nincs success
```

## Nem cél

```text
main solver CDE hole-aware collision
part holes átadása a Rust/main solvernek
cavity_prepack_v2 kiváltása
DXF/preflight refaktor
új optimizer/search stratégia
```

## Kötelező tesztek

Minimum:

```text
cavity_prepack_v2_outputs_hole_free_solver_input
cavity_prepack_v2_virtual_parent_has_empty_holes_points
cavity_prepack_v2_remaining_top_level_parts_have_empty_holes_points
validate_prepack_solver_input_hole_free_rejects_any_holes
cavity_prepack_v2_preserves_placement_tree_metadata
cavity_prepack_v2_quantity_delta_matches_internal_and_top_level
result_normalizer_expands_virtual_parent_to_internal_cavity_rows
validate_cavity_plan_v2_rejects_child_outside_cavity
validate_cavity_plan_v2_rejects_child_child_overlap
production_worker_rejects_or_blocks_hole_passthrough_without_prepack
```

## Verify

Futtasd a repo standard szerint, legalább:

```bash
python -m pytest tests worker -q -k "cavity or prepack or normalizer"
python -m pytest -q
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q16_STATUS: READY`.

## Output

Hozd létre/frissítsd:

```text
canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q15_cavity_prepack_v2_solver_hole_free_contract.yaml
codex/prompts/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract/run.md
codex/codex_checklist/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
docs/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.verify.log
```

PASS esetén:

```text
első sor: PASS
vége: SGH-Q16_STATUS: READY
```
