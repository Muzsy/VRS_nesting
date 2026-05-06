# T05b — CGAL Sidecar Probe: LV8 NFP Reference Implementation

**Dátum:** 2025-05-04
**Fázis:** T05b (CGAL sidecar prototípus)
**Állapot:** PARTIAL — probe és validator működik, jelentés+checklist elkészült, T08 integráció NEM indult

---

## 1. Telepített dependencyk

| Csomag | Verzió | Megjegyzés |
|--------|--------|------------|
| libcgal-dev | 5.6.1-3 | Header-only, Boost-ra épül |
| libboost-dev | 1.83.0 | Chrono, system, thread |
| libgmp-dev | 6.3.0 | Exact integer arithmetic |
| libmpfr-dev | 4.2.0 | Exact floating-point |
| nlohmann-json3-dev | 3.10.5-1 | JSON parsing |
| build-essential | — | g++, make |
| cmake | 3.25.1 | Build system |

**CGAL verzió:** 5.6 (Xenial, Debian 12)
**CGAL mód:** Header-only (`-DCGAL_HEADER_ONLY`)

---

## 2. Build sikeressége

**Igen** — mindkét komponens sikeresen buildelődött.

### CGAL probe
- **Binary:** `tools/nfp_cgal_probe/build/nfp_cgal_probe`
- **Méret:** 1.3 MB
- **Build ideje:** ~5s (CMake + g++ -O2)
- **Build parancs:** `scripts/build_nfp_cgal_probe.sh`

### T07 external_json mód
- **Bináris:** `rust/nesting_engine/target/release/nfp_correctness_benchmark`
- **Build ideje:** 1.44s (incremental)
- **Módosított fájl:** `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs`

---

## 3. Létrehozott fájlok

```
tools/nfp_cgal_probe/
  CMakeLists.txt                          # CMake config (header-only CGAL)
  src/main.cpp                            # CGAL Minkowski sum implementation
  build/nfp_cgal_probe                   # Binary (1.3MB)

scripts/
  build_nfp_cgal_probe.sh               # CMake + build script
  smoke_nfp_cgal_probe_lv8.sh           # Smoke test runner

rust/nesting_engine/src/bin/
  nfp_correctness_benchmark.rs           # MODIFIED: external_json support added

tmp/reports/nfp_cgal_probe/
  lv8_pair_01.json                       # CGAL output
  lv8_pair_02.json                       # CGAL output
  lv8_pair_03.json                       # CGAL output
```

---

## 4. Futtatott parancsok

### Build
```bash
scripts/build_nfp_cgal_probe.sh
# → tools/nfp_cgal_probe/build/nfp_cgal_probe

cargo build --release --bin nfp_correctness_benchmark
# → rust/nesting_engine/target/release/nfp_correctness_benchmark
```

### Smoke test (CGAL only)
```bash
scripts/smoke_nfp_cgal_probe_lv8.sh
# → Mindhárom LV8 pair sikeres
```

### T07 correctness validation
```bash
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/lv8_pair_01.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 \
  --output-json
# → PASS, FP=0, FN=0
# (ugyanez pair_02 és pair_03-ra is)
```

---

## 5. LV8 Pair eredmények

### CGAL probe output

| pair_id | sidecar_status | runtime_ms | output_outer_vertices | output_holes |
|---------|---------------|------------|----------------------|---------------|
| lv8_pair_01 | success | 200.24 | 776 | 0 |
| lv8_pair_02 | success | 118.21 | 786 | 0 |
| lv8_pair_03 | success | 118.00 | 324 | 0 |

### T07 correctness validator (external_json mode)

| pair_id | T07 verdict | FP_rate | FN_rate | boundary_mm | notes |
|---------|-------------|---------|---------|-------------|-------|
| lv8_pair_01 | PASS | 0.0 | 0.0 | 0.0 | exact match |
| lv8_pair_02 | PASS | 0.0 | 0.0 | 0.0 | exact match |
| lv8_pair_03 | PASS | 0.0 | 0.0 | 0.0 | exact match |

