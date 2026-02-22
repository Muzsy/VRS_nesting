# canvases/nesting_engine/nesting_engine_baseline_placer.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_baseline_placer.md`
> **TASK_SLUG:** `nesting_engine_baseline_placer`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — Baseline placer + Python runner + benchmark harness

## 🎯 Funkció

Egyszerű, determinisztikus BLF-jellegű (Bottom-Left Fill) construction placer
megvalósítása, Python runner adapter, és benchmark harness a Fázis 1 kiindulási
értékhez. Ez az utolsó Fázis 1 task — a végén van egy futó, mérhető,
determinisztikus nesting rendszer, amelyhez képest a Fázis 2 NFP-alapú motor
javulását mérni fogjuk.

**Deliverable-ök:**
- `rust/nesting_engine/src/feasibility/` — `can_place()`: AABB broad-phase + polygon narrow-phase
- `rust/nesting_engine/src/placement/blf.rs` — BLF construction placer
- `rust/nesting_engine/src/multi_bin/greedy.rs` — multi-sheet iteratív stratégia
- `rust/nesting_engine/src/main.rs` — `nest` subcommand (JSON in → JSON out, io_contract_v2)
- `vrs_nesting/runner/nesting_engine_runner.py` — Python adapter (vrs_solver_runner.py mintájára)
- `poc/nesting_engine/baseline_benchmark.md` — baseline mérési eredmény a poc fixture-ökön
- `determinism_hash` implementálása a JSON outputban (RFC 8785 / JCS, json_canonicalization.md szerint)

**Nem cél:**
- NFP számítás (F2-x task-ok)
- Simulated Annealing (F2-4 task)
- Python DXF importer módosítása
- `vrs_solver` bármilyen módosítása
- A meglévő `vrs_nesting/cli.py` `run` subcommand módosítása (az a vrs_solver-hez kapcsolódik)

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Létrehozandó (új):**
- `rust/nesting_engine/src/feasibility/mod.rs`
- `rust/nesting_engine/src/feasibility/aabb.rs` — AABB broad-phase
- `rust/nesting_engine/src/feasibility/narrow.rs` — polygon narrow-phase (Clipper/i_overlay)
- `rust/nesting_engine/src/placement/mod.rs`
- `rust/nesting_engine/src/placement/blf.rs` — BLF placer + rács-alapú candidate generálás
- `rust/nesting_engine/src/multi_bin/mod.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs` — iteratív multi-sheet stratégia
- `rust/nesting_engine/src/export/mod.rs`
- `rust/nesting_engine/src/export/output_v2.rs` — io_contract_v2 szerinti JSON output + determinism_hash
- `vrs_nesting/runner/nesting_engine_runner.py` — Python adapter
- `poc/nesting_engine/baseline_benchmark.md` — baseline mérési eredmény

**Módosuló (meglévő):**
- `rust/nesting_engine/src/main.rs` — `nest` subcommand hozzáadása
- `rust/nesting_engine/src/lib.rs` — új modulok exportálása (ha van lib.rs; ha nincs, main.rs bővül)
- `scripts/check.sh` — nesting_engine runner smoke: `nesting_engine_runner.py` alapfutás

