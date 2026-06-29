# SGH-Q70 - Corner-first residual-space recovery

## Goal

A Q69 forced-latest audit utan a kovetkezo feladat az, hogy a production latest-path ne csak
diagnosztikailag legyen aktiv, hanem a kritikus nagy alkatreszek Anchor/role-aware elhelyezese
tenylegesen a tabla szeleihez, lehetoseg szerint sarkaihoz igazodjon, es a megmarado egybefuggo
szabad ter valos authority legyen a dontesben.

## Context

- A Q69 runban a solver mar nem esett vissza native seed fallbackra vagy random bootstrapra.
- A renderelt tablakepeken viszont a nagy kritikus alkatreszek kozul tobb kozepre ul, vagy tul
  hamar elengedett sheet miatt nagy, kihasznalatlan egybefuggo ter marad mogottuk.
- Az anchor catalog free-space score jelenleg ranking proxy, de a vegso solve viselkedese alapjan
  nem eleg eros authority a center-seat es a generic bbox/corner jeloltek ellen.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/report_standard.md`
- `tmp/audit/audit_2026_06_23.md`
- `canvases/egyedi_solver/sgh_q69_full276_lv8_forced_latest_result_audit.md`

## Scope

- Erositsd meg az Anchor authorityt ugy, hogy latest-path alatt a critical nagy alkatreszeknel a
  corner-first / edge-first dontes tenylegesen nyomja el a center-seat elhelyezest, ha ezzel jobb
  egybefuggo szabad ter marad.
- A residual-space szempont ne csak catalog ranking proxy legyen, hanem a production admission
  dontesben is lathatoan eros preferencia.
- A forced-latest completion pass ne hagyjon ott nagy, nyilvanvaloan toltheto ures regiokat
  azert, mert a builder tul hamar tovabblepett vagy nem inditott eleg eros kitolto kort.
- A benchmark/report legyen eredmeny-kozpontu: render, diagnostics es sheetenkenti
  kihasznaltsag alapjan mondjon iteletet.

## Non-goals

- Nem cel megigeri a 276/276 vagy a 2 tablaba teljes pakolast, ha a solver allapota ezt meg nem
  tamasztja ala.
- Nem teljes solver-ujratervezes.
- Nem a Q62/Q63/Q69 artifactok atirasa.

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs`
  - erositsd a corner-first / residual-space scoringot;
  - dokumentald es diagnosztikazd, ha center seat csak kenyszerhelyzetben nyerhet.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - a production Anchor / critical admission dontesben erositsd meg a residual-space authorityt;
  - latest-path completion es filler pass ne hagyjon ott trivialis, nagy ures savokat;
  - legyen diagnosztika arrol, ha center-seat override vagy completion recovery tortent.
- `rust/vrs_solver/src/io.rs`
  - vedd fel a Q70 production diagnosztikakat.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs`
  - celzott teszt a corner-first / no-center-regression viselkedesre forced-latest alatt.
- `scripts/bench_sgh_q70_corner_first_residual_space_recovery.py`
  - Full276 benchmark runner Q70 artifactcsomaggal.

## Acceptance

- Forced-latest alatt a production diagnostics jelzik, ha center-seat nyert vagy tiltva lett.
- A nagy kritikus anchor dontesnel a residual-space / corner-first authority lathatoan erosodik.
- A Q70 renderelt tablakepeken az elso sheet nem marad kirivoan alultoltott ugyanazon Full276
  csomaggal, vagy a report ezt konkretan FAIL-kent rogzi.
- A benchmark report sheetenkent kihasznaltsagot, center/corner authority summaryt es vizualis
  kovetkeztetest tartalmaz.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md`
  PASS.
