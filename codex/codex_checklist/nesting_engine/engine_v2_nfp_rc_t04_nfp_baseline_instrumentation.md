# Codex checklist - engine_v2_nfp_rc_t04_nfp_baseline_instrumentation

- [x] AGENTS.md + T04 master runner/canvas/YAML/runner prompt beolvasva
- [x] T04 altal eloirt valos fajlok beolvasva (`nfp_fixture.rs`, `nfp/mod.rs`, `nfp/concave.rs`, T01 fixture-ok)
- [x] `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` letrehozva
- [x] Bin CLI implementalva (`--fixture`, `--timeout-ms`, `--part-a-only`, `--part-b-only`, `--output-json`)
- [x] JSON output tartalmazza: `fragment_count_a`, `fragment_count_b`, `pair_count`, `timed_out`, `verdict`
- [x] Timeout explicit `TIMEOUT` verdictdel kezelve (nem success)
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` baseline_metrics frissitve
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` baseline_metrics frissitve
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` baseline_metrics frissitve
- [x] Mindharom fixture benchmark futas megtortent (`--timeout-ms 5000`)
- [x] `cargo run --bin nfp_pair_benchmark -- --help` PASS
- [x] Output schema ellenorzes PASS (`lv8_pair_01`, `--output-json`)
- [x] `baseline_metrics` mezok nem nullak a 3 fixture-ben
- [x] `git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs` ures (erintetlen)
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md` PASS
