# codex/prompts/nesting_engine/arc_spline_polygonization_policy/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/arc_spline_polygonization_policy.md
- codex/goals/canvases/nesting_engine/fill_canvas_arc_spline_polygonization_policy.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.
- Csak a step `outputs` listájában szereplő fájlokat hozd létre / módosítsd.
- Ne találj ki új fixture-hierarchiát: az F3-1 valós DXF fixture-ei a canvas szerint a `samples/dxf_demo/` alatt élnek.
- A curve flatten tolerance és a chain endpoint epsilon fogalmát ne mosd össze, még ha numerikusan azonosak is.

A végén kötelező:
- ./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.
