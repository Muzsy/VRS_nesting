# T05u NFP Provider Audit Checklist

## NFP Call Graph feltérképezve ✓
- `main.rs` → `greedy_multi_sheet` → `nfp_place` → `compute_nfp_lib` (nfp_placer.rs:489) ✓
- `compute_nfp_lib`: convex A + convex B → `compute_convex_nfp()` (OK) ✓
- `compute_nfp_lib`: egyéb → `compute_concave_nfp_default()` (BOTTLENECK) ✓
- `compute_stable_concave_nfp` (concave.rs:261): decompose_to_convex_parts → 342×518=177K pairs → `union_nfp_fragments` ✓
- `union_nfp_fragments` (concave.rs:1057): `i_overlay Strategy::List` → NEM ÁLL VISSZA ✓
- `compute_orbit_exact_nfp` (concave.rs:320): alternatív mód, nem default ✓

## Optimizer Call Graph feltérképezve ✓
- `greedy_multi_sheet` → `nfp_place` vagy `blf_place` → part ordering → candidate generation → collision check ✓
- Slide compaction: `greedy.rs` CompactionMode::Slide ✓
- SA: `run_sa_search_over_specs` → greedy_single_sheet minden iteráción ✓
- Scoring: REMNANT_AREA_WEIGHT 500k ppm, REMNANT_COMPACTNESS 300k, REMNANT_MIN_WIDTH 200k ✓
- cavity_prepack output: main.rs → `run_inflate_pipeline` → pipe_resp → hole_collapsed check ✓

## Concave fragment-union bottleneck pontosan azonosítva ✓
- `concave.rs:911` decompose_to_convex_parts: ear_clip_triangulate → n-2 triangles per polygon ✓
- Lv8_07921_50db: 344pts → 342 triangles ✓
- Lv8_11612_6db: 520pts → 518 triangles ✓
- 342 × 518 = 177,156 NFP pairs → partial NFP loop ~6s → union SOHA nem tér vissza ✓
- `i_overlay Strategy::List` O(n²) vagy rosszabb 177K polygonon ✓

## Meglévő optimizer rétegek dokumentálva ✓
- greedy.rs: greedy multi-sheet + remnant scoring + slide compaction ✓
- sa.rs: SA search over part order + rotation space ✓
- nfp_placer.rs: NFP generation + cache + CFR + candidate + collision ✓
- blf.rs: BLF fallback placer ✓
- cfr.rs: IFP CFR computation (i_overlay Union + Difference) ✓

## Új optimalizáló írása elkerülve ✓
- TILOS: greedy.rs / sa.rs módosítása NEM volt a feladat ✓
- Minden optimizer komponens változatlanul marad a tervben ✓

## NFP Provider Interface terv elkészült ✓
- `NfpProvider` trait definiálva ✓
- `NfpKernel` enum: OldConcave / ReducedConvolutionExperimental / CgalProbeReference ✓
- `NfpProviderResult` struct: outer, holes, compute_time_ms, kernel, validation_status ✓
- Provider dispatch a `compute_nfp_lib` szintjén ✓

## Cache kulcs terv elkészült ✓
- `NfpCacheKeyV2` bővítés kernel + cleanup_profile mezőkkel ✓
- shape_id tartalmazza geometry-t (implicit) ✓
- cache lekérdezés: nfp_placer.rs:208 (változatlan) ✓
- cache feltöltés: nfp_placer.rs:247 (változatlan) ✓
- failure/timeout cache tiltás: Err ág nem insert-el ✓

## CGAL reference provider korlátai dokumentálva ✓
- CGAL GPL: soha production Docker image, soha production runtime ✓
- Binary: tools/nfp_cgal_probe/build/nfp_cgal_probe v0.2.0 ✓
- Feature flag / env flag mögött kell hogy legyen ✓
- CI: opcionális ✓
- JSON contract: input + output specifikálva ✓

## Production CGAL tiltás dokumentálva ✓
- TILOS: production Dockerfile módosítás ✓
- TILOS: CGAL production dependencyvé tétele ✓
- TILOS: silent fallback CGAL-ról OldConcave-re ✓

## Rust experimental provider terv elkészült ✓
- `reduced_convolution.rs` → `RcNfpProvider` wrapper ✓
- `compute_rc_nfp` → `NfpProviderResult` konverzió ✓
- T06 cleanup: `run_minkowski_cleanup` meghívása compute után ✓
- T07 validátor: `polygon_validation_report` minden output-on ✓
- Productionba lépés feltétele: T05b–T05e T07 + CGAL vs RC benchmark ✓

## Következő implementation task javaslat elkészült ✓
- T05v célja: `NfpProvider` trait + `OldConcaveProvider` pilot ✓
- Szükséges fájlok listázva ✓
- Kizárt elemek listázva ✓
