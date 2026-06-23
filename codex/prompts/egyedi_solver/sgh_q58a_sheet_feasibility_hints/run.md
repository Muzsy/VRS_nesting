# Runner — Q58A SheetFeasibilityHints

Hajtsd végre a canvas + goal YAML alapján a `sgh_q58a_sheet_feasibility_hints` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q58A_SheetFeasibilityHints.md
canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58a_sheet_feasibility_hints.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58a_sheet_feasibility_hints.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- area lower bound nem final sheet-count proof; minden becslés hint/probability (confidence/basis)
- nincs LV8-only target distribution hardcode; nincs part-id hack
- nem feltételez 2 sheetet csak mert area engedi; spacing/margin basis kötelező
- nincs placement mutáció ebben a taskban (Q58B köti be)
- nincs NFP, nincs bbox collision shortcut, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. PASS csak
zöld verify + teljesült DoD esetén.
