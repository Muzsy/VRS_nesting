# codex/prompts/nesting_engine/nesting_engine_timeout_bound_determinism_policy/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_timeout_bound_determinism_policy.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_timeout_bound_determinism_policy.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_timeout_bound_determinism_policy.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.