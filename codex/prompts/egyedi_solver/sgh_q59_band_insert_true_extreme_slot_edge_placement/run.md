# Runner — Q59 BandInsert true-extreme slot-edge placement

Hajtsd végre a canvas + goal YAML alapján a
`sgh_q59_band_insert_true_extreme_slot_edge_placement` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q59_BandInsert_true_extreme_slot_edge_placement.md
codex/reports/egyedi_solver/sgh_q55b_fix_one_part_sheet_edge.md
canvases/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q59_band_insert_true_extreme_slot_edge_placement.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q59_band_insert_true_extreme_slot_edge_placement.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- a fallback (band_insert_seeds bbox út) nem törölhető az új út bizonyítása előtt
- nincs bbox-only slot fit elfogadás; a slot bbox nem exact szabad tér
- continuous BandInsert rotációk nem snappelhetők 0/90/180/270-re
- a meglévő placed partok nem hagyhatók figyelmen kívül a validációnál
- nincs NFP, nincs part-id hack, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- VRS_BAND_INSERT_TRUE_EXTREME gate default off → no-regression

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert_slot_edge
VRS_BAND_INSERT_TRUE_EXTREME=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert_slot_edge
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. A
reportban magyarázd el, hogyan különbözik a slot-edge alignment a sheet-edge alignmenttől. PASS csak
zöld verify + teljesült DoD esetén.
