# Run: nfp_based_placement_engine

Olvasd el:
- AGENTS.md
- docs/nesting_engine/f2_3_nfp_placer_spec.md
- canvases/nesting_engine/nfp_based_placement_engine.md
- codex/goals/canvases/nesting_engine/fill_canvas_nfp_based_placement_engine.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- A spec (`docs/nesting_engine/f2_3_nfp_placer_spec.md`) normatív: ha eltérés van, az hibának számít.
- A minőségkaput kizárólag wrapperrel futtasd (ne rögtönözz párhuzamos check parancsokat).

A végén futtasd:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_based_placement_engine.md