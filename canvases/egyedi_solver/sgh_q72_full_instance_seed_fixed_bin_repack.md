# SGH-Q72 - Full-instance seed + fixed-bin global repack

## Goal

A forced/strict latest-path ne dobjon el darabot az igazi optimalizalo elott. A konstruktiv
critical-aware builder jo (el/flush) kritikus/anchor elhelyezeseit meg kell tartani, de a
Sparrow exploration SA + redistribute/reduction pipeline-nak a **teljes 276 instance-szal** kell
dolgoznia a rogzitett 2 tablan, hogy a placed_count tenylegesen a 276 fele emelkedjen, ne maradjon
a baseline alatt.

Az egyetlen elfogadasi mero a **placed_count 2 tablan** (cel 276), masodlagos a util%. Az
edge-lock / corner / residual-gap **csak diagnosztika**, soha nem acceptance gate.

## Context (diagnozis, path+line)

A Q70 (237/276) es a Q71 (215/276) forced-latest run **a baseline ala esett**: a Q62 current
(native seed + teljes pipeline) **259/276**-ot ad. Az ok architekturalis, nem a seed pontozasa:

- Forced/strict latest modban a builder seedje akkor is tovabbmegy, ha hianyos:
  `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:4882` (`if latest_lock { ... built }`).
- A hianyos seed egyetlen `run_subsolve` kort kap: `bpp_reduction.rs:4902`. Ez a
  `run_subsolve` -> `exploration_phase` ut: `bpp_reduction.rs:759`,
  `rust/vrs_solver/src/optimizer/sparrow/explore.rs:14`. Az `exploration_phase` egy
  **overlap-szeparator** (`self.separate(...)` ciklus): csak a layoutban **mar bent levo**
  darabok atfedeset oldja fel, **uj/hianyzo instance-t nem rak be soha**.
- A tabla-csokkento / redistribute fo ciklus **csak teljes konstrukcio eseten fut**:
  `bpp_reduction.rs:4923` (`if construction_full`). Full276-nal a seed nem teljes (215-237/276),
  ezert ez az egesz ki van hagyva; utana mar csak tomorites/gravity fut a **mar elhelyezett**
  darabokon.
- A builder altal eldobott instance-ok unplaced-kent kerulnek kiirasra es **soha nem terenek
  vissza** az optimalizalasba: `bpp_reduction.rs:5147`.

Kovetkezmeny: a Q70/Q71 a rossz retegen dolgozott (anchor/corner/residual proxy a mohou
builderben). A placed_count gyokeroka az, hogy a darabok az optimalizalo elott elvesznek es a
valodi globalis kereso ki van hagyva.

Mindket tabla ~50% telt (Q70: sheet0 55.3%, sheet1 54.8%), megis 39-61 darab kimaradt -> nem
kapacitas-, hanem (a) eldobott-darab + (b) fragmentalt-maradekter problema. A referencia
(`samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf`) bizonyitja, hogy 276
darab 2 tablan elfer.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `tmp/audit/audit_2026_06_23.md`
- `artifacts/benchmarks/sgh_q70/q70_summary.json`
- `artifacts/benchmarks/sgh_q71/q71_summary.json`
- `samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf`

## Scope

- Forced/strict latest modban a builder seed **ne dobjon el instance-t** az optimalizalo elott.
  A builder kritikus/anchor placementjeit meg kell tartani (priority/flush szempont megorzese),
  de a maradek darabokat is el kell helyezni a seedben (native LBF kitoltessel es/vagy kontrollalt
  atfedessel), hogy a layout **mind a 276 instance-t** tartalmazza, mielott a pipeline elindul.
- A teljes (mind az instance-t tartalmazo) seedre fusson a **valodi globalis optimalizalo a
  rogzitett 2 tablan**: az `exploration_phase` overlap-szeparacioja + a redistribute/reduction
  ut, hogy a darabok ne vesszenek el.
- A nagy anchorok el-/sarok-flush igazitasa a meglevo gravity/compaction post-passbol **jojjon ki**
  (`bpp_reduction.rs:4616` gravity_compact_layout, `:5119` hivas), ne torekeny pre-forced
  pozicionalasbol, ami csokkenti a darabszamot (ez tortent Q71-ben).
- Diagnosztika: rogzitsd, hogy a seed hany instance-t tartalmazott a pipeline elott (no-drop
  garancia), hany darabot helyezett vissza/szeparalt a globalis kereso, es hogy a vegso
  placed_count hogyan viszonyul a baseline 259-hez es a 276 celhoz.
