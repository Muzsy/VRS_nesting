# Ipari 2D Irregular Nesting Engine backlog (Blueprint architektúra, P0–P3)

## 🎯 Funkció

A cél egy ipari minőségű 2D nesting motor backlogja a rögzített architektúrával: geometria-központú, irreguláris bin packing + diszkrét rotáció (akár 1°) + part-in-part + kerf/spacing a magban + későbbi costing.

Ez a canvas tervezés/priorizálás: konkrét, repo-szintű feladatlista (P0–P3), DoD-vel és érintett fájlokkal.

## 🧠 Fejlesztési részletek

### Kiinduló repo evidenciák (megtartandó “platform” réteg)

- CLI/pipeline belépés: vrs_nesting/cli.py, vrs_nesting/pipeline/run_pipeline.py, vrs_nesting/pipeline/dxf_pipeline.py
- Run artifact rendszer: vrs_nesting/run_artifacts/run_dir.py
- Solver runner adapterek: vrs_nesting/runner/solver_adapter.py, vrs_nesting/runner/vrs_solver_runner.py, vrs_nesting/runner/sparrow_runner.py
- DXF IO: vrs_nesting/dxf/importer.py, vrs_nesting/dxf/exporter.py
- Geometria utilok (jelenleg Python): vrs_nesting/geometry/clean.py, vrs_nesting/geometry/offset.py, vrs_nesting/geometry/polygonize.py
- Solution validálás: vrs_nesting/validate/solution_validator.py
- Contract doksik: docs/solver_io_contract.md, docs/dxf_project_schema.md, docs/dxf_run_artifacts_contract.md
- Rust solver skeleton: rust/vrs_solver/*

### Nem-cél (ebben a backlogban)

- A Sparrow pipeline “véglegesítése” ipari célra (csak addig marad, amíg kell regresszióhoz / összehasonlításhoz).
- Web platform feature backlog (külön canvas: canvases/web_platform/*).

## P0 (BLOCKER) — Contract freeze + determinisztikus geometriai kernel + feasibility “truth layer”

P0 cél: a rendszer “ipari magja” megszülessen: kettős geometria (nominal/inflated), determinisztikus kernel, feasibility API, és mindez end-to-end futtatható legyen (még ha kezdetben egyszerű placementtel is).

### P0-1 — contract_v2_dual_geometry_and_rotation

Leírás: V2 solver IO + project schema kiegészítés: nominal vs inflated referenciaszintű kezelése, rotation_step_deg (1°) támogatás, irreguláris bin-ek explicit polygonként.

Érintett fájlok (docs):

- docs/solver_io_contract.md → kiegészítés vagy új: docs/solver_io_contract_v2.md
- docs/dxf_project_schema.md → kiegészítés vagy új: docs/dxf_project_schema_v2.md
- docs/dxf_run_artifacts_contract.md (run meta: solver_version, seed, objective breakdown)

Érintett kód:

- vrs_nesting/project/model.py (v2 mezők: machine/material, rotation policy, dual geometry refs)
- vrs_nesting/nesting/instances.py (rotation policy bővítés, geometry ref kezelés)
- vrs_nesting/runner/solver_adapter.py (v1/v2 kompat réteg)

DoD:

- v2 mezők dokumentálva + példajson (input+output)
- v1 kompat nem törik (adapter fallback)
- rotáció reprezentáció rögzítve (fok, óramutató/ellenkező, pivot policy)

### P0-2 — machine_profile_inputs_and_kerf_derive

Leírás: Projekt elején gép/lemez adatokból kerf/spacing → offset_margin számítás rögzítése (későbbi DB előkészítése).

Érintett fájlok:

- vrs_nesting/config/runtime.py (runtime paraméterek)
- vrs_nesting/project/model.py (machine/material/thickness)
- docs/dxf_project_schema_v2.md (kerf source: fix vs lookup)

DoD:

- offset_margin definíció kőbe vésve (egységek, képlet)
- “kerf forrás” jelölhető (fix / lookup stub)

### P0-3 — deterministic_geometry_kernel_rust_clipper2

Leírás: Determinisztikus, skálázott integer geometriai kernel Rustban (Clipper2): offset/clean/simplify/containment/intersection alapok.

Érintett fájlok:

- rust/vrs_solver/Cargo.toml, rust/vrs_solver/src/main.rs (modulosítás: kernel modulok)
- új Rust modulok (javasolt): rust/vrs_solver/src/geometry/*
- Python hívó: vrs_nesting/runner/vrs_solver_runner.py (subprocess/ffi/stdio protokoll)

DoD:

- skálázási policy rögzítve (SCALE, i64)
- offset: outer kifelé, holes befelé (kerf/spacing alapján)
- determinisztikus output (ugyanarra az inputra byte-azonos JSON)

### P0-4 — inflate_and_validate_truth_layer

Leírás: Import után nominal geometria normalizálása + inflated geometria előállítása + validálása (külön diagnosztikával: hole collapse, self-intersection).

Érintett fájlok:

- vrs_nesting/dxf/importer.py (nominal topológia: outer + inner rings)
- vrs_nesting/geometry/clean.py, vrs_nesting/geometry/polygonize.py (átmenetileg maradhat, de P1-ben kiváltjuk)
- vrs_nesting/geometry/offset.py (átkötés Rust kernelre, vagy párhuzamos debug)
- docs/error_code_catalog.md (új error code-ok: OFFSET_INVALID, HOLE_COLLAPSED, SELF_INTERSECT)

DoD:

- nominal valid gate + inflated valid gate
- invalid part/bin listázás reprodukálható hibakóddal
- inflated csak solverhez, export mindig nominalból (explicit szabály)

### P0-5 — feasibility_engine_api_mvp

Leírás: “behelyezhető-e” API (irreguláris bin polygonokra is), broad-phase + narrow-phase alapokkal.

Érintett fájlok:

- Rust: rust/vrs_solver/src/feasibility/*
- Python adapter: vrs_nesting/runner/vrs_solver_runner.py, vrs_nesting/runner/solver_adapter.py
- Validator: vrs_nesting/validate/solution_validator.py (feasibility check v2 szerint)

DoD:

- can_place(part_inflated, bin, transform) működik
- 0 overlap / 0 out-of-bounds garantált a validator szerint
- egyszerű cache (part_id+rot → polygon)

### P0-6 — baseline_placer_single_bin_then_multibin

Leírás: Legyen már futó baseline placement (akár egyszerű BLF/CFR-light): először single-bin, majd multi-bin minimális logikával.

Érintett fájlok:

- Rust: rust/vrs_solver/src/search/* (construction placer)
- vrs_nesting/pipeline/run_pipeline.py (solver mód kapcsoló)
- docs/how_to_run.md (új futtatási mód)

DoD:

- 1° rotációt kezel (diszkrét)
- több bin esetén képes min bin használatra törekedni (egyszerű greedy)
- run artifactban objective mezők kitöltve

## P1 — Stabilizálás + minőségkapuk (determinism, regresszió, DXF export szabályok)

P1 cél: a P0 “már fut” állapotból ipari stabilitás: determinisztikus, robusztus DXF edge-case-ekre, reprodukálható, regressziós tesztekkel.

### P1-1 — dxf_edgecase_suite_arc_spline_chain

Érintett: vrs_nesting/dxf/importer.py, vrs_nesting/geometry/polygonize.py, teszt fixture-ek

DoD: ARC/SPLINE poligonizálás tolerancia szerint; chaining hibák tesztelve; fixture DXF-ek bekerülnek.

### P1-2 — validator_split_independent_kernel

Érintett: vrs_nesting/validate/solution_validator.py

DoD: validator ne ugyanazt a “shortcutot” használja; safe-side policy rögzítve (touch/epsilon).

### P1-3 — export_nominal_only_with_debug_inflated_option

Érintett: vrs_nesting/dxf/exporter.py, docs/solver_io_contract_v2.md

DoD: alap export = nominal (CUT_OUTER/CUT_INNER), debug export = inflated külön layeren.

### P1-4 — ci_smoke_determinism_gate

Érintett: CI workflow (repo scripts/* ha van), docs/qa/testing_guidelines.md

DoD: ugyanazzal a seed-del azonos output hash; időkeret budget; FAIL ha nondeterministic.

## P2 — Minőségjavítás (compaction, part-in-part erősítés, remnant scoring)

P2 cél: a megoldások minősége látványosan javuljon, és a maradék-gazdálkodás “értelmesen” működjön.

### P2-1 — compaction_local_search

Érintett: Rust src/compaction/*

DoD: lokális slide/push, swap/move; objective javulás mérhető.

### P2-2 — part_in_part_candidate_pipeline

Érintett: Rust search modul + (opcionálisan) nominal hole index

DoD: hole-first stratégia; nominal alapján jelölt, inflated-del validált; regressziós teszt.

### P2-3 — remnant_value_model_v1

Érintett: Rust src/metrics/*, docs

DoD: maradék score definíció (area + hasznosság proxy: min width/compactness), inventory policy.

## P3 — Costing + gépadatbázis + ajánlatkérés (ipari üzemi réteg)

P3 cél: a nesting eredményből ajánlat és gyártási becslés legyen (vágásidő, költség), gépprofil DB-vel.

### P3-1 — costing_proxies_now_machine_db_later

Érintett: Rust src/costing/*, docs/*schema_v2.md

DoD: cut length (outer/inner), pierce count, rapid proxy; machine DB lookup interface stub.

### P3-2 — machine_profile_database_schema

Érintett: docs + (később) API/db réteg

DoD: anyag×vastagság → kerf, feedrate, pierce time; versioning.

### P3-3 — quote_output_artifact

Érintett: run artifact contract + export

DoD: JSON “quote” output (idők, költségek, breakdown), reprodukálható.

## 🧪 Tesztállapot

- P0 DoD: legalább 1 end-to-end run (DXF import → inflate+validate → solve → JSON artifact → nominal DXF export) PASS.
- P1 DoD: determinism + regresszió kötelező gate.
- P2 DoD: minőségmetrikák (sheet count / remnant score / proxy cut time) mérhetően javuljanak.
- P3 DoD: costing mezők és gépprofil lookup stabil contracttal.

## 🌍 Lokalizáció

Nem releváns (solver/back-end architektúra és contract).

## 📎 Kapcsolódások

- canvases/egyedi_solver_backlog.md (korábbi backlog keret)
- docs/solver_io_contract.md
- docs/dxf_project_schema.md
- docs/dxf_run_artifacts_contract.md
- docs/error_code_catalog.md
- docs/how_to_run.md
- vrs_nesting/cli.py
- vrs_nesting/pipeline/run_pipeline.py
- vrs_nesting/dxf/importer.py, vrs_nesting/dxf/exporter.py
- vrs_nesting/validate/solution_validator.py
- rust/vrs_solver/*
