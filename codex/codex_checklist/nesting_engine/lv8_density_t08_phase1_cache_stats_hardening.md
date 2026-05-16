# T08 Checklist — lv8_density_t08_phase1_cache_stats_hardening

- [x] Kötelező források beolvasva (`AGENTS.md`, Codex/QA szabályok, T08 canvas/YAML/runner, T07 report).
- [x] T07 előfeltétel ellenőrizve: `PASS_WITH_NOTES` (`codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md`).
- [x] `rust/nesting_engine/src/nfp/cache.rs` bővítve: `clear_all_events`, `peak_entries`, kumulatív hit/miss megtartás `clear_all()` után.
- [x] Debug cache log bővítve új mezőkkel.
- [x] `rust/nesting_engine/src/placement/nfp_placer.rs` bővítve: `nfp_cache_clear_all_events`, `nfp_cache_peak_entries`, `Default` és `merge_from` frissítve.
- [x] `rust/nesting_engine/src/multi_bin/greedy.rs` frissítve: egyetlen `nfp_cache.stats()` read + 3 végállapot mező export.
- [x] `scripts/experiments/lv8_2sheet_claude_search.py` normalizáció frissítve az új mezőkre.
- [x] `pending_phase1_fields` lezárva (üres lista).
- [x] `tests/test_lv8_density_engine_stats_export.py` frissítve (új mezők + pending lezárás + backward-compatible `None` esetek).
- [x] Új Rust teszt létrehozva: `rust/nesting_engine/tests/nfp_cache_stats_hardening.rs`.
- [x] `cargo check -p nesting_engine` futtatva (`rust/nesting_engine` könyvtárból) — PASS.
- [x] `cargo test -p nesting_engine --test nfp_cache_stats_hardening -- --nocapture` futtatva — PASS (4/4).
- [x] `python3 -m pytest tests/test_lv8_density_engine_stats_export.py` futtatva — PASS (18/18).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md` futtatva.
