Szerep: repo-szabálykövető Codex implementátor.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/full_pipeline_determinism_hardening.md
- codex/goals/canvases/nesting_engine/fill_canvas_full_pipeline_determinism_hardening.yaml

Feladat:
- Hajtsd végre a YAML stepjeit sorrendben.
- Csak a step `outputs` listájában szereplő fájlokat hozd létre / módosítsd.
- Minimal-invazív módon dolgozz, a meglévő contractokat ne bontsd meg.

Kritikus megkötések:
- Ez a kör **repo-native determinism contract hardening**, nem teljes geometriai újraírás.
- A `determinism_hash` contractot ne változtasd meg önkényesen; ha a canonical bytes ténylegesen változna,
  azt dokumentáld és csak indokolt esetben lépd meg.
- `touching = infeasible` maradjon explicit és változatlan policy.
- A PR gate-et a meglévő `scripts/check.sh` -> `repo-gate.yml` útvonalon kell lezárni;
  ne vezess be fölösleges új workflow-kényszert.
- A `platform-determinism-rotation.yml` külön extra réteg; ezt ne bontsd meg és ne helyettesítsd.

A végén kötelező:
- ./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md
- Az AUTO_VERIFY blokkot ne szerkeszd kézzel.
