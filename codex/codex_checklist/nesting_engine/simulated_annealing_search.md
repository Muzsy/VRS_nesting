# Codex Checklist — simulated_annealing_search

**Task slug:** `simulated_annealing_search`  
**Canvas:** `canvases/nesting_engine/simulated_annealing_search_move_neighborhood_and_dod_closure.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search_move_neighborhood_and_dod_closure.yaml`

---

## DoD

- [x] `apply_move` implementalva es bekotve `apply_neighbor`-be.
- [x] Uj `sa_` unit teszt: `sa_move_neighbor_preserves_permutation` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml sa_` PASS.
- [x] F2-4 fo report + checklist elkeszult (Report Standard v2 + AUTO_VERIFY + `.verify.log`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md` PASS.
