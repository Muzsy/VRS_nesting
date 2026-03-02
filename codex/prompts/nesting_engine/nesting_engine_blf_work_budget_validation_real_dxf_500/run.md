# codex/prompts/nesting_engine/nesting_engine_blf_work_budget_validation_real_dxf_500/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_blf_work_budget_validation_real_dxf_500.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_blf_work_budget_validation_real_dxf_500.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_blf_work_budget_validation_real_dxf_500.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.