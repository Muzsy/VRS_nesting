# Codex checklist — sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler

## Kötelező workflow

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/yaml_schema.md`
- [x] Elolvastam: `docs/codex/report_standard.md`
- [x] Canvas pontos: `canvases/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`
- [x] Goal YAML pontos: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.yaml`
- [x] A task elején rögzítettem a `git status --short` állapotot. (clean — csak a Q29 canvases/checklist/goals/prompts fájlok untracked)

## Phase A — upstream Sparrow A/B

- [x] Ellenőriztem: `.cache/sparrow` létezik.
- [x] Rögzítettem az upstream commitot: `git -C .cache/sparrow rev-parse HEAD`. (c95454e390276231b278c879d25b39708398b7d3)
- [x] Rögzítettem az upstream git státuszt.
- [ ] Nem használtam saját `vrs_solver` binárist upstream referenciaként.
- [ ] Nem használtam saját no-session / fallback buildet upstream referenciaként.
- [ ] Feltártam az upstream input schema / példa / CLI működést.
- [ ] Lefuttattam legalább micro upstream case-t, vagy BLOCKED indokoltam.
- [ ] Lefuttattam legalább medium upstream case-t, vagy BLOCKED indokoltam.
- [ ] Ha LV8-derived case futott upstreamen, dokumentáltam a konverziót.
- [ ] Létrejött: `artifacts/benchmarks/sgh_q29/upstream_ab_summary.json`.
- [ ] Létrejött: `artifacts/benchmarks/sgh_q29/upstream_ab_report.md`.

## Phase B — local CDE/search hotspot profiler

- [ ] A profiling env-flag vagy explicit profiling mód mögött fut, default szemantikát nem módosít.
- [ ] Nem módosítottam solver-algoritmust optimalizálási céllal.
- [ ] Mértem: native_search_placement total ms / calls.
- [ ] Mértem: candidate transform / shape prepare ms.
- [ ] Mértem: CDE query / collect ms.
- [ ] Mértem: specialized pipeline ms.
- [ ] Mértem: hazard/loss ms.
- [ ] Mértem vagy indokoltam: boundary check ms.
- [ ] Mértem vagy indokoltam: broadphase/bbox reject count.
- [ ] Mértem vagy indokoltam: early termination count.
- [ ] Lefutott local profiler medium case-en.
- [ ] Lefutott local profiler LV8-derived case-en.
- [ ] Dense191 case futott vagy explicit indokoltan kihagyva.
- [ ] Létrejött: `artifacts/benchmarks/sgh_q29/local_cde_hotspot_summary.json`.
- [ ] Létrejött: `artifacts/benchmarks/sgh_q29/local_cde_hotspot_report.md`.

## Smoke + quality gate

- [ ] `python3 scripts/smoke_sgh_q29_upstream_ab_and_cde_hotspot_profiler.py` PASS.
- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` PASS.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md` PASS.
- [ ] AUTO_VERIFY blokk frissült.
- [ ] Report tartalmazza a két végső választ:
  - [ ] Upstreamhez képest hol állunk?
  - [ ] A saját CDE/search útvonalon mi viszi el az időt?

## Tiltások ellenőrzése

- [ ] Nem vezettem be compressiont.
- [ ] Nem módosítottam strict touching policy szemantikát.
- [ ] Nem módosítottam worker ordering / GLS / search acceptance logikát optimalizálásként.
- [ ] Nem írtam azt, hogy upstream A/B történt, ha nem futott valódi `.cache/sparrow` upstream.
- [ ] Nem lazítottam Q28/Q26 gate-et.