**Nem módosul:**
- `rust/vrs_solver/` (egyetlen fájl sem)
- `vrs_nesting/runner/vrs_solver_runner.py` (minta, nem módosítjuk)
- `vrs_nesting/cli.py` (vrs_solver pipeline — érintetlen)
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/json_canonicalization.md`

---

### `nest` subcommand — JSON stdio interface

```bash
echo '{ io_contract_v2 input JSON }' | nesting_engine nest
```

Input: `io_contract_v2` szerinti JSON (`version`, `seed`, `time_limit_sec`, `sheet`, `parts`)
Output: `io_contract_v2` szerinti JSON (`version`, `seed`, `solver_version`, `status`, `sheets_used`, `placements`, `unplaced`, `objective`, `meta`)

**Fontos:** a `nest` subcommand az `inflate-parts`-ra épül belsőleg:
1. Input JSON-ból nominális geometriák kinyerése
2. `run_inflate_pipeline()` hívás → inflated geometria
3. BLF placer az inflated geometriával dolgozik
4. Output JSON-ban koordináták nominálisak (placement transzformáció a nominális origóra vonatkozik)
5. `meta.determinism_hash` kötelező, `json_canonicalization.md` szerint

---

### Feasibility engine: `can_place()`

```rust
/// Megmondja, hogy az adott inflated polygon elhelyezhető-e a megadott pozícióban.
/// Feltételek:
///   1. Tábla containment: az inflated polygon teljesen a bin_polygon belsejében van
///   2. 0 overlap: nem metszi az already_placed inflated polygonok egyikét sem
///   3. Touching = infeasible (TOUCH_TOL = 1 µm alapján)
pub fn can_place(
    candidate: &Polygon64,           // inflated part polygon
    position: Point64,               // elhelyezési pozíció (eltolás)
    rotation_deg: i32,               // forgatás fokban
    bin: &Polygon64,                 // tábla polygon (inflated határ)
    placed: &[PlacedPart],           // már elhelyezett inflated polygonok
) -> bool
```

**Broad-phase (AABB):**
- Axis-Aligned Bounding Box gyors kiszűrés
- Ha az AABB-k nem metszik egymást → can_place = true (narrow-phase kihagyva)
- Ha metszik → narrow-phase szükséges

**Narrow-phase:**
- Polygon containment: az `i_overlay` vagy polygon pont-in-polygon tesztelés
- Polygon overlap: polygon intersection check
- Touching policy: `TOUCH_TOL = 1` alapján (pontosan érintkezők = infeasible)

**Megjegyzés:** `jagua-rs` és `rstar` dependency a Cargo.toml-ban már megvan a
`vrs_solver`-ből — **ellenőrizd** hogy a `nesting_engine/Cargo.toml`-ban is
szerepelnek-e, és ha igen, ugyanolyan pinned verzióban. Ha nem, add hozzá.

---

### BLF placer: rács-alapú candidate generálás

```rust
/// Egyszerű BLF-jellegű placer: balról jobbra, alulról felfelé
/// grid_step_mm: a rács lépésköze (ajánlott: 1.0mm)
pub fn blf_place(
    parts_inflated: &[InflatedPart],  // rendezett lista (pl. területcsökkeno sorrend)
    bin: &Polygon64,
    grid_step_mm: f64,
    seed: u64,
    time_limit_sec: u64,
) -> PlacementResult
```

**Algoritmus:**
1. Parts rendezése: csökkenő területi sorrend (determinisztikus: azonos terület → id szerint)
2. Minden part-ra: végigmegy a rács candidate pozíciókon (bal-alsó saroktól jobbra-felfelé)
3. Minden candidate pozíción minden allowed rotation-re: `can_place()` check
4. Első feasible pozíció + rotáció = placement
5. Ha nincs feasible pozíció: part → `unplaced` lista, `TIME_LIMIT_EXCEEDED` vagy `PART_NEVER_FITS_SHEET`
6. Time limit ellenőrzés minden part elhelyezési ciklus előtt

**Determinizmus:**
- Rács traversal sorrendje rögzített (X-major: balról jobbra, alulról felfelé)
- Rotation sorrend rögzített: `allowed_rotations_deg` eredeti sorrendjében
- Seed: a Rust `rand` crate seeded RNG-je, ha szükséges (BLF-nél nem kell RNG, de a seed az output hash-be bele kell menjen)

---

### Multi-sheet greedy stratégia

```rust
pub fn greedy_multi_sheet(
    parts_inflated: &[InflatedPart],
    bin_spec: &BinSpec,  // width, height, kerf, margin
    grid_step_mm: f64,
    seed: u64,
    time_limit_sec: u64,
) -> MultiSheetResult
```

**Algoritmus:**
1. Első tábla: BLF placer futtatása az összes part-ra
2. Ami nem fért el (unplaced) → következő táblára kerül
3. Ismétlés amíg minden part elhelyezve vagy time limit lejár
4. `sheets_used` = felhasznált táblák száma
5. `unplaced` = ami time limit után sem fért el

---

### `determinism_hash` implementálása

Az `io_contract_v2.md` szerint a `meta.determinism_hash` kötelező mező.
Implementálása a `json_canonicalization.md` normative dokumentum alapján:

```
hash_view = {
  "schema_version": "nesting_engine.hash_view.v1",
  "placements": [
    { "sheet_id": "S<n>", "part_id": "...", "rotation_deg": N,
      "x_scaled_i64": round(x_mm * 1_000_000),
      "y_scaled_i64": round(y_mm * 1_000_000) }
  ]  // sorted by (sheet_id, part_id, rotation_deg, x_scaled_i64, y_scaled_i64)
}
determinism_hash = "sha256:" + SHA-256(UTF-8(JCS(hash_view))).hex()
```

**Rust implementáció:**
- JCS (RFC 8785) Rust crate: [`json-canon`](https://crates.io/crates/json-canon) vagy `serde_json` + manuális key-sort
- Sorting: `placements` tömböt a fenti tuple alapján rendezd, majd JCS serialize
- SHA-256: `sha2` crate

**Ellenőrizd** hogy a `json-canon` és `sha2` crate-ek elérhetők-e a crates.io-n,
és pineld be a verziókat (pl. `json-canon = "=X.Y.Z"`, `sha2 = "=X.Y.Z"`).

---

### Python runner: `nesting_engine_runner.py`

A `vrs_solver_runner.py` mintájára, de az `io_contract_v2` inputot és outputot kezeli.

```bash
python3 -m vrs_nesting.runner.nesting_engine_runner \
  --input poc/nesting_engine/sample_input_v2.json \
  --output runs/<run_id>/nesting_output.json \
  --seed 42 \
  --time-limit 30
