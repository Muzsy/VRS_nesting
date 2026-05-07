# T05x Checklist — CGAL Reference Provider

## Státusz: PASS

## Build & Compile

- [x] CgalReferenceProvider létrejött (`rust/nesting_engine/src/nfp/cgal_reference_provider.rs`)
- [x] `NfpProvider` trait-et implementálja
- [x] `cargo check` PASS (csak unused code warning-ok)
- [x] `cargo test --lib` PASS (60/60)

## NfpProvider Interface

- [x] `kernel() -> NfpKernel::CgalReference`
- [x] `kernel_name() -> "cgal_reference"`
- [x] `supports_holes() -> true`

## Guard & Opt-in

- [x] CGAL csak explicit env/config guard mögött fut (`NFP_ENABLE_CGAL_REFERENCE=1`)
- [x] Default kernel továbbra is `OldConcave`
- [x] `NFP_ENABLE_CGAL_REFERENCE` nélkül explicit hiba: `cgal_reference requires NFP_ENABLE_CGAL_REFERENCE=1`
- [x] `NFP_CGAL_PROBE_BIN` opcionális, default: `tools/nfp_cgal_probe/build/nfp_cgal_probe`

## Error Handling

- [x] CGAL binary missing → explicit `CgalBinaryNotFound` hiba
- [x] timeout → explicit `CgalSubprocessError` hiba
- [x] nonzero exit → explicit `CgalNonZeroExit` hiba
- [x] invalid JSON → explicit `CgalParseError` hiba
- [x] empty output → explicit `CgalEmptyOutput` hiba
- [x] NINCS silent fallback old_concave-ra

## Cache Key

- [x] Cache key kernel = `CgalReference` CGAL módban
- [x] CGAL és OldConcave cache nem keveredik

## CGAL Binary

- [x] `scripts/build_nfp_cgal_probe.sh` sikeres
- [x] `scripts/smoke_nfp_cgal_probe_lv8.sh` PASS (lv8_pair_01, lv8_pair_02, lv8_pair_03)

## Benchmark

- [x] `nfp_pair_benchmark` képes `cgal_reference` providerrel futni (`--nfp-kernel cgal_reference`)
- [x] Guard ellenőrzés: env nélkül `exit 1` + explicit hibaüzenet

## Production Constraints

- [x] CGAL nincs production Dockerfile-ban
- [x] Worker production runtime nem módosult
- [x] greedy / SA / multi-sheet / compaction nem módosult
- [x] Nincs új optimalizáló
- [x] Nincs OldConcaveProvider törlés

## Benchmark Eredmények

- [x] toxic lv8_pair_01 CGAL providerrel lefutott (SUCCESS, 186ms)
- [x] old_concave lv8_pair_01 default módban TIMEOUT (5000ms) — nem változott
- [x] lv8_pair_02 CGAL: SUCCESS (140ms)
- [x] lv8_pair_03 CGAL: SUCCESS (83ms)

## Tiltások

- [x] NINCS T08 indítás
- [x] NINCS production Dockerfile módosítás
- [x] NINCS silent fallback CGAL hibánál old_concave-ra
- [x] NINCS hibás CGAL output cache-elés
