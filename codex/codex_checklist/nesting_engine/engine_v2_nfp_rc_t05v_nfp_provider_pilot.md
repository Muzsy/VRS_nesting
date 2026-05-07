# T05v NFP Provider Interface Pilot — Checklist

## Feltételek

- [x] `NfpProvider` trait létrejött
- [x] `NfpKernel::OldConcave` létrejött
- [x] `NfpProviderResult` létrejött
- [x] `OldConcaveProvider` a meglévő convex/concave dispatch-et használja
- [x] `nfp_placer.rs` provider útvonalon számol NFP-t
- [x] Alapértelmezett kernel továbbra is old_concave
- [x] greedy / SA / multi-sheet optimalizáló nem lett újraírva
- [x] CGAL nincs bekötve
- [x] reduced_convolution experimental nincs bekötve
- [x] production Dockerfile nincs módosítva
- [x] cache nagy refactor nincs
- [x] cargo check PASS
- [x] cargo test PASS vagy ismert, dokumentált okból PARTIAL
- [x] nincs T08 indítás

## Teszt eredmények

| Teszt | Eredmény | Megjegyzés |
|-------|----------|------------|
| cargo check | PASS | 0 error, 28 pre-existing warning |
| cargo test (lib) | 59/60 PASS | 1 pre-existing CFR fail |
| nfp_pair_benchmark lv8_pair_01 | TIMEOUT (várt) | toxic concave, old_concave is timeout-ol |
| nfp_pair_benchmark lv8_pair_02 | TIMEOUT (várt) | toxic concave, old_concave is timeout-ol |

## Módosított fájlok

- `rust/nesting_engine/src/nfp/provider.rs` — ÚJ
- `rust/nesting_engine/src/nfp/mod.rs` — +1 sor
- `rust/nesting_engine/src/placement/nfp_placer.rs` — import + wrapper

## Személyes megjegyzések

- Binary/lib type mismatch: explicit konverzió szükséges a wrapper-ben
- Provider interface diagnosztika: `[NFP DIAG] provider=old_concave` aktív
- Pre-exisztáló CFR tesztfail nem kapcsolódik T05v-hez
