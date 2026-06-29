# SGH-Q71 - Anchor edge-lock and flush alignment

## Goal

A Q70 utan a kovetkezo feladat az, hogy a forced-latest production path ne csak corner-first
policyt jelezzen diagnosztikaban, hanem a nagy critical Anchor alkatreszek TENYLEGESEN maradjanak
a tabla szeleihez, lehetoseg szerint sarkaihoz zarva a vegso layoutban is. A solver nem sodorhatja
el oket egy gyenge separator vagy generic direct fallback miatt a tabla kozepe fele.

## Problem statement

- A Q70 futas mar nem nezett ki teljes regresszionak, de a vizualis ellenorzes alapjan a lenyeg
  nem javult elegge: a nagy anchor elemek kozul tobb nincs eleg eroteljesen a tabla szeleihez
  forgatva / igazítva.
- A seedelt edge/corner jelolt onmagaban nem eleg, ha a separation vagy a kesobbi fallback
  elsodorja a vegso elhelyezest a hasznos tabla-szelrol.
- A residual-space kezeles csak akkor hiteles, ha a nagy darab tenyleg flush marad az egyik vagy
  ket szelen, kulonben a marado egybefuggo ter szetesik.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/report_standard.md`
- `artifacts/benchmarks/sgh_q69/q69_report.md`
- `artifacts/benchmarks/sgh_q70/q70_report.md`

## Scope

- A production anchor admission legyen edge-lock aware: ne elegedjen meg azzal, hogy a seed jo volt,
  hanem a vegso placementet is ertekelje edge/corner drift szempontjabol.
- Forced-latest alatt az Anchor role generic direct fallbackja ne tudjon csendben visszacsuszni
  gyenge, nem edge-aligned elhelyezesre.
- A benchmark/report ne csak darabszamot nezzen, hanem kulon jelentse:
  - a legnagyobb anchor elemek edge gapjeit,
  - hogy maradt-e flush edge alignment,
  - hogy a renderen lathato-e valos javulas.

## Non-goals

- Nem cel a teljes solver ujratervezese.
- Nem cel a Q70 artifactok visszairasa.
- Nem cel kozmetikazni a reportot valodi solver-javitas nelkul.

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - anchor edge-lock / drift-aware scoring es forced-latest fallback-szigoritas.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs`
  - edge/corner jeloltek metadataja es rankingje tamogassa a vegso flush alignment ellenorzeset.
- `rust/vrs_solver/src/io.rs`
  - uj diagnostika az anchor vegso edge gap / drift megfigyelesere.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs`
  - regresszios teszt arra, hogy forced-latest anchor placement tenyleg a tabla szelen marad.
- `scripts/bench_sgh_q71_anchor_edge_lock_and_flush_alignment.py`
  - Full276 benchmark runner, mely a legnagyobb anchor elemek edge-gap summaryjat is reportolja.

## Acceptance

- Forced-latest alatt a nagy anchor placementeknel a report explicit edge-gap / drift summaryt ad.
- A generic direct fallback nem ronthatja le csendben az Anchor role edge-first viselkedeset.
- A Q71 renderen a nagy anchor darabok legalabb egy tabla-szelhez lathatoan flush kozelben maradnak,
  kulonben a report FAIL/partial-with-finding formatumban ezt oszinten kimondja.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md`
  PASS.
