# SGH-Q66 - SheetFeasibilityHints production cutover

## Goal / Funkcio

Kotesd be a meglevo Q58A/Q58B `SheetFeasibilityHints` reteget a production
`build_critical_aware_seed()` builderbe, hogy a hint-ek tenylegesen hassanak a critical queue
sorrendre, a per-sheet target kvotara, a critical frontierre es a best-partial diagnozisra.

## Context / Hatter

A repoban a `sheet_feasibility.rs` es `sheet_feasibility_bpp.rs` mar megvalositja a hint-modelt es
a builder-oldali segedlogikat, de a production `bpp_reduction.rs` jelenleg csak annyit tesz, hogy
hint gate alatt felkapcsol egy best-partial tracker flaget. Az audit szerint a strategiai
queue/quota/frontier wiring emiatt meg mindig hianyzik a valos dontesi utbol.

## Source of truth

- `AGENTS.md`
- `tmp/audit/audit_2026_06_23.md`
- `canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md`
- `canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md`

## Scope

- Production `build_critical_aware_seed()` fogyassza a Q58 hint-eket explicit gate alatt.
- Hint-aware critical queue reorder.
- Hint-derived per-sheet kvota + bounded frontier extension.
- Best-partial tracker valodi production diagnozisokkal.
- Fokuszalt production boundary teszt + artifact.

## Out of scope

- Q60 simultaneous admission teljes atvagasa.
- Nyers layout-quality claim vagy 2-sheet guarantee.
- Hint gate nelkuli viselkedes valtoztatasa.

## Required implementation

1. Epuljon live `SheetFeasibilityHints` a builder altal latott solver-frame partokbol/sheets-bol.
2. `VRS_SHEET_FEASIBILITY_HINTS=1` alatt a critical queue hint-aware reorderrel fusson.
3. A critical frontier per sheet a hint target kvota alapjan bounded modon tudjon hosszabb maradni.
4. A builder rogzitese:
   - hints used
   - target distribution / target quota
   - queue reorder applied
   - frontier extension applied
   - best partial critical count / source
   - quota met / abandoned reason
5. Keszits production boundary tesztet, ami a valos solve utrol bizonyitja a hint wiringet.

## Required diagnostics

- `artifacts/benchmarks/sgh_q66/sheet_feasibility_production_cutover.json`

## Required tests / runners

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp -- --nocapture
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.md
```

## Acceptance criteria

```text
- A production builder explicit gate alatt valoban fogyasztja a SheetFeasibilityHints-et.
- A queue/quota/frontier wiring mar nem csak helper-szinten letezik.
- A best partial diagnozis explicit es oszinte.
- Gate-off viselkedes nem torik.
```
