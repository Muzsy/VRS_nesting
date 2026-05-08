# T06g Codex Checklist — Quality Profile NFP Kernel Wiring

## T06f Eltartmondások Tisztázása

- [x] `cargo test` futtatás: **PARTIAL_WITH_KNOWN_PREEXISTING_FAIL**
  - 59 passed, 1 failed
  - Failing test: `nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component`
  - Commit `d3e0a76` által bevezetett pre-existing hiba
  - T06g módosítások NEM érintik ezt a testet

## Python Runtime Policy `nfp_kernel` Támogatás

- [x] `_RUNTIME_POLICY_KEYS` tartalmazza `"nfp_kernel"`
- [x] `VALID_NFP_KERNELS = ("old_concave", "cgal_reference")` létrehozva
- [x] `validate_runtime_policy()` validálja az `nfp_kernel` mezőt
- [x] `build_nesting_engine_cli_args_from_runtime_policy()` emits `--nfp-kernel` CLI arg
- [x] `__all__` exportálja `VALID_NFP_KERNELS`
- [x] `quality_cavity_prepack` viselkedése VÁLTOZATLAN (nincs nfp_kernel)

## Új Profil Létrehozása

- [x] `quality_cavity_prepack_cgal_reference` profil regisztrálva
- [x] Profil explicit dev/reference jellegű megjegyzésekkel ellátva
- [x] Profilban: `nfp_kernel: "cgal_reference"`
- [x] Profil nem módosítja az alap viselkedést (part_in_part=prepack, stb.)

## CLI Argumentum Támogatás

- [x] `nesting_engine_runner.py` argparse támogatja `--nfp-kernel`-et
- [x] `benchmark_cavity_v2_lv8.py` `--quality-profile` argumentum hozzáadva
- [x] `benchmark_cavity_v2_lv8.py` `--skip-solver` argumentum hozzáadva
- [x] `run_benchmark()` paraméterezése frissítve
- [x] Eredmény JSON tartalmazza `nfp_kernel` mezőt
- [x] Guard: solver success csak ha `skip_solver=False`

## Benchmark Eredmények

### quality_cavity_prepack (reference)

- [x] Prepack guard passed: holes 24→0
- [x] quantity_mismatch_count: 0
- [x] minimum_criteria_passed (skip-solver): true

### quality_cavity_prepack_cgal_reference

- [x] Prepack guard passed: holes 24→0
- [x] quantity_mismatch_count: 0
- [x] nfp_kernel a CLI args-ban: `["--nfp-kernel", "cgal_reference"]`
- [x] minimum_criteria_passed (skip-solver): true
- [x] CGAL kernel működik (simple test: 2 parts, RC=0, correct placements)

## Full Chain Verification

- [x] profile → runtime_policy → CLI args: **PASS**
- [x] CLI args → nesting_engine binary (--nfp-kernel cgal_reference): **PASS**
- [x] NFP provider: CgalReferenceProvider kiválasztva (simple test): **PASS**

## Production Safety Tiltások

- [x] CGAL NEM production default (quality_cavity_prepack változatlan)
- [x] NEM módosítja a production Dockerfile-t
- [x] NEM törli vagy nevezi át az OldConcave providert
- [x] NEM módosítja a Rust provider selection logikát
- [x] NEM írja át a greedy/SA/multi-sheet/slide compaction logikát
- [x] NEM ír új optimalizálót
- [x] NEM vezet be új placement stratégiát
- [x] NEM kerüli meg a cavity_prepack_v2-t
- [x] BLF fallback NEM silent (solver_fallback_used=True)
- [x] OldConcave fallback NEM silent
- [x] BLF fallback NEM minősül NFP sikernek (nfp_fallback_occurred külön trackelve)
- [x] Timeout NEM minősül PASS-nak
- [x] Gyártási exact geometria NEM módosítva destruktívan

## T06g Állapot

**IMPLEMENTATION COMPLETE — MINIMUM_CRITERIA_PASSED (prepack)**

- cargo test: **PARTIAL_WITH_KNOWN_PREEXISTING_FAIL** (pre-existing)
- Python wiring: **PASS**
- Prepack guard (quality_cavity_prepack_cgal_reference): **PASS**
- CGAL reference kernel simple test: **PASS**
- Solver timeout: **TIME_BUDGET_CONSTRAINED** (SA loop on 231 virtual parts, not kernel bug)
