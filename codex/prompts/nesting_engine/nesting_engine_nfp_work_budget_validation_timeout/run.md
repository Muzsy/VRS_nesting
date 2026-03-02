# codex/prompts/nesting_engine/nesting_engine_nfp_work_budget_validation_timeout/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_nfp_work_budget_validation_timeout.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_nfp_work_budget_validation_timeout.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_work_budget_validation_timeout.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.