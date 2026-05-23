# Checklist — JG-08 jagua_optimizer_t08_initial_construction_placer_v1

## Feladat

Első construction placer V1: deterministic item ordering + rectangular candidate-point próbák jagua boundary/collision checkkel, exact validatorral ellenőrzött Phase 1 rectangular outer-only layoutokra.

## Dependency

- [x] JG-04 report létezik.
- [x] JG-04 report első sora `PASS`.
- [x] JG-04 JaguaAdapter contract PoC elérhető az aktuális kódban.
- [x] JG-07 report létezik.
- [x] JG-07 report első sora `PASS`.
- [x] JG-07 report tartalmazza: `JG-08_STATUS: READY`.
- [x] JG-07 layout state / placement transform / candidate move / objective breakdown skeleton bizonyított.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Initial construction placer

- [x] Initial item ordering dokumentálva: area/bbox/egyéb tie-breaker.
- [x] Item ordering determinisztikus és tesztelt.
- [x] Rectangular candidate point generálás V1 implementálva.
- [x] Candidate dedupe determinisztikus.
- [x] Candidate sorting determinisztikus.
- [x] Sheet origin candidate szerepel.
- [x] Existing placement bbox jobb/felső candidate pontjai szerepelnek.
- [x] Jagua boundary check minden candidate próbánál használva.
- [x] Jagua collision check minden candidate próbánál használva.
- [x] Elhelyezhetetlen item explicit `unplaced` státuszba kerül.
- [x] Elhelyezhetetlen item nem tűnik el silent módon.
- [x] `placed_count + unplaced_count` egyezik az instance counttal.
- [x] Runtime/time limit nem végtelen ciklusos.

## Validation és fixtures

- [x] Small fixture minden partja validan elhelyezhető vagy explicit okkal unplaced.
- [x] Small fixture exact validator PASS.
- [x] Medium fixture legalább részleges, de valid layoutot ad.
- [x] Medium fixture exact validator PASS.
- [x] Invalid layout soha nem kap successful PASS státuszt.
- [x] Out-of-sheet vagy invalid sheet-index negatív esetet validator elutasít.
- [x] Overlap negatív esetet validator elutasít.
- [x] Determinism: azonos input + seed azonos placement listát ad.

## Diagnostics

- [x] Candidate count reportolva.
- [x] Rejection reason legalább részben reportolva: `OUT_OF_SHEET`, `COLLISION`, `UNSUPPORTED_ROTATION`, `NO_CANDIDATE`.
- [x] Report tartalmaz példafuttatást.
- [x] Report tartalmaz item ordering policyt.
- [x] Report tartalmaz candidate generation policyt.

## Smoke / tests

- [x] `scripts/smoke_jagua_initial_construction.py` létrejött.
- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS — 35/35.
- [x] `python3 scripts/smoke_jagua_initial_construction.py` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.verify.log`.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz valós kód auditot.
- [x] Report tartalmaz candidate model döntést.
- [x] Report tartalmaz exact validation evidence-t.
- [x] Globális progress checklist JG-08 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-09_STATUS: READY` vagy `NOT_READY`.
