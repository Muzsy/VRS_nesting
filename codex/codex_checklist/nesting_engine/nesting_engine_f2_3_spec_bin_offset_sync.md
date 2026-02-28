# Codex Checklist — nesting_engine_f2_3_spec_bin_offset_sync

**Task slug:** `nesting_engine_f2_3_spec_bin_offset_sync`  
**Canvas:** `canvases/nesting_engine/nesting_engine_f2_3_spec_bin_offset_sync.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_spec_bin_offset_sync.yaml`

---

## DoD

- [ ] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 3.2/5/6 fejezetei a bin_offset modell szerint frissítve.
- [ ] A specben a `spacing_effective` legacy szabály explicit (`spacing_mm` hiányában `kerf_mm` a spacing input).
- [ ] A spec támogatja a `margin < spacing/2` esetet (bin inflate).
- [ ] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_spec_bin_offset_sync.md`.
