# Codex Checklist — nfp_computation_concave

**Task slug:** `nfp_computation_concave`  
**Canvas:** `canvases/nesting_engine/nfp_computation_concave.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_concave.yaml`

---

## DoD

- [x] `nfp/mod.rs` integráció: `concave` + `boundary_clean` modulok és új `NfpError` variánsok (`NotSimpleOutput`, `OrbitLoopDetected`, `DecompositionFailed`).
- [x] `boundary_clean` implementálva: duplikált/záró pontok tisztítása, 0-hossz él és kollinearitás kezelése, CCW + lexikografikus start, i128 alapú önmetszés ellenőrzés.
- [x] Stabil konkáv alapútvonal implementálva: dekompozíció -> konvex NFP -> union -> boundary clean.
- [x] Opcionális orbitális exact réteg implementálva touching-group állapotgéppel, loop guarddal és fallback útvonallal.
- [x] Legalább 5 konkáv fixture létrehozva a `poc/nfp_regression/` alatt.
- [x] `poc/nfp_regression/README.md` bővítve a konkáv fixture contracttal.
- [x] Regressziós teszt bővítve konvex + konkáv fixture kezelésre, determinisztika és valid boundary ellenőrzéssel.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] Valós DXF alakzatpár-források rögzítve a canvasban (3 pár).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md` PASS.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` futtatva.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` futtatva.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md` futtatva.
