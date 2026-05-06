# T05c — CGAL Probe Holes Support: Verification Checklist

**Dátum:** 2025-05-04
**Fázis:** T05c
**Cél:** CGAL probe holes / Polygon_with_holes támogatás + T07 hole-aware correctness

---

## Build ellenőrzések

- [ ] `scripts/build_nfp_cgal_probe.sh` → BUILD SUCCESS
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --version` → `nfp_cgal_probe v0.2.0`
- [ ] `cargo build --release --bin nfp_correctness_benchmark` → BUILD SUCCESS
- [ ] T07 binary: `rust/nesting_engine/target/release/nfp_correctness_benchmark`

---

## Outer-only regresszió (T05b kompatibilitás)

### lv8_pair_01
- [ ] CGAL probe: `status=success`, output_holes=0
- [ ] T07: `correctness_verdict=PASS`, FP=0, FN=0, boundary_mm=0.0

### lv8_pair_02
- [ ] CGAL probe: `status=success`, output_holes=0
- [ ] T07: `correctness_verdict=PASS`, FP=0, FN=0, boundary_mm=0.0

### lv8_pair_03
- [ ] CGAL probe: `status=success`, output_holes=0
- [ ] T07: `correctness_verdict=PASS`, FP=0, FN=0, boundary_mm=0.0

---

## CGAL probe holes parsing

- [ ] `make_polygon_with_holes()` függvény létezik
- [ ] `reflect_polygon_with_holes()` függvény létezik
- [ ] CGAL API hívás: `minkowski_sum_by_reduced_convolution_2(pwh_a, reflected_pwh_b)`
- [ ] Stats JSON tartalmazza: `input_holes_a`, `input_holes_b`, `input_hole_vertices_a`, `input_hole_vertices_b`, `output_holes`, `output_hole_vertices`

---

## Holes smoke fixture

### CGAL probe output
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --fixture .../lv8_pair_holes_smoke.json --output-json ...`
- [ ] exit code: 0
- [ ] `status=success`
- [ ] `holes_i64` nem üres (legalább 1 hole)
- [ ] `holes_i64[0]` legalább 3 vertex
- [ ] `stats.output_holes >= 1`
- [ ] `stats.output_hole_vertices >= 3`

### T07 holes-aware correctness
- [ ] `cargo run --bin nfp_correctness_benchmark -- --fixture ...lv8_pair_holes_smoke.json --nfp-source external_json --nfp-json ... --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 --output-json`
- [ ] `correctness_verdict=PASS`
- [ ] `false_positive_count=0`
- [ ] `false_negative_count=0`
- [ ] `boundary_penetration_max_mm=0.0`
- [ ] `notes` tartalmazza: `HOLES_AWARE`
- [ ] `holes_i64` parse-olva a Polygon64-be

---

## T07 holes correctness implementáció

- [ ] `holes: Vec<Vec<Point64>>` a Polygon64-ben external_json ágból
- [ ] `point_in_polygon()` figyelembe veszi a holes-t
  - Inside: outer belsejében ÉS nem hole-ban
  - Outside: outer-en kívül VAGY hole-ban
- [ ] Scale-aware konverzió: `x * 1_000_000 / scale`
- [ ] Nincs silent fallback: ha holes_i64 üres, nincs note HOLES_AWARE

---

## Real LV8 hole-os pair

- [ ] Keresés: LV8 part-ok akárhol a repo-ban holes_mm-mel → NEM talált
- [ ] Dokumentálva a jelentésben: real LV8 holes pair NEM érhető el
- [ ] Ok: cavity_prepack v2 fill-elı a lyukakat a solver inputban

---

## Korlátozások dokumentálva

- [ ] Hole boundary sampling NEM implementált (csak outer boundary mintavételezés)
- [ ] T08 Engine v2 integráció TILTVA
- [ ] CGAL GPL licenc — production Docker image NEM tartalmazza

---

## Összefoglaló eredmények

| pair_id | fixture_type | sidecar_status | output_holes | T07 verdict | FP | FN | holes_correctness |
|---------|-------------|---------------|-------------|-------------|----|----|-------------------|
| lv8_pair_01 | outer-only LV8 | success | 0 | PASS | 0 | 0 | outer-only |
| lv8_pair_02 | outer-only LV8 | success | 0 | PASS | 0 | 0 | outer-only |
| lv8_pair_03 | outer-only LV8 | success | 0 | PASS | 0 | 0 | outer-only |
| lv8_pair_holes_smoke | synthetic | success | 1 | PASS | 0 | 0 | hole-aware |

---

## Módosított fájlok

- [ ] `tools/nfp_cgal_probe/src/main.cpp` — holes-aware, v0.2.0
- [ ] `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` — holes_i64 parser, hole-aware containment
- [ ] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_holes_smoke.json` — ÚJ synthetic smoke fixture
- [ ] `codex/reports/nesting_engine/engine_v2_nfp_rc_t05c_cgal_holes_probe.md` — jelentés
- [ ] `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t05c_cgal_holes_probe.md` — checklist

---

## Státusz

**PASS**

- CGAL probe: holes input → holes output ✓
- T07: holes_i64 parse + hole-aware containment ✓
- Outer-only regresszió: 3/3 PASS ✓
- Synthetic holes smoke: PASS ✓
- Real LV8 holes: NEM ELÉRHETŐ (nem a probe/validator hibája) ✓
