# Codex Checklist — cfr_sort_key_precompute_and_hash_cache

**Task slug:** `cfr_sort_key_precompute_and_hash_cache`  
**Canvas:** `canvases/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cfr_sort_key_precompute_and_hash_cache.yaml`

---

## DoD

- [x] `cfr.rs` komponens-sort kulcs előszámítva (nincs sha256 a comparatorban).
- [x] `ring_hash_u64` hívás komponensenként egyszer / precompute mintára korlátozva (test guardrail igazolja).
- [x] A meglévő CFR unit tesztek továbbra is PASS (startpoint/orientáció/permutáció-stabil).
- [x] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md`.
