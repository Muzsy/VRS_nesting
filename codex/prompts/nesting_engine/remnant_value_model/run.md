Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/remnant_value_model.md
- codex/goals/canvases/nesting_engine/fill_canvas_remnant_value_model.yaml

Feladat:
- Hajtsd végre a YAML stepjeit sorrendben.
- Csak a step `outputs` listájában szereplő fájlokat hozd létre / módosítsd.
- Minimal-invazív módon dolgozz, a meglévő contractokat ne bontsd meg.

Kritikus megkötések:
- Az F3-3 ebben a körben **proxy remnant model**, nem exact remnant polygon extraction.
- A primary objective sorrend nem változhat meg: feasibility/unplaced -> sheets_used -> remnant_value.
- A remnant score integer-only, determinisztikus, ppm skálán számoljon.
- A determinism hash contractot ne módosítsd.

A végén kötelező:
- ./scripts/verify.sh --report codex/reports/nesting_engine/remnant_value_model.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.