```

**Implementációs elvek (`vrs_solver_runner.py` mintájára):**
- Binary resolution: `--nesting-engine-bin` flag → `NESTING_ENGINE_BIN` env → `PATH` lookup `nesting_engine`
- Subprocess: stdin-re írja az input JSON-t, stdout-ból olvassa az output JSON-t
  (eltérés a vrs_solver_runner-től, ami fájlokon keresztül kommunikál)
- Meta artifact: `runner_meta.json` a run könyvtárban (run_id, started_at, elapsed_sec,
  input_sha256, output_sha256, return_code, solver_version)
- stdout: kizárólag a run_dir útvonalat írja ki
- stderr: diagnosztika
- Non-zero exit: `NestingEngineRunnerError` kivétel
- Output SHA-256 ellenőrzés: ha az output JSON nem valid → diagnosztikus hiba

**Run könyvtár struktúra:**
```
runs/<run_id>/
  nesting_input.json    ← input snapshot
  nesting_output.json   ← solver output
  runner_meta.json      ← meta artifact
```

---

### Benchmark harness

A `poc/nesting_engine/baseline_benchmark.md` tartalmazza a Fázis 1 baseline mérési
eredményt a `poc/nesting_engine/sample_input_v2.json` fixture-ön:

```markdown
## Baseline mérési eredmény (F1-4, BLF placer)

| Fixture | sheets_used | utilization_pct | elapsed_sec | seed |
|---|---|---|---|---|
| sample_input_v2.json | N | X% | Y | 42 |

Mérési feltételek: grid_step_mm=1.0, time_limit_sec=30, seed=42
```

Ez az a szám, amelyhez képest az F2-x NFP motor javulása mérhető lesz.

---

### Gate: 0 overlap, 0 out-of-bounds ellenőrzés

Az F1-4 elfogadásához a `can_place()` invariánsnak igaznak kell lennie
**minden** elhelyezett partra a poc fixture outputjában:

```bash
# Python validátor (meglévő solution_validator.py bővítve vagy új script)
python3 scripts/validate_nesting_solution.py \
  --input poc/nesting_engine/sample_input_v2.json \
  --output runs/<run_id>/nesting_output.json
