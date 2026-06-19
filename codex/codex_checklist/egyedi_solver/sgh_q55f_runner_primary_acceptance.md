# Q55F Codex Checklist

Task: `sgh_q55f_runner_primary_acceptance`
Canvas: `canvases/egyedi_solver/sgh_q55f_runner_primary_acceptance.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55f_runner_primary_acceptance.yaml`
Report: `codex/reports/egyedi_solver/sgh_q55f_runner_primary_acceptance.md`

## DoD

- [ ] Repo szabályfájlok + Q55A-E + Q54E misleading-PASS tanulság rögzítve a reportban.
- [ ] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [ ] CDE final validation semantics nem gyengült; a proof csak CDE-valid layouton.
- [ ] Nincs NFP, nincs bbox-corner shortcut primary, nincs cavity/hole fősolver logika.
- [ ] Continuous rotation guardrail nem sérült.
- [ ] Nincs part-id hack a solverben, nincs hardcoded 3+3.
- [ ] Benchmark + artifactok elkészültek (`artifacts/benchmarks/sgh_q55/`).
- [ ] Report őszinte verdiktet ad; a diagnosztika role-onként bizonyítja a skeleton működését.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55f_runner_primary_acceptance.md` lefutott.
- [ ] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates (PRIMARY — kötelező)

- [ ] 6× `Lv8_11612`, spacing 5, skeleton ON: status ok, final_pairs 0, boundary 0.
- [ ] `max_big_per_sheet >= 3` ÉS egy sheeten Anchor + Interlock + BandInsert.
- [ ] `band_insert_candidates_accepted >= 1`.
- [ ] Ha bármelyik primary nem teljesül → `verdict = FAIL` (a secondary nem írhatja felül).

## Secondary (no-regression; nem írja felül a primary-t)

- [ ] spacing 0 no-regression (2 tábla / 3+3).
- [ ] full276 no-regression (placed 276, ON ≤ OFF, valid).
- [ ] gate off → byte-azonos.
- [ ] `python3 scripts/bench_sgh_q55_role_skeleton.py --proof-time 120 --full-time 300`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55f_runner_primary_acceptance.md`
