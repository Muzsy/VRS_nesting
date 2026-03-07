# codex/prompts/nesting_engine/part_in_part_pipeline/run.md

Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/part_in_part_pipeline.md
- codex/goals/canvases/nesting_engine/fill_canvas_part_in_part_pipeline.yaml

Feladat:
- Hajtsd végre a YAML `steps` lépéseit sorrendben.
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.

Kötelező keret:
- A jelenlegi hybrid gating policy-t ne bontsd meg: holes / `hole_collapsed` esetén az NFP út továbbra is BLF fallback maradhat.
- Az F3-2 ebben a körben BLF cavity-aware candidate generation legyen, nem teljes hole-aware NFP/CFR.
- `--part-in-part off` mellett a baseline működésnek változatlannak kell maradnia.
- `hole_collapsed` / outer-only source nem lehet cavity-forrás.
- Az IO contractot ne bővítsd.

A végén kötelező:
- ./scripts/verify.sh --report codex/reports/nesting_engine/part_in_part_pipeline.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.
