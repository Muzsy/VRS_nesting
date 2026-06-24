# Checklist - SGH-Q67 Simultaneous critical production cutover

- [x] A production builder gate alatt explicit simultaneous authority probat futtat.
- [x] Same-part 2-es critical group eseten a simultaneous modul committed layoutot tud visszaadni.
- [x] A 3-as group best partial / rejection summary explicit diagnosztikaban latszik.
- [x] Elkeszult a `artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json`.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q67_simultaneous_cutover -- --nocapture` lefutott.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q67_simultaneous_critical_production_cutover.md` PASS.
