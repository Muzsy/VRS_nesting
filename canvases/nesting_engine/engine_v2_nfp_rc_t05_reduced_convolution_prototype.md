# Engine v2 NFP RC — T05 Reduced Convolution Prototype

## Cél
Kipróbálni a reduced convolution / Minkowski irányt a T01 problémás partpárokon.
Első döntési pont: Rust prototype elegendő-e, vagy szükséges CGAL sidecar.
A task bizonyítja, hogy az új megközelítés egyáltalán futtatható az LV8 fixture-ökön,
és ha van output, az összevethető a T04 baseline-nal.

## Miért szükséges
A jelenlegi orbit-alapú concave NFP (concave.rs) fragment explosion módban fail-el a
nagy konkáv partokon. A reduced convolution / Minkowski approach alternatív algoritmus:
a geometriai összegzés elvén alapul, nem kell konvex dekompozíció. Ha ez az irány
működik, a T01 fixture-ökre nem lesz timeout. Ez a task az első kísérleti implementáció.

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `rust/nesting_engine/src/nfp/mod.rs` — NfpError enum (az új error típushoz minta)
- `rust/nesting_engine/src/nfp/concave.rs` — jelenlegi NFP flow (megértéshez)
- `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64
- `rust/nesting_engine/src/geometry/cleanup.rs` — T03 output (cleanup pipeline)
- `rust/nesting_engine/src/geometry/simplify.rs` — T03 output (simplification)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` — T01 fixture
- `docs/nesting_engine/geometry_preparation_contract_v1.md` — T02 contract

### Létrehozandó:
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` — RC NFP modul
- `rust/nesting_engine/src/bin/nfp_rc_prototype_benchmark.rs` — prototype mérő bin

### Módosítandó:
- `rust/nesting_engine/src/nfp/mod.rs` — `pub mod reduced_convolution;` hozzáadása

## Nem célok / scope határok
- Nem kell a jelenlegi concave.rs-t törölni vagy módosítani.
- Nem kell teljesen kész, production-ready algoritmust implementálni — prototype elég.
- Ha a teljes algoritmus meghaladja a scope-ot: `RcNfpError::NotImplemented` explicit.
- Nem kell CGAL sidecar-t implementálni (de a döntést dokumentálni kell).
- Nem kell a nfp_placer.rs-t módosítani (az T08 feladata).

## Architektúra döntési protokoll

### A. CGAL sidecar ellenőrzés
```bash
ls tools/nfp_cgal_probe/ 2>/dev/null && echo "CGAL probe létezik" || echo "CGAL probe nincs"
which cmake && cmake --version && echo "CMake elérhető" || echo "CMake nem elérhető"
pkg-config --exists cgal && echo "CGAL elérhető" || echo "CGAL nem elérhető"
```

### B. Döntési fa
- Ha CGAL elérhető ÉS tools/nfp_cgal_probe/ létezik → CGAL sidecar irányt dokumentálni a reportban, de implementálni a Rust prototype-ot is
- Ha CGAL nem elérhető → Rust prototype implementálása (ez a várható eset)

A döntést a reportban explicit rögzíteni:
```
ARCHITECTURE_DECISION: Rust prototype (CGAL not available) / CGAL sidecar (path=...)
```

## Részletes implementációs lépések

### 1. `rust/nesting_engine/src/nfp/reduced_convolution.rs` implementálása

**ReducedConvolutionOptions struct:**
```rust
#[derive(Debug, Clone)]
pub struct ReducedConvolutionOptions {
    /// mm → i64 skálázás (alapértelmezés: geometry::scale::SCALE konstans)
    pub integer_scale: i64,
    /// Minimum él hossza egységben (töredékek elhagyásához)
    pub min_edge_length_units: i64,
    /// Maximum output vertex count (biztonsági cap)
    pub max_output_vertices: usize,
    /// Ha az input cleanup szükséges-e automatikusan
    pub auto_cleanup: bool,
}

