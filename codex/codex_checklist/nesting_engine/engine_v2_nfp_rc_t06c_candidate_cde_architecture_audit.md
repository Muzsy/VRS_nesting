# T06c — Candidate CDE Architecture Audit Checklist

## Előkészület

- [x] T06b report elolvasva (`engine_v2_nfp_rc_t06b_cfr_strategy_benchmark.md`)
- [x] T06a report elolvasva (`engine_v2_nfp_rc_t06a_cfr_bottleneck_audit.md`)
- [x] T05u report elolvasva (`engine_v2_nfp_rc_t05u_nfp_provider_audit.md`)
- [x] T05v report elolvasva (`engine_v2_nfp_rc_t05v_nfp_provider_pilot.md`)
- [x] T05w report elolvasva (`engine_v2_nfp_rc_t05w_provider_selection_cache_key.md`)
- [x] T05x report elolvasva (`engine_v2_nfp_rc_t05x_cgal_reference_provider.md`)

## Forrásfájl Audit

- [x] `nfp_placer.rs` — teljes file elolvasva (1018 sor)
- [x] `cfr.rs` — teljes file elolvasva (845 sor)
- [x] `cache.rs` — teljes file elolvasva (350 sor)
- [x] `provider.rs` — teljes file elolvasva (238 sor)
- [x] `nfp/mod.rs` — teljes file elolvasva (73 sor)
- [x] `feasibility/mod.rs` — teljes file elolvasva (4 sor)
- [x] `feasibility/aabb.rs` — teljes file elolvasva (54 sor)
- [x] `feasibility/narrow.rs` — teljes file elolvasva (627 sor)
- [x] `nfp/nfp_validation.rs` — teljes file elolvasva (170 sor)
- [x] `nfp/ifp.rs` — teljes file elolvasva (119 sor)
- [x] `geometry/types.rs` — részben elolvasva (143 sor)
- [x] `geometry/scale.rs` — teljes file elolvasva (34 sor)
- [x] `multi_bin/greedy.rs` — részben elolvasva (1077 sor)
- [x] `geometry/` — directory listing

## CFR Hot-Loop Feltérképezés

- [x] CFR hot-loop call graph dokumentálva
- [x] `compute_cfr_internal()` belépési pont azonosítva (cfr.rs:185)
- [x] `run_overlay(NFP_shapes, [], Union)` bottleneck azonosítva (cfr.rs:234)
- [x] `run_overlay(IFP_shape, union_shapes, Diff)` azonosítva (cfr.rs:259)
- [x] NFP polygon összegyűjtés helye azonosítva (nfp_placer.rs:204-267)
- [x] Candidate extraction helye azonosítva (nfp_placer.rs:595-641)
- [x] Collision check (`can_place()`) helye azonosítva (narrow.rs:79)
- [x] Broad-phase (RTree) azonosítva (narrow.rs:PlacedIndex)
- [x] Narrow-phase (polygons_intersect_or_touch) azonosítva (narrow.rs:261)
- [x] Típusok azonosítva (Polygon64, Point64, IfpRect, PlacedPart, Aabb, stb.)
- [x] T06b snapshot helye azonosítva (cfr.rs:42-85, 224-227)

## Candidate Source Audit

- [x] CFR output candidate source értékelve (jelenlegi baseline)
- [x] IFP corners candidate source értékelve
- [x] Pairwise NFP vertex candidate source értékelve
- [x] Pairwise NFP edge/contact candidate source értékelve
- [x] Placed bbox / anchor candidate source értékelve
- [x] BLF / bottom-left candidate source értékelve
- [x] Current CFR output mint reference oracle értékelve
- [x] Sliding / exact-fit candidate source értékelve (későbbi irány)
- [x] Full CFR nélküli candidate útvonalak értékelve
- [x] Candidate source összehasonlító táblázat készült

## Collision Index / CDE Terv