# Elvárt: 0 overlap, 0 out-of-bounds
```

Ha nincs még `validate_nesting_solution.py` v2-kompatibilis módban,
egy inline Python one-liner ellenőrzés is elfogadható a report-ban:
- Minden placement `x_mm >= margin_mm` és `x_mm + part_bbox_x <= width_mm - margin_mm`
- Hasonlóan Y-ra
- Placements nem metszik egymást (bounding box szinten elegendő a baseline-hoz)

---

### Kockázat + mitigáció + rollback

| Kockázat | Mitigáció | Rollback |
|---|---|---|
| Rács-alapú candidate generálás lassú 500+ példánynál | `time_limit_sec` kötelező; time limit lejáratán `partial` status és `TIME_LIMIT_EXCEEDED` az unplaced-ben | Rácslépés növelése (grid_step_mm paraméter) |
| `determinism_hash` JCS crate nem elérhető / kompatibilitási probléma | Fallback: manuális key-sortos JSON serialize + sha256 (nincs külső JCS crate) | A hash placeholder marad, F3-4 hardening task véglegesíti |
| Python runner subprocess stdin/stdout deadlock | `communicate()` helyett `Popen` + timeout kezelés, ahogy a vrs_solver_runner.py is csinálja | subprocess.run timeout fallback |
| `jagua-rs`/`rstar` nesting_engine Cargo.toml-ból hiányzik | Felderítési lépés: Cargo.toml elolvasása → ha hiányzik, hozzáadás a vrs_solver Cargo.toml-ból kimásolva | Dependency eltávolítása, pure AABB marad |

---

## ✅ Pipálható DoD lista

### Felderítés
- [ ] `AGENTS.md` elolvasva
- [ ] `docs/codex/overview.md` elolvasva
- [ ] `docs/codex/yaml_schema.md` elolvasva
- [ ] `docs/codex/report_standard.md` elolvasva
- [ ] `rust/nesting_engine/src/geometry/pipeline.rs` — `run_inflate_pipeline()` API ismert
- [ ] `rust/nesting_engine/src/io/pipeline_io.rs` — `PipelineRequest`, `PipelineResponse` struktúrák ismertek
- [ ] `rust/nesting_engine/Cargo.toml` — meglévő dependency-k azonosítva (`jagua-rs`, `rstar` szerepel-e?)
- [ ] `docs/nesting_engine/io_contract_v2.md` — input/output séma ismert
- [ ] `docs/nesting_engine/json_canonicalization.md` — `determinism_hash` szabály ismert
- [ ] `vrs_nesting/runner/vrs_solver_runner.py` — runner minta megvizsgálva (subprocess, meta artifact, binary resolution)
- [ ] `poc/nesting_engine/sample_input_v2.json` — fixture ismert

### Implementáció — Rust feasibility + placer
- [ ] `rust/nesting_engine/src/feasibility/mod.rs` létrehozva
- [ ] `rust/nesting_engine/src/feasibility/aabb.rs` — AABB broad-phase
- [ ] `rust/nesting_engine/src/feasibility/narrow.rs` — polygon narrow-phase
- [ ] `rust/nesting_engine/src/placement/mod.rs` létrehozva
- [ ] `rust/nesting_engine/src/placement/blf.rs` — BLF placer, rács traversal, time limit
- [ ] `rust/nesting_engine/src/multi_bin/mod.rs` létrehozva
- [ ] `rust/nesting_engine/src/multi_bin/greedy.rs` — iteratív multi-sheet
- [ ] `rust/nesting_engine/src/export/mod.rs` létrehozva
- [ ] `rust/nesting_engine/src/export/output_v2.rs` — `determinism_hash` + io_contract_v2 JSON
- [ ] `rust/nesting_engine/src/main.rs` — `nest` subcommand
- [ ] `cargo test` PASS (can_place unit tesztek, BLF determinizmus teszt)

### Implementáció — Python runner
- [ ] `vrs_nesting/runner/nesting_engine_runner.py` létrehozva
- [ ] Binary resolution: `--nesting-engine-bin` → `NESTING_ENGINE_BIN` → PATH
- [ ] `runner_meta.json` artifact: run_id, input_sha256, output_sha256, elapsed_sec, solver_version
- [ ] Non-zero exit kezelés: `NestingEngineRunnerError`

### Poc és benchmark
- [ ] `nesting_engine nest` sikeresen fut a `sample_input_v2.json`-on
- [ ] Output valid io_contract_v2 JSON: `meta.determinism_hash` nem placeholder
- [ ] 0 overlap, 0 out-of-bounds ellenőrzés PASS
- [ ] Determinizmus: két egymást követő futás azonos `determinism_hash`-t ad
- [ ] `poc/nesting_engine/baseline_benchmark.md` létrehozva valós mérési eredménnyel

### Gate
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer.md` PASS

