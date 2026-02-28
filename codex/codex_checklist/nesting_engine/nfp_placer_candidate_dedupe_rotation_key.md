# Codex Checklist — nfp_placer_candidate_dedupe_rotation_key

**Task slug:** `nfp_placer_candidate_dedupe_rotation_key`  
**Canvas:** `canvases/nesting_engine/nfp_placer_candidate_dedupe_rotation_key.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_placer_candidate_dedupe_rotation_key.yaml`

---

## DoD

- [x] `nfp_placer.rs` dedupe kulcs rotáció-érzékeny: `(tx, ty, rotation)`.
- [x] Új unit teszt lefedi a `same (tx,ty), different rotation` regressziós esetet és PASS.
- [x] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_placer_candidate_dedupe_rotation_key.md`.
