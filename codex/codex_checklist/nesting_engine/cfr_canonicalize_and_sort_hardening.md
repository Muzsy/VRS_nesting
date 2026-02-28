# Codex Checklist — cfr_canonicalize_and_sort_hardening

**Task slug:** `cfr_canonicalize_and_sort_hardening`  
**Canvas:** `canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cfr_canonicalize_and_sort_hardening.yaml`

---

## DoD

- [x] CFR output komponensek minden ringje kanonizált (orientáció + lex-min start + tisztítás).
- [x] 0-area / degenerált komponensek determinisztikusan eldobva.
- [x] Komponens sort totális (`ring_hash` tie-breakkel).
- [x] Új unit tesztek:
  - [x] ring startpoint drift ellen (rotált ring ugyanarra kanonizálódik)
  - [x] orientáció drift ellen (reversed ring ugyanarra kanonizálódik)
  - [x] komponens-sorrend stabil (input `nfp_polys` permutálása esetén CFR output stabil)
- [x] Új F4 fixture létrehozva (noholes, `spacing_mm` explicit).
- [x] `scripts/check.sh` bővítve: F4 3× determinism NFP módban.
- [x] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md`.
