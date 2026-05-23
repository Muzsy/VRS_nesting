# Checklist — JG-07 jagua_optimizer_t07_layout_state_and_candidate_model

## Feladat

Optimizer állapotmodell és candidate move skeleton létrehozása a JG-06 utáni Phase 1 láncban. Ez adatmodell és diagnosztikai alap, nem construction placer vagy score/search implementáció.

## Dependency

- [x] JG-06 report létezik.
- [x] JG-06 report első sora `PASS`.
- [x] JG-06 report tartalmazza: `JG-07_STATUS: READY`.
- [x] JG-06 item geometry store / rotation cache evidence áttekintve.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Layout state model

- [x] `rust/vrs_solver/src/optimizer/state.rs` létrejött vagy a report explicit indokolja az alternatív repo-konform helyet.
- [x] `LayoutState` modell létrejött vagy részletesen definiálva.
- [x] Placed állapot külön kezelve.
- [x] Unplaced állapot külön kezelve.
- [x] Part id / instance id kapcsolat nem vész el.
- [x] Sheet index / sheet metadata stabilan kezelve.
- [x] Determinism / seed mezők előkészítve.
- [x] State diagnosztikába szerializálható.
- [x] Invalid/partial state nem jelenik meg sikeres final layoutként.

## Transform model

- [x] `PlacementTransform` modell létrejött.
- [x] Translation adat (`x`, `y` vagy ekvivalens) szerepel.
- [x] Rotation adat (`rotation_deg` vagy ekvivalens) szerepel.
- [x] Transform adat nem veszik el placed recordba konvertáláskor.
- [x] V1 `Placement` contract kompatibilis maradt.

## Candidate move skeleton

- [x] `rust/vrs_solver/src/optimizer/moves.rs` létrejött vagy a report explicit indokolja az alternatív repo-konform helyet.
- [x] `CandidateMove` modell létrejött.
- [x] Place candidate alap szerepel.
- [x] Move candidate alap szerepel.
- [x] Reinsert candidate alap szerepel.
- [x] Rotate candidate alap szerepel.
- [x] A skeleton nem implementál minőségi search-t vagy collision alapú candidate generationt.
- [x] Candidate move diagnosztikai reprezentációja stabil/determinisztikus.

## Objective breakdown skeleton

- [x] `rust/vrs_solver/src/optimizer/score.rs` létrejött vagy a report explicit indokolja az alternatív repo-konform helyet.
- [x] `ObjectiveBreakdown` skeleton létrejött.
- [x] `placed_count` vagy ekvivalens mező szerepel.
- [x] `unplaced_count` vagy ekvivalens mező szerepel.
- [x] `sheet_count_used` vagy ekvivalens mező szerepel.
- [x] Penalty / placeholder mezők későbbi score modelhez előkészítve.
- [x] Ez még nem score optimalizáló implementáció.

## Smoke / tests

- [x] State unit tesztek PASS.
- [x] Transform serialization / diagnostics teszt PASS.
- [x] CandidateMove skeleton teszt PASS.
- [x] ObjectiveBreakdown skeleton teszt PASS.
- [x] Deterministic state ordering teszt PASS.
- [x] Existing JG-06 smoke továbbra is PASS.
- [x] Existing JG-05 rectangular smoke továbbra is PASS.
- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS — 21/21.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.verify.log`.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz optimizer module design döntést.
- [x] Report tartalmaz rövid állapotdiagramot vagy állapotmodell leírást.
- [x] Report tartalmaz candidate move skeleton leírást.
- [x] Report tartalmaz objective breakdown skeleton leírást.
- [x] Report tartalmaz futtatott parancsokat és eredményeket.
- [x] Globális progress checklist JG-07 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-08_STATUS: READY` vagy `NOT_READY`.
