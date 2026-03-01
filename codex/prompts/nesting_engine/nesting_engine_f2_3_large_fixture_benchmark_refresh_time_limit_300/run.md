# codex/prompts/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.