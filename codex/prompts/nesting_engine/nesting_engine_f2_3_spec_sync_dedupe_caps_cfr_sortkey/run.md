# Run: nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- A minőségkaput kizárólag wrapperrel futtasd.

A végén futtasd:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md
