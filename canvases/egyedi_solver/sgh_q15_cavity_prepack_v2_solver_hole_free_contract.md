# SGH-Q15 — Cavity prepack v2 solver-hole-free contract hardening

## Státusz

Replacement task. A korábbi `sgh_q15_cde_hole_cavity_semantics_foundation` csomagot **ne futtasd**; az rossz irány volt, mert a fő solver nem kaphat belső furatot/kivágást.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q15_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell?

A repo alapján a cavity prepack v2 architektúra lényege:

```text
prepack előtt: part holes/cavities feldolgozása és child placement döntés
solver input: outer-only virtual parentek + outer-only top-level partok
solver után: cavity_plan_v2 alapján expansion / normalizer / export visszaállítja a child placementeket és hole metadata-t
```

A fő solver tehát **nem lehet hole-aware solver**. Nem kaphat `holes_points_mm`/belső kivágás geometriát. Ha hole-os input kerülne hozzá, az architekturális hiba.

A Q15 célja ezért nem CDE hole-aware collision a fő solverben, hanem:

```text
cavity_prepack_v2 contract hardening
solver_input hole-free invariant
cavity_plan_v2 metadata preservation
post-solve expansion / validation gate
no silent geometry loss
```

## Repo evidence, amit ellenőrizni kell

A friss repo-ban ezek a döntő pontok:

```text
worker/cavity_prepack.py
- _rotation_shapes(): outer-only proxy; holes excluded from fit geometry, exact holes preserved for export.
- build_cavity_prepacked_engine_input_v2(): virtual solver parts holes_points_mm=[].
- non-holed top-level solver parts holes_points_mm=[].
- validate_prepack_solver_input_hole_free(): explicit gate.

worker/main.py
- cavity_prepack_enabled esetén build_cavity_prepacked_engine_input_v2(...)
- requested part_in_part_policy == prepack esetén validate_prepack_solver_input_hole_free(...)
- run végén validate_cavity_plan_v2(...)

worker/result_normalizer.py
- cavity_plan_v2 alapján virtual parent + internal_cavity placement tree flatten.
```

## Cél

Q15 keményítse meg és dokumentálja ezt az invariánst:

```text
MAIN_SOLVER_MUST_BE_HOLE_FREE
```

Konkrétan:

```text
1. cavity_prepack v2 után a solver input minden partján holes_points_mm == [] legyen.
2. virtual parent csak outer geometry-t kapjon, belső furat nélkül.
3. child/parent hole metadata ne vesszen el: cavity_plan_v2 placement_trees, quantity_delta, diagnostics megőrzi a visszaállításhoz szükséges adatot.
4. result normalizer az internal cavity child placementeket visszaállítja.
5. validate_cavity_plan_v2 fut a solver output után.
6. ha valamilyen útvonalon hole-os solver input jutna a fő solverhez, az fail/Unsupported legyen, nem silent CDE-hole support.
```

## Nem cél

```text
CDE hole-aware collision a fő solverben
part holes átadása a Rust/main solvernek
cavity_prepack_v2 kiváltása
új cavity placement optimizer
DXF/preflight refaktor
CDE default production bekapcsolása
Sparrow teljes port
```

## Scope

### Engedélyezett production fájlok

```text
worker/cavity_prepack.py
worker/cavity_validation.py
worker/result_normalizer.py
worker/main.py
worker/engine_adapter_input.py                 # csak ha solver-input gate miatt szükséges
worker/tests/ vagy tests/                      # repo-stílus szerint
```

### Dokumentáció / report

```text
canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q15_cavity_prepack_v2_solver_hole_free_contract.yaml
codex/prompts/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract/run.md
codex/codex_checklist/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.verify.log
docs/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

## Kötelező pre-audit

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
```

Futtasd és dokumentáld:

```bash
rg -n "build_cavity_prepacked_engine_input_v2|validate_prepack_solver_input_hole_free|holes_points_mm\": \[\]|cavity_plan_v2|placement_trees|quantity_delta|validate_cavity_plan_v2|internal_cavity" worker tests docs canvases codex
```

## Kötelező javítások / hardening

### 1. Solver input hole-free invariant

Bizonyítsd és ha kell keményítsd:

```text
build_cavity_prepacked_engine_input_v2(..., enabled=True)
  -> out_input["parts"][*]["holes_points_mm"] == []
```

Ez vonatkozzon:

```text
virtual module/parent solver parts
remaining top-level non-holed parts
bármely generated solver part
```

### 2. Global guard a production boundary-n

A worker production pathon ne csak opcionális helyen legyen gate. A cél:

```text
ha engine_backend == nesting_engine_v2 és a fő solver felé megy input,
akkor explicit ellenőrizhető legyen, hogy a solver input hole-free,
ha a pipeline policy szerint cavity_prepack/prepack aktív.
```

Ha olyan profile létezik, ahol cavity_prepack nem aktív, de hole-os base input menne a solverbe, azt dokumentáld és dönts:

```text
- fail Unsupported / WorkerError
vagy
- explicit outer-only solidify policy, ha ez már dokumentáltan létezik
```

Ne hagyj silent hole passthrough-t a fő solver felé.

### 3. Metadata preservation

Cavity prepack v2 ne dobja el a visszaállításhoz kellő adatot:

```text
cavity_plan.version == cavity_plan_v2
virtual_parts
placement_trees
quantity_delta
instance_bases
diagnostics
summary
```

Külön ellenőrizd:

```text
parent_part_revision_id
parent_instance
child part_revision_id / child_instance
parent_cavity_index
local transform
cavity_tree_depth
```

### 4. Expansion / normalizer gate

`result_normalizer.py` és/vagy a kapcsolódó worker flow bizonyítsa:

```text
solver placement of virtual parent
  -> top_level_parent placement row
  -> internal_cavity child placement rows
  -> quantity_delta internal_qty == actual internal child rows
```

### 5. Cavity validation gate

`validate_cavity_plan_v2(...)` futása legyen kötelező a prepack v2 run végén, és fail esetén ne legyen successful run.

Ellenőrizendő:

```text
child inside selected cavity
no child-child overlap in same cavity
transform composition valid
quantity_delta valid
nested depth limit valid
```

### 6. No main solver hole-aware CDE requirement

A Q15 reportban explicit szerepeljen:

```text
The main solver remains outer-only after cavity_prepack_v2.
Q15 does not implement CDE hole-aware item collision in the main solver.
Cavity semantics live in prepack + cavity_plan_v2 + validation + expansion.
```

## Kötelező tesztek

Adj vagy erősíts célzott teszteket, minimum:

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

Ha egyes worker integration tesztek túl drágák, adj kis unit fixture-t közvetlenül a `worker/cavity_prepack.py`, `worker/cavity_validation.py`, `worker/result_normalizer.py` szinten.

## Verify

Futtasd legalább:

```bash
python -m pytest tests worker -q -k "cavity or prepack or normalizer"
python -m pytest -q
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

Ha a repo standard tesztparancsa eltér, használd a repo szabályfájljait, de a reportban pontosan szerepeljen a futtatott parancs.

Ha bármelyik fail: report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q16_STATUS: READY`.

## PASS feltételek

PASS csak akkor lehet, ha:

```text
- cavity_prepack_v2 után a solver input bizonyítottan hole-free.
- main solver hole-aware CDE nem lett követelményként bevezetve.
- cavity metadata megmarad a planben.
- result normalizer/validation visszaállítja és ellenőrzi az internal placements-t.
- nincs silent hole passthrough a fő solver felé.
- verify zöld.
```

PASS esetén:

```text
első sor: PASS
report vége: SGH-Q16_STATUS: READY
```