- Eredmeny-kozpontu benchmark: teljeskoru run-rogzites (input/output/log/render/summary/report) a
  `artifacts/benchmarks/sgh_q72/` ala, sheetenkenti kihasznaltsaggal es **kotelezo vizualis
  audittal** a renderelt tablakepeken.

## Non-goals

- Nem cel a 276/276 garantalt elerese egyetlen iteracioban; a cel a **gyokeroka** felszamolasa
  (no-drop + globalis repack) es a baseline 259 **tenyleges meghaladasa** mereheto modon.
- Nem cel uj anchor-/corner-/residual-proxy heurisztika a mohou builderben.
- Nem cel a spacing/margin csokkentese vagy barmilyen geometriai infeasibility-kijelentes.
- Nem cel a folyamatos forgatas kikapcsolasa (0/90/180/270 kenyszer tilos).
- Nem cel part-id / koordinata hardcode.
- Nem cel a Q62/Q63/Q69/Q70/Q71 artifactok atirasa.

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - latest-path seed: a builder critical/anchor placementjei + a maradek instance-ok teljes
    kitoltese (no-drop) a pipeline elott;
  - a teljes seed fusson at a globalis optimalizalon (exploration SA + redistribute) a rogzitett
    2 tablan; ne legyen olyan ut, ahol a hianyzo darabok kihagyjak a kereso(ke)t;
  - el-/sarok-flush a compaction post-passbol, nem pre-forced pozicionalasbol.
- `rust/vrs_solver/src/io.rs`
  - Q72 production diagnosztikak: seed_instance_count_before_pipeline, no_drop_seed_used,
    global_repack_reinserted_count, placed_count vs baseline/target.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs`
  - celzott teszt: forced-latest alatt a seed **minden instance-t** tartalmaz a pipeline elott
    (no-drop), es a placed_count nem esik a native+full-pipeline baseline ala.
- `scripts/bench_sgh_q72_full_instance_seed_fixed_bin_repack.py`
  - Full276 (2x1500x3000, margin5, spacing5, continuous) benchmark runner Q72 artifactcsomaggal,
    Q62/Q70/Q71 osszehasonlitassal, sheetenkenti kihasznaltsaggal, render + manualis vizualis
    audit blokkal.

## Acceptance / Definition of Done

1. **No-drop seed bizonyitva:** forced/strict latest modban a layout a pipeline elott mind a 276
   instance-t tartalmazza (diagnosztika + teszt), nem dob el darabot az optimalizalo elott.
2. **Globalis repack a rogzitett 2 tablan:** a teljes seed atmegy a valodi exploration SA +
   redistribute uton; diagnosztika mutatja a visszahelyezett/szeparalt darabok szamat.
3. **Placed_count meghaladja a baseline-t:** a Q72 forced-latest run placed_count-ja **> 259**
   (a Q62 current baseline), a 276 fele tartva; ha nem, a report ezt **FAIL**-kent rogziti
   (nincs proxy-alapu PASS).
4. **El-/sarok-flush a compactionbol:** a nagy anchorok el-igazitasa a post-pass eredmenye, nem
   pre-forced; ezt a render es a diagnosztika tamasztja ala, throughput-veszteseg nelkul.
5. **Teljeskoru run-rogzites:** `artifacts/benchmarks/sgh_q72/` ala minden kimeneti fajl megvan
   (inputs/outputs/logs/renders + q72_summary.json + q72_report.md); a render SVG+PNG generalva.
6. **Vizualis audit rogzitve:** a renderelt tablakepek (sheet_00, sheet_01) manualis ellenorzese
   eredmeny-kozpontuan dokumentalva (mit mutat a maradekter es az anchorok el-igazitasa).
7. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md`
   PASS, es a report DoD -> Evidence Matrix path+line bizonyitekokkal kitoltve.

## Constraints (nem alkuképes)

- Spacing/margin nem csokkentheto; geometriai infeasibility nem allithato (PDF referencia bizonyit).
- CDE a vegso utkozes/hatar igazsag (nincs bbox-only collision).
- Folyamatos forgatas megmarad (nincs 0/90/180/270 kenyszer).
- Nincs part-id / koordinata hardcode; nincs csendes visszaeses regi logikara.
- Cargo toolchain nincs default PATH-on: export RUSTUP_HOME/CARGO_HOME + stable toolchain bin a
  cargo/verify.sh futtatas elott.