- [x] SheetCollisionState adat modell terv készült
- [x] AABB broad-phase terv készült (RTree újrafelhasználás)
- [x] Exact narrow-phase terv készült (can_place() újrafelhasználás)
- [x] Spacing kezelés terv készült (inflated polygon)
- [x] Sheet boundary / IFP containment terv készült
- [x] Holes / cavity_prepack utáni geometria terv készült
- [x] Polygon64 / Point64 típusok illeszkedése dokumentálva
- [x] Meglévő nfp_validation / geometry modulok kapcsolódása dokumentálva
- [x] jagua-rs / külső CDE opcionális adapter terv készült (nem T06d scope)

## Exact Validation Gate

- [x] Validator követelmények definiálva (no overlap, bounds, spacing, holes)
- [x] Meglévő can_place() mint validator azonosítva
- [x] SheetCollisionState mint collision state management azonosítva
- [x] Tolerancia (TOUCH_TOL=1 µm) dokumentálva
- [x] Hibareportálási terv készült

## Optimizer Preservation Plan

- [x] Greedy preservation dokumentálva
- [x] SA preservation dokumentálva
- [x] Multi-sheet preservation dokumentálva
- [x] Slide compaction preservation dokumentálva
- [x] Quality profile-ok preservation dokumentálva
- [x] NFP provider selection preservation dokumentálva
- [x] NFP cache preservation dokumentálva
- [x] Módosított függvények listája készült
- [x] Feature flag terv készült (NESTING_ENGINE_CANDIDATE_DRIVEN)
- [x] Régi vs új útvonal benchmark stratégia készült

## Prototype Options Comparison

- [x] Opció A (in-repo minimal CDE) értékelve
- [x] Opció B (jagua-rs PoC) értékelve
- [x] Ajánlott opció kiválasztva: Opció A
- [x] Indoklás dokumentálva

## Benchmark Terv

- [x] Metrikák definiálva (placed count, runtime, candidate count, stb.)
- [x] Benchmark parancsok dokumentálva (baseline vs candidate-driven)
- [x] Correctness gate definiálva (false accept = 0, placed ≥ baseline × 0.95)

## Kockázatelemzés

- [x] Candidate generator túl kevés jelölt kockázat dokumentálva
- [x] Broad-phase túl sok találat kockázat dokumentálva
- [x] Exact validator túl lassú kockázat dokumentálva
- [x] NFP cache túl nagy kockázat dokumentálva
- [x] Spacing kezelés pontatlanság kockázat dokumentálva
- [x] Holes / cavity_prepack visszabontás kockázat dokumentálva
- [x] SA cost összehasonlíthatóság kockázat dokumentálva
- [x] CFR vs candidate-driven eltérés kockázat dokumentálva

## T06d Javaslat

- [x] Task címe meghatározva
- [x] Cél meghatározva
- [x] Nem célok meghatározva
- [x] Érintett fájlok listázva
- [x] Minimális implementáció leírva
- [x] Feature flag neve meghatározva
- [x] Benchmark parancsok dokumentálva
- [x] Acceptance criteria definiálva
- [x] Rollback stratégia dokumentálva

## Output fájlok

- [x] `codex/reports/nesting_engine/engine_v2_nfp_rc_t06c_candidate_cde_architecture_audit.md` létrehozva
- [x] `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t06c_candidate_cde_architecture_audit.md` létrehozva

## Szigorú tiltások betartása

- [x] Nincs új optimalizáló írva
- [x] Greedy / SA / multi-sheet / compaction lánc nem lett módosítva
- [x] jagua-rs vagy külső CDE nincs production módon integrálva
- [x] Nincs bbox pre-merge hack javasolva főirányként
- [x] Placement behavior nincs módosítva
- [x] CFR nincs kikapcsolva production módban
- [x] Nincs silent fallback bevezetve
- [x] Nincs approximate placement exact final validation nélkül javasolva
- [x] Production Dockerfile nincs módosítva
- [x] Nincs T08 indítva
- [x] Nincs nagy feature implementálva ebben a taskban

## Codex stílus

- [x] Markdown renderelhető, nincs ASCII art vagy box drawing, amit ne lehetne terminálban olvasni
- [x] Magyar nyelvű output
- [x] Step-by-step phased execution jelzés: AUDIT kész, IMPLEMENTATION nem indult
- [x] Rövid verdikt a végén: PASS/PARTIAL/FAIL
- [x] Következő emberi döntési pont azonosítva
