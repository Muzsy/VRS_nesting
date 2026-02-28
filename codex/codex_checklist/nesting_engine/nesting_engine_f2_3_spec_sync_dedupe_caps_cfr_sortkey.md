# Codex Checklist — nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey

**Task slug:** `nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey`  
**Canvas:** `canvases/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.yaml`

---

## DoD

- [x] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 10.3 frissitve: totalis komponens-sorrend `ring_hash` tie-breakkel.
- [x] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 12.3 frissitve: dedupe kulcs `(tx,ty,rotation_idx)` + determinisztikus set policy.
- [x] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 12.4 frissitve: `MAX_CANDIDATES_PER_PART = 4096` (part-szint, rotaciok egyutt) + cap alkalmazas sorrendje.
- [x] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md`.
