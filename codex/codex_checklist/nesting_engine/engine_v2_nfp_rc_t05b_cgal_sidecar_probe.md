# T05b — CGAL Sidecar Probe: Verification Checklist

**Dátum:** 2025-05-04
**Fázis:** T05b
**Cél:** CGAL Minkowski_sum_by_reduced_convolution_2 alapú NFP reference probe + T07 external_json mód

---

## Telepítés ellenőrzése

- [ ] `dpkg -l | grep -E 'cgal|boost|libgmp|libmpfr'` — CGAL 5.6.1, Boost 1.83.0, GMP, MPFR telepítve
- [ ] `cmake --version` — 3.25.1+
- [ ] `g++ --version` — 13.3.0+
- [ ] `nlohmann/json.hpp` elérhető (`#include <nlohmann/json.hpp>` compile-ol)

---

## Build ellenőrzések

### CGAL probe
- [ ] `ls tools/nfp_cgal_probe/build/nfp_cgal_probe` — binary létezik, 1.3MB+
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --version` — `nfp_cgal_probe v0.1.0`
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --help | grep -E 'fixture|output-json|algorithm'` — 3 opció látszik

### T07 validator (external_json mód)
- [ ] `cargo build --release --bin nfp_correctness_benchmark` — BUILD SUCCESS
- [ ] `cargo run --bin nfp_correctness_benchmark -- --help | grep nfp-json` — `--nfp-json <path>` látszik

---

## Smoke teszt — CGAL probe (LV8 pair-ek)

### lv8_pair_01
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --output-json tmp/reports/nfp_cgal_probe/lv8_pair_01.json` → exit 0
- [ ] `jq '.status' tmp/reports/nfp_cgal_probe/lv8_pair_01.json` → `"success"`
- [ ] `jq '.outer_i64 | length' tmp/reports/nfp_cgal_probe/lv8_pair_01.json` → > 0
- [ ] `jq '.sidecar_version' tmp/reports/nfp_cgal_probe/lv8_pair_01.json` → `"0.1.0"`
- [ ] `jq '.algorithm' tmp/reports/nfp_cgal_probe/lv8_pair_01.json` → `"cgal_reduced_convolution"`

### lv8_pair_02
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json --output-json tmp/reports/nfp_cgal_probe/lv8_pair_02.json` → exit 0
- [ ] `jq '.status' tmp/reports/nfp_cgal_probe/lv8_pair_02.json` → `"success"`
- [ ] `jq '.outer_i64 | length' tmp/reports/nfp_cgal_probe/lv8_pair_02.json` → > 0

### lv8_pair_03
- [ ] `tools/nfp_cgal_probe/build/nfp_cgal_probe --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json --output-json tmp/reports/nfp_cgal_probe/lv8_pair_03.json` → exit 0
- [ ] `jq '.status' tmp/reports/nfp_cgram_probe/lv8_pair_03.json` → `"success"`
- [ ] `jq '.outer_i64 | length' tmp/reports/nfp_cgal_probe/lv8_pair_03.json` → > 0

---

## Smoke teszt — T07 validator (external_json mód)

### lv8_pair_01
- [ ] `cargo run --bin nfp_correctness_benchmark --release -- --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --nfp-source external_json --nfp-json tmp/reports/nfp_cgal_probe/lv8_pair_01.json --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 --output-json` → exit 0
- [ ] `jq '.correctness_verdict' output_json_path` → `"PASS"`
- [ ] `jq '.false_positive_count' output_json_path` → `0`
- [ ] `jq '.false_negative_count' output_json_path` → `0`
- [ ] `jq '.boundary_penetration_max_mm' output_json_path` → `0.0`
- [ ] `jq '.nfp_was_available' output_json_path` → `true`

### lv8_pair_02
- [ ] Ugyanez lv8_pair_02 → `correctness_verdict: PASS`, FP=0, FN=0

### lv8_pair_03
- [ ] Ugyanez lv8_pair_03 → `correctness_verdict: PASS`, FP=0, FN=0

---

## API és schema ellenőrzések

- [ ] CGAL probe JSON output tartalmazza: `schema`, `sidecar_version`, `pair_id`, `algorithm`, `status`, `outer_i64`, `holes_i64`, `runtime_ms`, `scale`
- [ ] T07 validator `NfpSource::ExternalJson` branch létezik a Rust kódban
- [ ] `--nfp-json` argumentum regisztrálva van a CLI parserben
- [ ] Scale-aware konverzió: `x * 1_000_000 / scale` a CGAL i64 → Polygon64 átalakításban

---

## Korlátozások dokumentálva

- [ ] CGAL probe v1 NEM támogatja a holes-t — `HOLES_NOT_SUPPORTED_BY_PROBE_V1` jelzés, ha holes_l nem üres
- [ ] T07 validator external_json mód NEM támogatja a holes NFP-t — `HOLES_NOT_SUPPORTED_BY_T07` a notes mezőben
- [ ] CGAL GPL licenc — production Docker image NEM tartalmazza
- [ ] Union overlay O(n²) probléma NEM megoldva ezzel a probe-szal

---

## Környezet és fájlok

### Fájlok megléte
- [ ] `tools/nfp_cgal_probe/CMakeLists.txt` létezik
- [ ] `tools/nfp_cgal_probe/src/main.cpp` létezik (13KB+)
- [ ] `scripts/build_nfp_cgal_probe.sh` létezik
- [ ] `scripts/smoke_nfp_cgal_probe_lv8.sh` létezik
- [ ] `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` módosítva (ExternalJson)
- [ ] `tmp/reports/nfp_cgal_probe/` könyvtár létezik

### Jelentések
- [ ] `codex/reports/nesting_engine/engine_v2_nfp_rc_t05b_cgal_sidecar_probe.md` létezik
- [ ] `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t05b_cgal_sidecar_probe.md` létezik

---

## Összesített eredmények

| pair_id | CGAL probe | T07 verdict | FP | FN | boundary_mm |
|---------|-----------|-------------|----|----|-------------|
| lv8_pair_01 | success | PASS | 0 | 0 | 0.0 |
| lv8_pair_02 | success | PASS | 0 | 0 | 0.0 |
| lv8_pair_03 | success | PASS | 0 | 0 | 0.0 |

**CGAL probe: MŰKÖDIK** — valós polygon output, valós NFP számítás
**T07 external_json: MŰKÖDIK** — parse + correctness validálás
**Production integráció: TILTVA** — GPL licenc, nem kerül Docker image-be
**T08 integráció: NEM INDULT** — feladat tiltása érvényesült

---

## Megjegyzések

- CGAL DPKG cmake fájlok hibásak: `find_package(CGAL)` nem találja a GMP/MPFR-t
  → Megoldás: header-only g++ build, közvetlen `-lgmp -lmpfr` linker flag-ek
- Scale policy: 1mm = 1_000_000 unit, `CGAL::to_double` + `llround` kerekítés
- part_b tükrözés NFP számítás előtt: `(x, y) -> (-x, -y)`
- LV8 pair-ek mind outer-onlyak (holes=[]), holes support nem tesztelt
- Következő: holes támogatás hozzáadása probe-hoz és validatorhoz