---

## 6. CGAL runtime megjegyzések

- CGAL 5.6 `Minkowski_sum_by_reduced_convolution_2` alacsonyabb vertex-számú párokra gyors (118-200ms)
- Mindhárom LV8 pair outer-only (nincs lyuk a kimenetben)
- A probe NEM támogatja a holes_t kezelést — ez explicit `HOLES_NOT_SUPPORTED_BY_PROBE_V1` státuszként jelenik meg, ha holes_l lenne
- Scale policy: 1mm = 1_000_000 egység, `CGAL::Epick` kernel, `CGAL::to_double` + `llround` a kerekítéshez

---

## 7. T07 external_json implementáció

A `--nfp-source external_json --nfp-json <path>` mód:

1. Beolvassa a CGAL probe JSON outputját
2. Validálja a `nfp_cgal_probe_result_v1` schema mezőt
3. Ellenőrzi a `status == "success"` feltételt
4. Parse-olja az `outer_i64` tömböt → `Vec<Point64>`
5. Scale-konverzió: `x * 1_000_000 / scale`
6. Holes: explicit `HOLES_NOT_SUPPORTED_BY_T07` note, ha vannak lyukak
7. Sample-alapú correctness: 1000 inside + 1000 outside + 200 boundary

**Holes policy:** A T07 validator jelenleg NEM támogatja a holes NFP-t. Ha a CGAL probe holes_i64-t ad vissza, az validator csak az outer correctness-et ellenőrzi, és a notes mezőben jelzi: `HOLES_NOT_SUPPORTED_BY_T07: outer-only correctness check`.

---

## 8. Blocker

**Nincs blocker a T05b scope-jában.**

A CGAL probe és a T07 external_json mód is működik. Az alábbi megjegyzések fontosak a jövőbeli munkához:

- **CGAL nem megy production-be:** GPL licenc miatt nem Docker-image, nem worker runtime
- **Holes támogatás hiányzik:** Mind a probe (v1), mind a T07 validator csak outer polygon-t kezel
- **Scale konverzió:** A CGAL i64 output skálázódik a fixture 1mm=1_000_000 unit konvenciójához

---

## 9. Döntés

| Komponens | Működik? | Következő javítandó pont |
|-----------|----------|--------------------------|
| CGAL probe (nfp_cgal_probe) | **Igen** | Holes támogatás hozzáadása |
| T07 external_json validator | **Igen** | Holes NFP correctness check |
| CGAL runtime (3 LV8 pair) | **Igen** | Nagyobb vertex-számú párok (Lv8_11612_6db fail-pairs) nem teszteltek |

### CGAL probe: MŰKÖDIK
- Mindhárom LV8 pair sikeres, valós polygon output
- 0 false positive, 0 false negative

### external_json validator: MŰKÖDIK
- CGAL output parse, scale-konverzió, sample-alapú correctness
- Mindhárom pair-re PASS verdikt ad

### T08 Engine v2 integráció: NEM indult
- A feladat szigorú tiltása érvényesült: NEM lett integrálva production útvonalba

---

## 10. Következő javasolt lépés (T05c vagy T08)

1. **Holes támogatás probe v1-ben:** Ha LV8 pair-ek holes_mm mezővel jelennek meg, a probe-nak explicit hibát kellene dobnia, nem csendes üres holes_i64-t
2. **T07 holes correctness:** A validator sample-alapú ellenőrzését ki kell terjeszteni holes NFP-re is
3. **Nagyobb LV8 pair-ek tesztelése:** Lv8_11612_6db (9 holes, 520 vertices) — ez okozza a Phase 8-as union crash-t, a CGAL-nak meg kell tudnia oldani
4. **T08 Engine v2 integráció:** Csak akkor, ha a probe és validator holes-t is támogat
