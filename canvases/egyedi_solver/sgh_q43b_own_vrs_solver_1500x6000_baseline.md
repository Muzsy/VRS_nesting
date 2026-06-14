# SGH-Q43b — Own vrs_solver 1x1500x6000 full276 LV8 continuous baseline + parity audit

## Cel

A sajat `vrs_solver` (natív Rust Sparrow CDE port) futtatasa a Q42 full276 LV8 csomagon, **1 db 1500×6000 mm** single finite stock containerrel. Ez a Q43 upstream SPP 1500×6000 futas **parja a sajat oldalrol**: ugyanaz a 12 part type / 276 instance geometria, ugyanaz a container, de a sajat finite-stock + Q40/Q41 margin/spacing policy alkalmazásával.

A sajat solver source szigorúan nem modosúl. A Q43b kiegeszíto audit + benchmark, nem implementacio.

## Nem-cel

- Saát solverlogika javítása.
- Saát vrs_solver binary modositasa.
- Q42 output utólagos kozmetikazasa.
- Compression / cavity prepack / legacy fallback bekötése.
- Run B futtatasa (a user kérésére csak egy Run A 1200 sec).

## Engedélyezett

- A meglevo `vrs_solver` release binary futtatasa.
- Benchmark runner keszítése.
- Q42 inputbol származo input JSON epitese a Q43b container modellel.
- Audit doksi + report + artifact keszítése.
- 3-way comparison (Q43 upstream + Q43b own + Q42 own).
- Semantic parity audit (9 téma, Q43 audit alapjan).

## Érintett fájlok (kötelezően valós, kereséssel igazolt)

### Saját solver (audit célú, NEM modosítva)
- `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs` (Q32 finite-stock manager)
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs` (LBF)
- `rust/vrs_solver/src/optimizer/sparrow/sample/` (search, best_samples, coord_descent)
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs` (CDE tracker)
- `rust/vrs_solver/src/optimizer/sparrow/geometry/` (Q40/Q41 spacing)
- `rust/vrs_solver/src/technology/clearance.rs` (Q33 technology policy)
- `rust/vrs_solver/src/rotation_policy.rs` (continuous rotation)
- `rust/vrs_solver/target/release/vrs_solver` (binary, 2,226,184 byte, 2026-06-14 09:27 mtime)

### Q42 baseline (referencia, csak olvasás)
- `artifacts/benchmarks/sgh_q42/inputs/q42_full276_3x1500x3000_margin5_spacing8_continuous_1200.json`
- `artifacts/benchmarks/sgh_q42/q42_summary.json`

### Q43 baseline (referencia, csak olvasás)
- `artifacts/benchmarks/sgh_q43/upstream_summary.json`

### Új artifactok (Q43b)
- `scripts/bench_sgh_q43b_own_full276_1500x6000.py` (runner)
- `scripts/smoke_sgh_q43b_own_solver_audit.py` (smoke)
- `scripts/build_sgh_q43b_comparison_artifacts.py` (3-way comparison + parity matrix)
- `artifacts/benchmarks/sgh_q43b/` (minden output)
- `canvases/egyedi_solver/sgh_q43b_…md` (canvas)
- `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q43b_…yaml` (goal YAML)
- `codex/codex_checklist/egyedi_solver/sgh_q43b_…md` (checklist)
- `codex/reports/egyedi_solver/sgh_q43b_…md` (report)

## Feladatlista

- [x] Pre-immutability snapshot (git status + diff).
- [x] `vrs_solver` binary clone info + build log (saját repo, nem upstream).
- [x] Q43b input JSON építése (Q42 inputból, 1 db 1500×6000 stockkal).
- [x] Runner + smoke + comparison script.
- [x] Own solver Run A 1200 sec (1 db 1500×6000 stockon).
- [x] 3-way comparison (Q43 + Q43b + Q42).
- [x] Semantic parity audit (9 téma, Q43 audit alapján).
- [x] Smoke validator.
- [x] Report + canvas + goal YAML + checklist.
- [x] Post-immutability snapshot.

## DoD

1. A Q43b artifact struktúra megegyezik a Q43-mal: `upstream_clone_info.json`, `upstream_build.log`, `upstream_run_1200.log`, `upstream_summary.json`, `comparison_summary.json`, `semantic_parity_matrix.json`, `q43b_summary.json`, pre/post status + diff.
2. A `vrs_solver` binary azonosítva (path, size, mtime, build recipe).
3. A Q43b input Q42 inputból származik, 1 db 1500×6000 stockkal.
4. A Q43b Run A 1200 sec lefutott, 218/276 placement (partial).
5. A 3-way comparison ki van írva `comparison_summary.json`-ba, `direct_comparability: PARTIAL_DIRECTLY_COMPARABLE`.
6. A 9 audit téma mindegyike kapott verdictet (ugyanaz a séma, mint a Q43-ban).
7. A parity matrix a `semantic_parity_matrix.json`-ban van.
8. A saját solver source nem változott (pre + post diff 0 bájt).
9. A `scripts/smoke_sgh_q43b_own_solver_audit.py` PASS.
10. A report a Q43-mal azonos szerkezetű, +1 „Q43b-specifikus" szekció a 3-way összehasonlítással.

## Kockázatok és rollback

- **A Q43b 218/276 partial eredménye** a Q40/Q41 margin/spacing policy-ból fakad. Ez nem hiba, hanem szándékos policy-hatás. Ha „raw" baseline kellene, a Q43b input `margin_mm=0, spacing_mm=0` értékekkel újrafuttatható.
- **A saját solver source diff bármilyen nem-üres értéke esetén** a Q43b automatikusan FAIL. A Q43b runner + smoke + comparison script nem nyúl rust/api/worker/frontend/vrs_nesting forrásfájlokhoz.

Rollback: a Q43b-re létrehozott `scripts/bench_sgh_q43b_*.py`, `scripts/smoke_sgh_q43b_*.py`, `scripts/build_sgh_q43b_*.py`, `artifacts/benchmarks/sgh_q43b/`, `canvases/egyedi_solver/sgh_q43b_*.md`, `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q43b_*.yaml`, `codex/codex_checklist/egyedi_solver/sgh_q43b_*.md`, `codex/reports/egyedi_solver/sgh_q43b_*.md` törlésével a repo Q43b előtti állapota áll vissza.

## Teszt terv

- `python3 scripts/smoke_sgh_q43b_own_solver_audit.py` → PASS
- `git diff -- rust/vrs_solver/src api worker frontend vrs_nesting` → 0 bájt (pre és post)
- `python3 scripts/build_sgh_q43b_comparison_artifacts.py` → comparison_summary + parity_matrix kiírva
- Own solver Run A futás a `scripts/bench_sgh_q43b_own_full276_1500x6000.py` által
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q43b_own_vrs_solver_1500x6000_baseline.md` → nem kötelező (a Q43b spec single-run, nincs verify gate a Q43 mintájára)

## Elfogadási kritérium

A Q43b akkor tekinthető késznek, ha:

- A saját vrs_solver binary azonosítva és a build dokumentálva.
- A Q43b input Q42 inputból származik, 1 db 1500×6000 stockkal.
- A Q43b Run A 1200 sec lefutott, partial placement.
- 3-way comparison (Q43 + Q43b + Q42) ki van írva.
- 9 audit téma feldolgozva, parity matrix kiírva.
- Saját solver source nem módosult.
- Smoke PASS.
- Report + canvas + goal YAML + checklist megvan.
