# Runner — Q56C SheetEdgePlacementCatalog (edge-corner Anchor candidate-ek)

Hajtsd végre a canvas + goal YAML alapján a
`sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q56C_SheetEdgePlacementCatalog_edge_corner_anchor_candidates.md
codex/reports/egyedi_solver/sgh_q55b_fix_one_part_sheet_edge.md
canvases/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- nem csak több 90/270 seed; a center nem maradhat az egyetlen production Anchor candidate
- spacing nélküli bbox nem lehet final placement truth
- aktív margin mellett nem illeszt a nyers sheet határhoz (bizonyítsd a margin-shrink-et)
- a generált candidate-eket a production Anchor út ténylegesen használja
- nincs NFP, nincs bbox collision shortcut, nincs part-id hack
- nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- Q55B one-part true-extreme sheet-edge proof nem regresszálhat

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_edge_anchor_catalog
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_sheet_edge_anchor
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. A report
mondja ki, hogy a center placement fallback, nem az egyetlen Anchor policy. PASS csak zöld verify +
teljesült DoD esetén.
