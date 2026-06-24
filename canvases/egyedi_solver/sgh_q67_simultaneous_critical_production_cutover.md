# SGH-Q67 - Simultaneous critical production cutover

## Goal

Kotesd be a `critical_simultaneous.rs` bounded same-part group admission logikajat a production
`try_admit_critical()` utba ugy, hogy a `VRS_SIMULTANEOUS_CRITICAL=1` gate alatt ne csak
instrumentacio legyen, hanem a modul tenylegesen probalja meg a 2-es / 3-as same-part critical
group admissiont, es siker eseten o adja vissza a committed layoutot.

## Context

Az audit szerint a Q60 modul megvan, de a production builder jelenleg foleg a
`try_seeded_critical_separation` + `simultaneous_critical_repack` altalanos utjara tamaszkodik. A
Q60 bounded group admission emiatt nem elso rangon hoz dontest, csak legfeljebb kozvetetten
jelez. A kovetkezo hianyzik: a modul live solver helyzetben, ugyanabban a sheet-builder critical
admission utban kapjon authorityt.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/report_standard.md`
- `tmp/audit/audit_2026_06_23.md`
- `canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md`

## Scope

- Gate alatt a production builder explicit simultaneous group authority probat futtat.
- Elso korben same-part repeated critical csoportokra (2 vagy 3 darab) ervenyes production cutover.
- Siker eseten a modul a live layoutot is vissza tudja adni.
- Sikertelenseg eseten explicit best-partial / rejection summary marad a diagnosztikaban.

## Non-goals

- Nem teljes altalanos mixed-part group optimizer.
- Nem layoutminosegi PASS allitas 3/3 spacinges LV8-re.
- Nem fallback utak eltavolitasa.

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs`
  - legyen live solver `SPInstance` + `SheetShape` alapu same-part group admission helper.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - a production `try_admit_critical()` ut elejen / role-aware utjaban hivja ezt a group authority
    probat, es full success eseten commitolja a live layoutot.
- `rust/vrs_solver/src/io.rs`
  - keruljenek be explicit production simultaneous authority diagnostikak.
- `rust/vrs_solver/tests/sparrow_q67_simultaneous_cutover.rs`
  - solve-boundary teszt gate-off/gate-on bizonyitekkal.
- `artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json`
  - live artifact 2-part es 3-part scenario summaryval.

## Acceptance

- gate-off run nem allit be simultaneous authority diagnostikakat;
- gate-on runban a production path explicit simultaneous authority probat jelent;
- same-part 2-es group eseten a modul kepes accepted source-szal committed layoutot adni;
- 3-as group eseten, ha nincs full success, a best partial es rejection summary latszik;
- a fallback tovabbra is elerheto;
- `./scripts/verify.sh --report ...` PASS.
