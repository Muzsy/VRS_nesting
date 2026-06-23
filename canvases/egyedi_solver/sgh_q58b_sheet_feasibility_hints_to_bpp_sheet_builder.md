# Q58B — SheetFeasibilityHints bekötése a BPP / sheet-builderbe

## Goal / Funkció

Használd a Q58A `SheetFeasibilityHints`-et a critical-aware sheet builder és a BPP reduction
stratégiai irányítására. A hint **nem** final authority: stratégiai vezérlés (mely kritikus partokat
próbáld először, hány kritikus part/tábla, mikor tartsd nyitva a kritikus fázist, mely partial
incumbent maradjon meg, mikor állj le egy lehetetlen kvótával).

## Context / Háttér

A jelenlegi sheet-builder `critical_frontier` / consecutive-fail guarddal zárja a kritikus fázist. A
Q58B ezt hint-aware-ré teszi: ha a hint szerint egy sheet 3 kritikus partot célozzon, ne zárja a
kritikus fázist sekély bukások után az Anchor/Interlock/BandInsert utak kipróbálása előtt — de
végtelen próbálkozás nélkül. **Kötelező** a best-partial preservation: ha a kvóta bukik, a legjobb
valid partial layout megmarad; soha ne térjen vissza rosszabb 1/3-ra, ha korábban volt valid 2/3.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q58B_SheetFeasibilityHints_to_BPP_sheet_builder.md`
- Függés: Q58A `SheetFeasibilityHints`.

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `build_critical_aware_seed(...)`,
  `try_admit_critical(...)`, `critical_frontier`, best partial / fallback handling, bpp diagnostics.
- `rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs` — `build_criticality_queues(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — SkeletonRole assignment.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_feasibility.rs` — Q58A hints.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
rust/vrs_solver/src/optimizer/sparrow/sheet_feasibility.rs
rust/vrs_solver/src/io.rs
```

## Scope

- Critical queue ordering finomítása hint-tel (priority_score megőrizve, kombinálva, diagnosztizálva).
- Sheet-enkénti target kritikus kvóta hint + minimum hasznos partial count.
- Critical phase frontier hint-aware kiterjesztés (de bounded).
- Best partial preservation (kötelező, diagnosztikával).
- Gate: `VRS_SHEET_FEASIBILITY_HINTS=1`.
- Fókuszált artifact.

## Out of scope

- Hints final authority-vé tétele; exact CDE validáció megkerülése.
- 2-sheet eredmény kényszerítése proof nélkül.
- Simultaneous triple admission (Q60).

## Required implementation

1. **Critical queue ordering:** `danger_parts` + kritikus típus-hint szerint, figyelembe véve
   criticality_tier, fit_difficulty, sheet-count-driver, alacsony estimated max per sheet, ismételt
   kritikus mennyiség-nyomás, pair/triple stratégia elérhetőség. `priority_score` megmarad.
2. **Target kvóta:** sheet-enként target kritikus típusok, típusonkénti count, összes target kritikus
   count, fallback minimum hasznos partial count.
3. **Critical phase frontier:** hint-aware; ha a hint 3-at céloz, ne zárj sekély bukás után a releváns
   Anchor/Interlock/BandInsert utak előtt, de kerüld a végtelen próbálkozást.
4. **Best partial preservation (kötelező):** kvóta-bukáskor a legjobb valid partial megmarad
   (critical_count, hint target satisfaction, placed area, free-space score, future sheet feasibility
   szerint). Soha nem ad vissza rosszabb 1/3-at, ha volt valid 2/3 — ez a regresszió-osztály
   konstrukció szerint lehetetlen.

Integrációs szabály: a hint advisory; minden placement átmegy az exact validáción. Hint-konfliktus
logolva (`hint_target_failed`, `observed_best_partial`, `reason_summary`).

## Required diagnostics

Mezők: `bpp_sheet_feasibility_hints_used`, `bpp_target_critical_distribution`,
`bpp_sheet_target_quota`, `bpp_sheet_target_quota_met`, `bpp_sheet_best_partial_critical_count`,
`bpp_sheet_best_partial_source`, `bpp_hint_queue_reorder_applied`,
`bpp_hint_frontier_extension_applied`, `bpp_hint_quota_abandoned_reason`.

Artifact: `artifacts/benchmarks/sgh_q58b/sheet_builder_hints_integration.json` —
`critical_distribution_hint`, `sheet_attempts[]` (sheet_index, target_quota,
critical_candidates_attempted, critical_placed, best_partial_count, best_partial_source, quota_met,
abandoned_reason).

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_sheet_feasibility_bpp_integration.rs`. Ellenőrzések:

1. A hints elérhető a `build_critical_aware_seed` számára.
2. A critical queue order csak hint-gate bekapcsolva változik.
3. A target kvóta látható a diagnosztikában.
4. Valid best partial megmarad, ha a kvóta bukik.
5. Hint/gate nélkül a korábbi viselkedés reprodukálható (byte-azonos).

Fókuszált futás: valós LV8 kritikus part család, single/multisheet, valós spacing/margin, skeleton +
feature candidates + sheet feasibility hints bekapcsolva.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
VRS_SHEET_FEASIBILITY_HINTS=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
```

## Acceptance criteria

```text
- A BPP/sheet-builder fogyasztja a SheetFeasibilityHints-et explicit gate alatt.
- A critical queue/quota/frontier hint-aware.
- A best partial preservation implementált és diagnosztikával alátámasztott.
- A 2/3 → final 1/3 regresszió-osztály konstrukció szerint lehetetlen.
- Az artifact bizonyítja a target kvótát és a best-partial viselkedést.
```

## Hard restrictions

```text
- a hint nem skippeli az exact CDE validációt
- nincs 2-sheet eredmény kényszerítés proof nélkül
- valid partial nem dobható el csak mert a target kvóta bukott
- nincs LV8 distribution hardcode
- a fallback viselkedés nem rejthető el
- nincs NFP, nincs bbox collision shortcut, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- Az integráció `VRS_SHEET_FEASIBILITY_HINTS` gate mögött; default off → byte-azonos no-regression.
- Ha a hint-aware frontier instabilitást/timeoutot okoz, gate-off visszaállítja a meglévő
  `critical_frontier` viselkedést; a best-partial preservation azonban gate-független invariáns marad.

## Deliverables

```text
canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.yaml
codex/prompts/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder/run.md
codex/codex_checklist/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.verify.log
```
