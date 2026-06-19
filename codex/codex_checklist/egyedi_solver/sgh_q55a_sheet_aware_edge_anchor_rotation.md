# Q55A Codex Checklist

Task: `sgh_q55a_sheet_aware_edge_anchor_rotation`
Canvas: `canvases/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55a_sheet_aware_edge_anchor_rotation.yaml`
Report: `codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md`

## DoD

- [x] Repo szabályfájlok + Q47–Q54 előzmények (+ Q54E proof) elolvasva, reportban rögzítve.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült.
- [x] Nincs NFP, nincs bbox-corner shortcut primary critical pathként, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült (nincs 90/270/45 snapping; anchor-szög folytonos).
- [x] Nincs part-id hack, nincs hardcoded 3+3.
- [x] Task-specifikus unit tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a sheet-aware rotációt (seed/refined/edge_distance/anchor_side).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] A seed-halmaz tartalmaz long-edge ÉS short-edge igazítást + 180° flip variánst.
- [x] Lv8-szerű parton 1500×3000 sheeten ≥1 CDE-clear sheet-edge anchor candidate.
- [x] A refined rotáció continuous (nem fix 0/90/180/270 snapping, ha az optimum eltér).
- [x] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml edge_anchor`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md`
