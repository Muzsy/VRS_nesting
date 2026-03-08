# Codex Checklist — remnant_value_model

**Task slug:** `remnant_value_model`  
**Canvas:** `canvases/nesting_engine/remnant_value_model.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_remnant_value_model.yaml`

---

## DoD

- [x] `MultiSheetResult` kiterjesztve remnant objective mezőkkel.
- [x] Remnant score integer-only, determinisztikus, ppm skálán számol.
- [x] SA objective kiterjesztve: equal unplaced + equal sheets_used esetén remnant value dönt.
- [x] `objective` JSON blokk tartalmazza a remnant mezőket.
- [x] Targeted `remnant_` Rust tesztek PASS.
- [x] `scripts/check.sh` futtat targeted `remnant_` teszteket is.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/remnant_value_model.md` lefuttatva.
