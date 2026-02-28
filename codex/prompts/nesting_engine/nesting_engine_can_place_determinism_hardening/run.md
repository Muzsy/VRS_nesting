# codex/prompts/nesting_engine/nesting_engine_can_place_determinism_hardening/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_can_place_determinism_hardening.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_can_place_determinism_hardening.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_can_place_determinism_hardening.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.