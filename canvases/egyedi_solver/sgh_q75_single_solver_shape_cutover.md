# SGH-Q75 - Single solver-shape cutover cleanup

## Goal

A `tmp/plans/solver_architektura_modositott_leiras.md` szerinti architekturalis takaritas: a solver
belul **egyetlen geometriat** lasson (a spacinggel beegetett, hole-free, csak kulso konturu
solver-proxy), a kettos `base_shape` + `spacing_collision_base_shape` dontesmodell kivezetese, hard
SolverInputGuard a top-level hole-okra, es a furat-alapu jelek dontesbol valo kizarasanak biztositasa.

A NAGY nyereseg mar megvan (SGH-Q40: spacing offset app-oldalon, solver spacing=0; Q39 kontroll:
offset-alak 257 vs dual-geometry 146). Ez a task a maradek **kod-higiéniat** vegzi el, **byte-azonos
production viselkedes** mellett (a kivett dual-geometry spacing=0-nal bizonyitottan no-op volt).

## Context

- Aktiv production modell (SGH-Q40, `adapter.rs`): `build_offset_parts` (spacing/2 beegetes),
  `apply_rectangular_sheet_offset` (margin−spacing/2), `spacing_mm: 0.0` a solvernek.
- A `SPInstance.spacing_collision_base_shape` (Q36 dual-geometry) production-ben mar a `base_shape`
  Rc-klonja volt (spacing=0) -> minden olvasasa azonos eredmenyt adott.

## Source of truth

- `tmp/plans/solver_architektura_modositott_leiras.md`
- `AGENTS.md`, `docs/codex/report_standard.md`
- `rust/vrs_solver/src/adapter.rs` (SGH-Q40 pipeline)
- `rust/vrs_solver/src/optimizer/sparrow/model.rs`, `quantify/tracker.rs`

## Scope (fazisok)

1. **Dual-geometry kivezetese:** `SPInstance.spacing_collision_base_shape` mezo torlese; minden
   collision/boundary olvasas a `base_shape` (egy alak) ellen; a model.rs spacing-shape epitese
   torolve; a tracker `spacing_applied` always-false (a Q36 dual-ut kivezetve). Byte-azonos spacing=0-ra.
2. **SolverInputGuard:** a sparrow multisheet pipeline elejen hard-fail, ha barmely part top-level
   hole-t hoz (`CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN`). Production hole-free -> sosem aktivalodik.
3. **PartAnalysis hole-jelek:** igazolas + dokumentalas, hogy a furat-mezok DIAGNOSZTIKA-ONLY (sehol
   nem dontesi input); a Fazis 2 guard utan strukturalisan mindig hole-free.
4. **Terminologia:** a tracker / OrientationCatalog dual-geometry kommentek/jelolesek tisztitasa.

## Non-goals

- Nem cel a placed_count valtoztatasa (byte-azonos production a cel).
- Nem cel a diagnosztikai mezok / output-sema atirasa (zero-erteku, kockazatos churn) — a doc
  intencioja (furat nem dontesi jel) igazolva + dokumentalva.
- Nem cel a 3/tabla nesting (az kulon task).

## Acceptance / DoD

1. Nincs `spacing_collision_base_shape` a kodban; minden collision/boundary egy alakon (`base_shape`).
2. SolverInputGuard hard-fail top-level hole-ra (`CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN`).
3. Furat-jel sehol nem dontesi input (igazolva + dokumentalva).
4. Build zold; 550+ lib teszt + osszes integracios teszt zold (a dual-geometry tesztek a single-shape
   modellre frissitve).
5. Production byte-azonos: a kivett ut spacing=0-nal no-op (a Full276 wall-time futas wall-time-zajos,
   de nem regresszal; Q72/Q74 600s ~262 / ~274 ujraigazolva).
6. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q75_single_solver_shape_cutover.md` PASS.

## Constraints

- Minimal-invaziv; meglevo (production) mukodest nem rontunk. Cargo toolchain export a build elott.