---

## 🧪 Tesztállapot

**Kötelező gate:**
```
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer.md
```

**Task-specifikus ellenőrzések:**
```bash
# Rust unit tesztek
cargo test --manifest-path rust/nesting_engine/Cargo.toml

# Build
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml  # regresszió

# Nest futás a poc fixture-ön
cat poc/nesting_engine/sample_input_v2.json \
  | ./rust/nesting_engine/target/release/nesting_engine nest \
  > /tmp/baseline_out.json
python3 -m json.tool /tmp/baseline_out.json > /dev/null  # valid JSON

# Determinizmus
cat poc/nesting_engine/sample_input_v2.json \
  | ./rust/nesting_engine/target/release/nesting_engine nest \
  > /tmp/baseline_out2.json
python3 -c "
import json
a = json.load(open('/tmp/baseline_out.json'))
b = json.load(open('/tmp/baseline_out2.json'))
assert a['meta']['determinism_hash'] == b['meta']['determinism_hash'], 'HASH MISMATCH'
assert a['meta']['determinism_hash'] != 'sha256:placeholder', 'HASH IS PLACEHOLDER'
print('determinism_hash OK:', a['meta']['determinism_hash'])
"

# 0 overlap / 0 out-of-bounds (bbox szintű ellenőrzés)
python3 -c "
import json
inp = json.load(open('poc/nesting_engine/sample_input_v2.json'))
out = json.load(open('/tmp/baseline_out.json'))
sheet = inp['sheet']
for p in out['placements']:
    assert p['x_mm'] >= sheet['margin_mm'], f'out of bounds: {p}'
    assert p['y_mm'] >= sheet['margin_mm'], f'out of bounds: {p}'
print('0 out-of-bounds OK')
"

# Python runner
python3 -m vrs_nesting.runner.nesting_engine_runner \
  --input poc/nesting_engine/sample_input_v2.json \
  --seed 42 \
  --time-limit 30
```

**Elfogadási kritériumok:**
- `cargo test` PASS (legalább: can_place ok eset, can_place overlap eset, BLF determinizmus)
- `nest` subcommand fut és valid io_contract_v2 JSON-t ad
- `meta.determinism_hash` nem placeholder, két futás azonos hash-t ad
- 0 overlap, 0 out-of-bounds a poc fixture-ön
- `baseline_benchmark.md` valós mérési eredménnyel megvan

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

**Szülő dokumentum:**
- `canvases/nesting_engine/nesting_engine_backlog.md` — F1-4 task

**Előző task outputjai — elolvasandó implementáció előtt:**
- `rust/nesting_engine/src/geometry/pipeline.rs` — `run_inflate_pipeline()` (F1-3)
- `rust/nesting_engine/src/io/pipeline_io.rs` — `PipelineRequest`, `PipelineResponse` (F1-3)
- `rust/nesting_engine/src/main.rs` — meglévő CLI (F1-1, F1-3)
- `docs/nesting_engine/io_contract_v2.md` — io séma (F1-2)
- `docs/nesting_engine/json_canonicalization.md` — `determinism_hash` (F1-2)
- `docs/nesting_engine/tolerance_policy.md` — SCALE, TOUCH_TOL (F1-1)
- `docs/nesting_engine/architecture.md` — nominális vs. inflated szabály (F1-3)

**Minta (nem módosítjuk):**
- `vrs_nesting/runner/vrs_solver_runner.py` — runner architektúra minta

**Következő task (F2-1):**
- `canvases/nesting_engine/nfp_computation_convex.md`

**Codex workflow:**
- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`