# SGH-Q73 - Big-part pitch-minimizing interlock row-seed

## Goal

A nagy ismetlodo kritikus tipusnal a forced/strict latest-path ne a min-bbox-szelesseg szerinti 90
fokon, egy-darab-per-tabla modon helyezze el a darabokat, hanem egy CDE-vel meghatarozott
**legkisebb lepeskozu (pitch) orientacion** (nem-ortogonalis is megengedett), **tablankent annyit,
amennyi tenylegesen befer**, ugy hogy egy tablat feltolt, mielott uj tablat nyitna. Ezutan a Q72
no-drop kiegeszites + a valodi exploration SA tolti ki a maradekot (a kis darabokat a konkav
oblokbe).

## Context (adatvezerelt diagnozis)

A Q72 (262/276) utan a render+output szerint a domináns nagy tipus (`Lv8_11612_6db`, bbox
2522x733, area 597k, 32% kitoltes, 6 db) eloszlasa rossz:
- sheet 0: 1 db @ 90, sheet 1: 2 db @ 89.9/269.9, **3 db elhelyezetlen**;
- minden nagy darab gyakorlatilag **90/270 fokon** (a 199 nem-ortogonalis forgatas a kis daraboke);
- a sheet 0-ra 90 fokon is **2 db elferne**, megis csak 1 van -> tiszta eloszlasi veszteseg.

Python+shapely prototipus (valos geometria): a darab egysoros / 2D bottom-left pakolasa
**maximum 2 db/tabla** ennel az alaknal, de a nem-ortogonalis ~81 fok a lepeskozt 738 -> ~521 mm-re
csokkenti (szorosabb pakolas, tobb hely a fillereknek). A **3 db/tabla** ennel a 2522 mm hosszu
alaknal azonos darabok racsos/BL nestingjevel **geometriailag nem all ossze** -> ezt oszinten
rogzitjuk, nem igerjuk.

## Source of truth

- `AGENTS.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `artifacts/benchmarks/sgh_q72/q72_summary.json`
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` (`sheet_local_feasible`, latest-lock seed)
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` (`prepare_shape_native`, CDE truth)
- `samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf`

## Scope

- Forced/strict latest modban a dominans ismetlodo nagy tipust egy **pitch-minimalizalo
  orientacio-sweep** + CDE-validalt sor-seed helyezze el: tablankent a max befero darabszam, egy
  tablat feltoltve mielott uj tablat nyitna.
- Az orientacio-sweep folyamatos (nem-ortogonalis is) -> ahol a konkav darabok szorosabban
  pakolhatok, ott nem-ortogonalis szog nyer.
- A geometria a tenyleges transzformalt polygon-bboxbol szamitodik (`prepare_shape_native`), nem a
  sarok-origo feltetelezesbol (a local polygon a spacing-expandalt kontur, nem (0,0)-bol indul).
- A seedelt sort a Q72 no-drop kiegeszites + a valodi exploration SA egesziti ki; a nagy darabok
  jo pozicioja megmarad, a maradek a fillerekkel tolt.
- Eredmeny-kozpontu benchmark: teljeskoru run-rogzites (input/output/log/render/summary/report) a
  `artifacts/benchmarks/sgh_q73/` ala, nagy-darab/tabla eloszlassal, forgatassal es **kotelezo
  vizualis audittal**.

## Non-goals

- Nem cel a 6/6 nagy darab (3/tabla) garantalt elerese: ez ennel az alaknal geometriailag nem all
  ossze, es ezt oszinten FAIL/PARTIAL-kent rogzitjuk, nem igerjuk.
- Nem cel uj proxy heurisztika a mohou builderben.
- Nem cel spacing/margin csokkentes, infeasibility-kijelentes, folyamatos forgatas kikapcsolasa,
  part-id/koordinata hardcode.
- Nem cel a Q70/Q71/Q72 artifactok atirasa.

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `repeated_big_critical_row_seed`: dominans nagy tipus kivalasztasa, orientacio-sweep +
    CDE-validalt min-pitch sor, tablankenti eloszlas (fill-before-open);
  - latest-lock seed: a nagy tipus placementjeinek lecserelese a sor-seedre, majd Q72 no-drop
    kiegeszites.
- `rust/vrs_solver/src/io.rs`
  - Q73 diagnosztikak: `bpp_q73_big_row_seed_used`, `_part_id`, `_rotation_deg`, `_pitch_mm`,
    `_copies_per_sheet`, `_seeded_count`.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs`
  - regresszios teszt: forced-latest alatt a nagy ismetlodo tipus 2/tabla sor-seedet kap.
- `scripts/bench_sgh_q73_big_part_interlock_rowseed.py`
  - Full276 benchmark Q73 artifactcsomaggal, nagy-darab/tabla eloszlas + forgatas elemzes.

## Acceptance / Definition of Done

1. **Sor-seed aktiv:** forced-latest alatt a dominans nagy tipus sor-seedet kap (diag + teszt).
2. **2/tabla eloszlas:** a dominans nagy tipus minden hasznalt tablan >= 2 db (sheet 0 nem marad
   1-darabos).
3. **Nem-ortogonalis orientacio:** a sor-seed orientacioja nem 0/90/180/270, ahol az szorosabb.
4. **Nincs darabszam-regresszio:** a teljes placed_count >= 262 (Q72), ervenyes (final_pairs=0,
   boundary_violations=0).
5. **Teljeskoru run-rogzites + vizualis audit:** minden kimeneti fajl a `artifacts/benchmarks/sgh_q73/`
   alatt; a renderelt tablak manualis ertekelese eredmeny-kozpontuan rogzitve.
6. **Oszinte 3/tabla limit:** ha 6/6 nem all ossze, a report ezt geometriai limitkent rogzi (nem
   spacing/margin csokkentessel kerul meguszasra).
7. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md`
   PASS, DoD -> Evidence Matrix path+line bizonyitekkal.

## Constraints (nem alkuképes)

- Spacing/margin nem csokkentheto; infeasibility nem allithato (PDF referencia).
- CDE a vegso utkozes/hatar igazsag.
- Folyamatos forgatas megmarad; nincs part-id/koordinata hardcode; nincs csendes regi-logika fallback.
- Cargo toolchain nincs default PATH-on: export RUSTUP_HOME/CARGO_HOME + stable toolchain bin.
