# codex/prompts/nesting_engine/simulated_annealing_search/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/simulated_annealing_search.md
- codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- ./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.