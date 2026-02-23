# Codex Checklist — nfp_computation_convex

**Task slug:** `nfp_computation_convex`  
**Canvas:** `canvases/nesting_engine/nfp_computation_convex.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_convex.yaml`

---

## DoD

- [x] `compute_convex_nfp()` legalább 4 unit tesztet futtat PASS-al (kézzel megadott referenciaértékekkel).
- [x] Nem-konvex bemenet `Err(NfpError::NotConvex)` hibát ad (panic nélkül).
- [x] Üres polygon bemenet `Err(NfpError::EmptyPolygon)` hibát ad.
- [x] `NfpError` csak `NotConvex` és `EmptyPolygon` variánsokat tartalmaz (`InvalidInput` nincs).
- [x] `cross_product_i128()` helper létezik, az orientáció-ellenőrzések i128-on futnak.
- [x] `NfpCacheKey.rotation_steps_b` típusa `i16` (f64 nélkül a kulcsban).
- [x] Cache hit/miss statisztika debug szinten logolva.
- [x] Determinisztikus kimenet: azonos input kétszer futtatva azonos NFP csúcslistát ad.
- [x] `poc/nfp_regression/` könyvtár létrejött legalább 2 fixture-rel.
- [x] Fixture koordináták integer egységben vannak (nincs mm/SCALE konverzió a fixture szinten).
- [x] `rust/nesting_engine/tests/nfp_regression.rs` integrációs teszt PASS.
- [x] Integrációs teszt `canonicalize_ring` + egzakt `assert_eq!` összehasonlítást használ.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` PASS.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` futtatva.
