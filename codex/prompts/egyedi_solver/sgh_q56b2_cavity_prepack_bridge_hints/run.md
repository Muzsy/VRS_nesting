# Runner — Q56B2 CavityPrepackBridgeHints

Hajtsd végre a canvas + goal YAML alapján a `sgh_q56b2_cavity_prepack_bridge_hints` taskot.

## Fontos alapállítás

```text
A cavity prepack v2 már meglévő pre-solver réteg (worker oldalon).
A Rust/Sparrow solvernek hole-free inputot kell kapnia.
Ez a task bridge hint / diagnosztika / szerződés — NEM cavity újraírás Rustban.
```

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q56B2_CavityPrepackBridgeHints.md
worker/cavity_prepack.py
worker/cavity_validation.py
worker/result_normalizer.py
worker/engine_adapter_input.py
worker/main.py
canvases/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b2_cavity_prepack_bridge_hints.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b2_cavity_prepack_bridge_hints.yaml`

## Kötelező audit parancs

```bash
rg -n "build_cavity_prepacked_engine_input_v2|validate_prepack_solver_input_hole_free|cavity_plan_v2|validate_cavity_plan_v2|holes_points_mm|internal_cavity" worker tests docs canvases codex
```

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- nincs cavity packing reimplementáció Rustban
- cavity/hole logika nem kerülhet a Rust fősolverbe
- nincs silent hole passthrough a fő solver felé
- holes nem kezelhető elérhető cavity-ként a Rust Sparrow solverben
- validáció nem gyengíthető fixture-passért
- result_normalizer expansion nem törhet
- nincs NFP, nincs bbox collision shortcut, nincs part-id hack
- nincs spacing/margin gyengítés
- CDE/final exact validation marad az igazság

## Célzott tesztek / runnerek

```bash
python3 -m pytest tests/worker/test_cavity_prepack_bridge_hints.py -q
python3 -m pytest tests worker -q -k "cavity or prepack or normalizer"
```

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. A report
explicit mondja ki: a vrs_solver top-level input hole-free a sikeres cavity prepack v2 után, és nem
készült Rust cavity prepack reimplementáció. PASS csak zöld verify + teljesült DoD esetén.
