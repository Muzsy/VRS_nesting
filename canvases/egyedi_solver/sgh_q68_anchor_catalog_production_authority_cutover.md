# SGH-Q68 - Anchor catalog production authority cutover

## Goal

A Q56C SheetEdgePlacementCatalog production Anchor agban ne csak fallback legyen, hanem tenyleges
score-versenyzo a skeleton feature candidate-ek mellett. A production `try_admit_critical()`
Anchor role-ban a catalog es a feature winner ugyanazon free-space score alapjan versenyezzen, es a
jobb jelolt nyerjen.

## Context

Az audit szerint a jelenlegi production commit policy tul gyenge: a code path a catalogot csak akkor
engedi nyerni, ha nincs skeleton feature-gyoztes (`best_skeleton.is_none()`). Ez ellentmond a Q56C
celjanak, ahol a catalog first-class Anchor candidate forras.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/report_standard.md`
- `tmp/audit/audit_2026_06_23.md`
- `canvases/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md`

## Scope

- A production Anchor role-ban a catalog mar ne fallback-only legyen.
- Ugyanazzal a `sheet_freespace_score(...)` metrikaval hasonlitsuk a legjobb skeleton feature
  winnerhez.
- A vegso Anchor authority dontesrol explicit diagnostika keszuljon.
- Keszitsunk valos solve-boundary artifactot, ami megmutatja a competition allapotot.

## Non-goals

- Nem teljes LV8 layout-quality helyreallitas.
- Nem az Anchor generator geometriai ujratervezese.
- Nem Interlock/BandInsert ujradrótozas.

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - vezess be explicit Anchor authority winner dontest;
  - a catalog es a skeleton feature winner kozos score-versenyben induljon;
  - a production builder rogzitese, hogy melyik ut nyert.
- `rust/vrs_solver/src/io.rs`
  - keruljenek be a Q68 Anchor competition diagnostikak.
- `rust/vrs_solver/tests/sparrow_q68_anchor_catalog_cutover.rs`
  - solve-boundary teszt gate-off/gate-on artifacttal.
- `artifacts/benchmarks/sgh_q68/anchor_catalog_production_cutover.json`
  - live artifact a competition diagnostikaval.

## Acceptance

- Gate-on Anchor role-ban a catalog consultation utan explicit competition decision szuletik.
- Ha a catalog score-ja legalabb olyan jo, mint a feature winner score-ja, a catalog nyerhet.
- A production diagnostikaban latszik: competition futott-e, milyen score-ok versenyeztek, es melyik
  ut nyert.
- A gate-off run nem allitja be ezeket a Q68 mezoket.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q68_anchor_catalog_production_authority_cutover.md`
  PASS.
