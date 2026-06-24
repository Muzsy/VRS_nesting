# Checklist - SGH-Q66 SheetFeasibilityHints production cutover

- [x] A production builder explicit gate alatt valoban fogyasztja a Q58 hint-eket.
- [x] A critical queue hint-aware reorderrel tud futni.
- [x] A per-sheet target kvota es frontier extension diagnosztikailag latszik.
- [x] A best partial critical count/source es quota abandoned reason rogzitve van.
- [x] Elkészült a `artifacts/benchmarks/sgh_q66/sheet_feasibility_production_cutover.json`.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp -- --nocapture` lefutott.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` lefutott.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.md` PASS.