impl Default for ReducedConvolutionOptions {
    fn default() -> Self {
        Self {
            integer_scale: crate::geometry::scale::SCALE,
            min_edge_length_units: 100,
            max_output_vertices: 50_000,
            auto_cleanup: true,
        }
    }
}
```

**RcNfpError enum:**
```rust
#[derive(Debug, Clone)]
pub enum RcNfpError {
    InputTooComplex { vertex_count: usize, limit: usize },
    EmptyInput,
    /// Explicit placeholder: az algoritmus nem teljes implementáció
    NotImplemented,
    ComputationFailed(String),
    OutputExceedsCap { vertex_count: usize, cap: usize },
    CleanupFailed(String),
}
```

**RcNfpResult struct:**
```rust
#[derive(Debug, Clone)]
pub struct RcNfpResult {
    /// None ha hiba keletkezett
    pub polygon: Option<Polygon64>,
    /// Output vertex count cleanup ELŐTT
    pub raw_vertex_count: usize,
    /// Computation idő ms-ban
    pub computation_time_ms: u64,
    /// Hiba, ha volt
    pub error: Option<RcNfpError>,
    /// Algoritmus verzió (tracability)
    pub kernel_version: &'static str,
}
```

**Publikus API:**
```rust
/// Reduced convolution NFP számítás
/// part_a: a statikus alkatrész (nem fordul)
/// part_b: a mozgó alkatrész (ezt helyezzük el)
pub fn compute_rc_nfp(
    part_a: &Polygon64,
    part_b: &Polygon64,
    options: &ReducedConvolutionOptions,
) -> RcNfpResult
```

**Algoritmus implementációs irányelvek:**

Az alap reduced convolution NFP algoritmus lépései:
1. A part_b tükrözése (negálás: minden pont negálva)
2. Minkowski összeg számítása: part_a ⊕ (-part_b)
3. A Minkowski összeg az NFP

Részletes lépések:
1. **Input cleanup** (ha auto_cleanup = true): run_cleanup_pipeline a T03 modulból
2. **part_b reflection**: minden `Point64 {x, y}` → `Point64 {x: -x, y: -y}`
3. **Edge decomposition**: mindkét polygon éllistájának felépítése
4. **Convolution**: az éllista rotációs összegzése (edge convolution)
5. **Loop closing**: a konvolúciós hurkok azonosítása és zárása
6. **Output assembly**: a hurkokból Polygon64 összeállítása
7. **NotImplemented fallback**: ha bármely lépés nem implementált: `RcNfpError::NotImplemented`

**Fontos:** A `NotImplemented` explicit return — nem panic, nem silent fallback.

### 2. `rust/nesting_engine/src/bin/nfp_rc_prototype_benchmark.rs` implementálása

**Parancssori interfész:**
```
--fixture <path>      NFP pair fixture JSON fájl
--timeout-ms <N>      Timeout (default: 10000)
--compare-baseline    Ha megvan a T04 baseline a fixture-ben, összehasonlít
--output-json         JSON output
```

**stdout JSON output:**
```json
{
  "benchmark_version": "nfp_rc_prototype_v1",
  "fixture": "lv8_pair_01",
  "kernel": "reduced_convolution_v1",
  "rc_result": {
    "success": false,
    "error": "NotImplemented",
    "raw_vertex_count": 0,
    "computation_time_ms": 1,
    "kernel_version": "reduced_convolution_v1"
  },
  "comparison_to_baseline": {
    "baseline_verdict": "TIMEOUT",
    "baseline_fragment_count_a": 42,
    "baseline_fragment_count_b": 67,
    "baseline_pair_count": 2814,
    "rc_avoids_fragment_explosion": null,
    "time_ratio": null
  },
  "verdict": "NOT_IMPLEMENTED"
}
```

**verdict értékek:**
- `SUCCESS` — RC NFP sikeresen kiszámítva
- `NOT_IMPLEMENTED` — `RcNfpError::NotImplemented` (explicit, nem hiba)
- `ERROR` — egyéb hiba
- `TIMEOUT` — timeout

### 3. nfp/mod.rs módosítás

A meglévő `pub mod` sorok mellé:
```rust
pub mod reduced_convolution;
```

### 4. CGAL sidecar döntés dokumentálása

A reportban explicit szekció:
```markdown
## Architecture Decision: RC Kernel Backend

**Checked:** tools/nfp_cgal_probe/ — [FOUND/NOT FOUND]
**Checked:** cmake version — [VERSION/NOT AVAILABLE]
**Checked:** CGAL pkg-config — [FOUND/NOT FOUND]

**Decision:** Rust prototype (reason: CGAL not available / CGAL available but Rust prototype preferred for integration)

**Implication:** T06, T07, T08 a Rust prototype-ra épülnek. CGAL sidecar opció a jövőre halasztva.
```

## Adatmodell / contract változások
Új Rust modul (`reduced_convolution.rs`), új bin (`nfp_rc_prototype_benchmark.rs`).
`nfp/mod.rs` minimális módosítás (pub mod sor).

## Backward compatibility
A meglévő `concave.rs`, `convex.rs`, `cfr.rs` érintetlenek.
Az új modul `pub` de nincs integrálva a placer-be (az T08 feladata).

## Hibakódok / diagnosztikák
- `RcNfpError::NotImplemented` — explicit placeholder, NEM silent fallback
- `RcNfpError::InputTooComplex` — vertex count meghaladja a limitet
- `RcNfpError::OutputExceedsCap` — output meghaladja a max_output_vertices-t
- `RcNfpError::ComputationFailed(String)` — részletes hibaüzenet

## Tesztelési terv
```bash
# 1. Compile check
cargo check -p nesting_engine

# 2. Bin help fut
cargo run --bin nfp_rc_prototype_benchmark -- --help

# 3. T01 fixture-n lefut (NotImplemented is elfogadható)
cargo run --bin nfp_rc_prototype_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'rc_result' in d
assert 'verdict' in d
assert d['verdict'] in ('SUCCESS', 'NOT_IMPLEMENTED', 'ERROR', 'TIMEOUT')
print('PASS: verdict =', d['verdict'])
"

# 4. NotImplemented nem panic (explicit return)
cargo run --bin nfp_rc_prototype_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json 2>&1 | grep -v "^error" | python3 -c "
import json, sys; d = json.load(sys.stdin)
assert d.get('rc_result', {}).get('error') != 'panic', 'PANIC detected!'
print('No panic: OK')
"
```

## Elfogadási feltételek
- [ ] `cargo check -p nesting_engine` hibátlan
- [ ] `cargo run --bin nfp_rc_prototype_benchmark -- --help` fut
- [ ] T01 fixture-ökön lefut (akár `NOT_IMPLEMENTED` verdict-tel is)
- [ ] `RcNfpError::NotImplemented` explicit, nem silent fallback és nem panic
- [ ] Döntési pont dokumentálva a reportban (Rust prototype vs CGAL sidecar)
- [ ] A `concave.rs` érintetlen
- [ ] `nfp/mod.rs`-ben `pub mod reduced_convolution` megjelenik

## Rollback / safety notes
Additive Rust modul, nem integrálja a placer-be (az T08 feladata).
A `concave.rs` érintetlen — a meglévő NFP pipeline nem változik.

## Dependency
- T01: lv8_pair_01–03 fixture-ök
- T03: cleanup.rs, simplify.rs (auto_cleanup használja)
- T04: baseline mérések (comparison_to_baseline-hoz)
- T06 (minkowski_cleanup) depends on T05 output
