# T05w Checklist — NFP Provider Selection + Cache Key Safety

## Státusz: PASS

## Checklist

- [x] `NfpKernel` enum előkészítve több kernelre (3 variant: OldConcave, ReducedConvolutionExperimental, CgalReference)
- [x] Default kernel továbbra is `OldConcave`
- [x] `NfpProviderConfig` létrehozva `Default` impl-mal
- [x] `create_nfp_provider` factory létrehozva
- [x] Nem implementált providerek explicit unsupported hibát adnak (`NfpError::UnsupportedKernel`)
- [x] `NfpCacheKey` tartalmazza a `nfp_kernel: NfpKernel` mezőt
- [x] Cache konstrukciók frissítve minden helyen (`nfp_placer.rs`, `cache.rs` tesztek)
- [x] Failure / timeout nincs sikeres cache entryként tárolva
- [x] greedy / SA / multi-sheet / compaction nem módosult
- [x] CGAL nincs bekötve
- [x] reduced_convolution nincs bekötve
- [x] production Dockerfile nincs módosítva
- [x] cache nagy refactor nincs (csak kernel mező hozzáadva)
- [x] `cargo check` PASS (0 error, 28 pre-existing warning)
- [x] `cargo test` PASS vagy ismert pre-existing fail dokumentálva (59/60 PASS, 1 pre-existing CFR fail)
- [x] Nincs T08 indítás

## Megjegyzések

- Pre-existing CFR tesztfail (`cfr_sort_key_precompute_hash_called_once_per_component`): 8 vs 6 hívás — nem T05w regresszió, dokumentálva a riportban.
- CLI `--nfp-kernel` flag nincs bekötve — ez külön task (T05w2).
- `create_nfp_provider` nem publikus a lib API-ban — a jelenlegi binary call graph nem igényli a változtatást.
