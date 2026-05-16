# T07 Checklist — lv8_density_t07_phase1_0_cache_path_discovery_spike

- [x] Kötelező források beolvasva (`AGENTS.md`, Codex/QA szabályok, T07 canvas/YAML/runner, T06 reportok).
- [x] T06 előfeltétel ellenőrizve: `PASS_WITH_NOTES`, `hard_cut_decision=DEFER_HARD_CUT` (nem blokkoló).
- [x] T07 inventory fájlok ellenőrizve (`cache.rs`, `nfp_placer.rs`, `greedy.rs`, `provider.rs`, `concave.rs`, `cgal_reference_provider.rs`).
- [x] Szimbólum-scan lefutott, munkaartefakt elkészült: `tmp/t07_cache_symbol_scan.txt`.
- [x] NFP call graph dokumentálva (`tmp/phase1_spike_cache_path_discovery.md`).
- [x] Per-kernel audit dokumentálva (OldConcave / cgal_reference / reduced_convolution státusz).
- [x] `shape_id` origin audit dokumentálva (inflated vs nominal, spacing kérdés státusz).
- [x] LRU vs `clear_all` döntési input dokumentálva (`MAX_ENTRIES`, reset-hatás, stat-gap).
- [x] `pipeline_version` szükségesség auditválasz dokumentálva (UNPROVEN + T09 follow-up).
- [x] T08/T09/T10 handoff rögzítve a T07 reportban.
- [x] Production kód nem módosult T07-ben.
- [x] `cargo check -p nesting_engine` futtatva.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md` futtatva.
