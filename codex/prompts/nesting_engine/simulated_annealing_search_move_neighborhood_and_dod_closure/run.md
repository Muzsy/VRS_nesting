# codex/prompts/nesting_engine/simulated_annealing_search_move_neighborhood_and_dod_closure/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/simulated_annealing_search_move_neighborhood_and_dod_closure.md
- codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search_move_neighborhood_and_dod_closure.yaml

Feladat:
- Hajtsd végre a YAML stepjeit sorrendben.
- Csak a step `outputs` listájában szereplő fájlokat hozd létre / módosítsd.

A végén kötelező:
- ./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.