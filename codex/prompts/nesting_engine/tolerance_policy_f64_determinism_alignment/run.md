Szerep: repo-szabalykovo Codex implementator.

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/tolerance_policy_f64_determinism_alignment.md
- codex/goals/canvases/nesting_engine/fill_canvas_tolerance_policy_f64_determinism_alignment.yaml

Feladat:
- Hajtsd vegre a YAML stepjeit sorrendben.
- Csak a step `outputs` listajaban szereplo fajlokat hozd letre / modositsd.
- Minimal-invaziv modon dolgozz, a meglevo contractokat ne bontsd meg.

Kritikus megkotesek:
- Ez a kor policy-alignment stabilizacio, nem teljes geometriai integer-only ujrairas.
- A touching policy explicit maradjon: touching = infeasible.
- A determinism hash contractot ne modositsd.
- A PR gate a meglevo scripts/check.sh -> repo-gate.yml utvonalon maradjon.

A vegen kotelezo:
- ./scripts/verify.sh --report codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md
- Az AUTO_VERIFY blokkot ne szerkeszd kezzel.
