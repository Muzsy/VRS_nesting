# VRS Nesting Codex Task — NFP Nesting Engine: Polygon pipeline (nominális → inflated)
TASK_SLUG: nesting_engine_polygon_pipeline

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `rust/nesting_engine/src/geometry/offset.rs` — `inflate_part()` API, `OffsetError` (F1-1 output)
6. `rust/nesting_engine/src/geometry/scale.rs` — `SCALE`, `mm_to_i64()`, `i64_to_mm()` (F1-1 output)
7. `rust/nesting_engine/src/geometry/types.rs` — `Point64`, `Polygon64` (F1-1 output)
8. `rust/nesting_engine/src/main.rs` — meglévő CLI struktúra (F1-1 output)
9. `docs/nesting_engine/tolerance_policy.md` — CCW/CW irány, touching policy (F1-1 output)
10. `docs/nesting_engine/io_contract_v2.md` — nominális mezőnevek (F1-2 output)
11. `docs/nesting_engine/json_canonicalization.md` — determinism referencia (F1-2 output)
12. `canvases/nesting_engine/nesting_engine_polygon_pipeline.md` — feladat specifikációja
13. `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_polygon_pipeline.yaml` — lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

JSON stdio alapú inflate pipeline kiépítése a Rust kernelben. Az `inflate-parts`
subcommand stdin-ről fogad nominális polygon JSON-t, meghívja az F1-1-ben megírt
`inflate_part()` függvényt, és stdout-ra írja az inflated geometriát.

Deliverable-ök:
- `rust/nesting_engine/src/io/` — pipeline IO struktúrák
- `rust/nesting_engine/src/geometry/pipeline.rs` — `run_inflate_pipeline()`
- `inflate-parts` subcommand a Rust binárisban
- Unit tesztek: ok, hole_collapsed, determinizmus esetek
- `docs/nesting_engine/architecture.md` — nominális vs. inflated szabály dokumentálva
- Poc JSON fájlok a smoke teszthez
- `scripts/check.sh` sorrend-korrekció (nesting_engine build a vrs_solver UTÁN)

## 3) Nem cél

- Baseline placer (F1-4 task)
- NFP számítás (F2-x task-ok)
- Python DXF importer logikájának változtatása
- `determinism_hash` (RFC 8785 / JCS) implementálása — az az F1-4 feladata;
  itt csak `diff`-alapú determinizmus smoke teszt szükséges

---

## 4) Architekturális invariáns — soha nem szeghet meg

```
A solver feasibility engine CSAK inflated geometriával dolgozik.
DXF export MINDIG nominális geometriából történik.
Ez a különbség soha nem keveredhet.
```

Ez a szabály az `architecture.md`-ben dokumentálandó, és a kód nem sértheti meg.

---

## 5) Munkaszabályok (nem alkuképes)

- **Outputs szabály:** csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel
  az adott YAML step `outputs` listájában.
- **Valós repó elv:** nem találhatsz ki fájlokat, API-kat, konstansokat — az F1-1
  outputjaiból kell dolgoznod, azokat nem írhatod felül (csak bővítheted).
- **Gate csak wrapperrel:** ne rögtönözz párhuzamos check parancsokat.
- **vrs_solver érintetlen:** a regressziós baseline nem változhat.

---

## 6) check.sh sorrend-korrekció (kötelező ebben a taskban)

Az F1-1 óta a `nesting_engine` build a `vrs_solver` build **előtt** szerepel a
`check.sh`-ban — ez ellentétes a deklarált sorrenddel. Ebben a taskban a
`check.sh` amúgy is módosul (ha szükséges), ezért itt korrigáljuk.

**Elvárt sorrend a check.sh-ban:**
```
1. vrs_solver build   ← kisebb sorszám
2. nesting_engine build  ← nagyobb sorszám
```

Ellenőrzés: `grep -n "nesting_engine\|vrs_solver" scripts/check.sh`

---

## 7) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit **sorrendben**:

```
codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_polygon_pipeline.yaml
```

---

## 8) Kötelező gate (a végén, egyszer)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline.md
```

A gate előtt ellenőrizd manuálisan:
```bash
# Unit tesztek
cargo test --manifest-path rust/nesting_engine/Cargo.toml

# vrs_solver regresszió
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml

# Pipeline smoke determinizmus
cat poc/nesting_engine/pipeline_smoke_input.json \
  | ./rust/nesting_engine/target/release/nesting_engine inflate-parts \
  > /tmp/pipe_out1.json
cat poc/nesting_engine/pipeline_smoke_input.json \
  | ./rust/nesting_engine/target/release/nesting_engine inflate-parts \
  > /tmp/pipe_out2.json
diff /tmp/pipe_out1.json /tmp/pipe_out2.json   # üresnek kell lennie

# check.sh sorrend ellenőrzés
grep -n "nesting_engine\|vrs_solver" scripts/check.sh
# vrs_solver sora < nesting_engine sora
```

---

## 9) Elvárt kimenetek

**Új fájlok:**
- `rust/nesting_engine/src/io/mod.rs`
- `rust/nesting_engine/src/io/pipeline_io.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `docs/nesting_engine/architecture.md`
- `poc/nesting_engine/pipeline_smoke_input.json`
- `poc/nesting_engine/pipeline_smoke_expected.json`
- `codex/codex_checklist/nesting_engine/nesting_engine_polygon_pipeline.md`
- `codex/reports/nesting_engine/nesting_engine_polygon_pipeline.md`
- `codex/reports/nesting_engine/nesting_engine_polygon_pipeline.verify.log`

**Módosuló fájlok:**
- `rust/nesting_engine/src/main.rs` — `inflate-parts` subcommand
- `rust/nesting_engine/src/geometry/mod.rs` — `pub mod pipeline`
- `scripts/check.sh` — sorrend-korrekció

**Érintetlen (ellenőrizd):**
- `rust/vrs_solver/` — egyetlen fájl sem változik
- `vrs_nesting/dxf/importer.py` — nem változik
- `docs/nesting_engine/io_contract_v2.md` — nem változik
- `docs/nesting_engine/json_canonicalization.md` — nem változik

---

## 10) Elfogadási kritériumok

1. `cargo test --manifest-path rust/nesting_engine/Cargo.toml` — PASS (pipeline tesztek benne)
2. `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` — PASS (regresszió)
3. Pipeline ok eset: `rect_100x50` inflated bbox ≥ `102×52mm` (delta = 5.1mm)
4. Pipeline hole_collapsed eset: 2×2mm lyuk 5mm delta után → status=`hole_collapsed`, nem crash
5. Pipeline determinizmus: `diff /tmp/pipe_out1.json /tmp/pipe_out2.json` — üres
6. `grep -n "nesting_engine\|vrs_solver" scripts/check.sh` — vrs_solver sor < nesting_engine sor
7. `./scripts/verify.sh` gate — PASS