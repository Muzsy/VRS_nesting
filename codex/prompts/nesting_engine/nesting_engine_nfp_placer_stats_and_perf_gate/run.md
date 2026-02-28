# codex/prompts/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md
- codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_nfp_placer_stats_and_perf_gate.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.

Kötelező szabály:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

A végén:
- Futtasd: ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md
- A report AUTO_VERIFY blokkot ne szerkeszd kézzel.