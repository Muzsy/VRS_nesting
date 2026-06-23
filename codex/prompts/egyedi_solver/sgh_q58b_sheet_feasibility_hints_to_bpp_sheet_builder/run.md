# Runner — Q58B SheetFeasibilityHints → BPP / sheet-builder

Hajtsd végre a canvas + goal YAML alapján a
`sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q58B_SheetFeasibilityHints_to_BPP_sheet_builder.md
canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.yaml
```

Előfeltétel: Q58A `SheetFeasibilityHints` elérhető.

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- a hint advisory; nem skippeli az exact CDE validációt
- nincs 2-sheet eredmény kényszerítés proof nélkül
- valid partial nem dobható el csak mert a target kvóta bukott (best-partial preservation kötelező)
- nincs LV8 distribution hardcode; a fallback nem rejthető el
- nincs NFP, nincs bbox collision shortcut, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- VRS_SHEET_FEASIBILITY_HINTS gate default off → no-regression (byte-azonos)

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp
VRS_SHEET_FEASIBILITY_HINTS=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. PASS csak
zöld verify + teljesült DoD esetén. A reportban bizonyítsd, hogy a 2/3 → final 1/3 regresszió
konstrukció szerint lehetetlen.
