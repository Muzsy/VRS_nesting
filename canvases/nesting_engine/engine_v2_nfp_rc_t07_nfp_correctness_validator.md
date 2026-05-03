# Engine v2 NFP RC — T07 NFP Correctness Validator

## Cél
Bizonyítani, hogy az új RC NFP igazat mond az exact collision validatorhoz képest.
False positive és false negative arány mérése mintavételezéssel. A correctness
validator KÖTELEZŐ — validálatlan NFP nem fogadható el sikernek.

## Miért szükséges
Az NFP (No-Fit Polygon) pontosságának elvesztése közvetlenül gyártási hibát okoz:
- False positive NFP: az algoritmus azt mondja, hogy egy elhelyezés ütközésmentes,
  de valójában ütközés van → átfedő alkatrészek a kész munkán.
- False negative NFP: az algoritmus ütközésnek jelöl egy valid elhelyezést →
  felesleges kimaradó hely, rosszabb kihasználtság.

A correctness validator statisztikai mintavételezéssel méri mindkét típust.

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `rust/nesting_engine/src/nfp/nfp_validation.rs` — T06 output (polygon_is_valid)
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` — T05 output (compute_rc_nfp)
- `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` — T06 output (run_minkowski_cleanup)
- `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` — T01 fixture

### Olvasandó (kollizió validáció mintájához):
- `rust/nesting_engine/src/feasibility/narrow.rs` — narrow feasibility check (ha létezik)
- `rust/nesting_engine/src/feasibility/aabb.rs` — AABB kollizió check (ha létezik)

### Létrehozandó:
- `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` — correctness mérő bin

## Nem célok / scope határok
- Nem kell NFP-t számítani (a meglévő RC NFP-t teszteli, ha van output).
- Nem kell Python kódot módosítani.
- Nem kell a nfp_placer.rs-t módosítani.

## Kétszintű verdict — kötelező megkülönböztetés

A T07 task két különböző pass-szintet különböztet meg:

**`validator_infra_pass = true`:**
- A nfp_correctness_benchmark bin elkészült és fut
- A mock_exact NFP-n false_positive_rate = 0.0
- Az infrastruktúra (sampling, exact collision check, JSON output) működik
- Ez szükséges, de NEM elegendő T08 indításához

**`rc_correctness_pass = true`:**
- A tényleges RC kernel outputján fut a correctness validator
- `verdict` nem `NOT_AVAILABLE` (T05 adott valódi NFP outputot)
- `false_positive_rate = 0.0` (FAIL_FALSE_POSITIVE nem elfogadható)
- `false_negative_rate < 0.01` (PASS vagy MARGINAL)
- **Ez szükséges T08 indításához**

**T08 blokkolása:**
- Ha `validator_infra_pass = true` de `rc_correctness_pass = false`: T08 NEM INDÍTHATÓ
- Ha `rc_correctness_pass = false` oka `NOT_AVAILABLE` (T05 nem adott outputot): először T05-öt kell fixálni
- Ha `rc_correctness_pass = false` oka `FAIL_FALSE_POSITIVE`: az RC kernel javítandó (T05/T06 hibája)

## Részletes implementációs lépések

### 1. Exact collision check implementálása

A correctness validator saját exact collision check-kel dolgozik
(nem a placer collision checker-ét hívja, hogy ne legyen körkörös):

```rust
/// Ellenőrzi, hogy a part_b a `placement` pozícióban ütközik-e part_a-val
/// Exact geometriai metszésvizsgálat (Point-in-Polygon + edge intersection)
pub fn exact_collision_check(
    part_a: &Polygon64,
    part_b: &Polygon64,
    placement: &Point64,  // part_b eltolása
) -> bool
```

Az implementáció:
- part_b minden pontját a `placement` vektorral eltolja
- Part_a és az eltolt part_b AABB-k metszés ellenőrzése (gyors prefilter)
- Ha AABB metsz: polygon-polygon intersection check (edge-edge vagy point-in-polygon)

### 2. Mintavételező funkciók implementálása

```rust
/// N random pontot generál a polygon belsejéből
/// Returns: Vec<Point64>
pub fn sample_points_inside(poly: &Polygon64, n: usize, seed: u64) -> Vec<Point64>

/// N random pontot generál a polygon külső AABB-jából, de a polygon-on kívülről
/// Returns: Vec<Point64>
pub fn sample_points_outside(poly: &Polygon64, n: usize, seed: u64) -> Vec<Point64>

/// N pontot generál a polygon határán
/// Returns: Vec<Point64>
pub fn sample_points_on_boundary(poly: &Polygon64, n: usize, seed: u64) -> Vec<Point64>
```

### 3. `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` implementálása

**Parancssori interfész:**
```
--fixture <path>          NFP pair fixture JSON fájl
--nfp-source <src>        NFP forrás: "reduced_convolution_v1" | "mock_exact"
--sample-inside <N>       Mintaszám NFP belsejéből (default: 1000)
--sample-outside <N>      Mintaszám NFP külsejéből (default: 1000)
--sample-boundary <N>     Mintaszám NFP határán (default: 200)
--boundary-perturbation   Perturbáció mm-ben (default: 0.01)
--output-json             JSON output
```

**Correctness algoritmus:**

1. NFP kiszámítása (RC kernel vagy mock)
2. **Inside sampling** — N pont az NFP belsejéből:
   - Minden belső pontra: `exact_collision_check(part_a, part_b, point)` → True-nak KELL lennie
   - Ha False: `false_negative_count++` (az NFP azt mondja "belül van" = ütközés van, de exact check szerint nem)
3. **Outside sampling** — N pont az NFP külsejéből:
   - Minden külső pontra: `exact_collision_check(part_a, part_b, point)` → False-nak KELL lennie
   - Ha True: `false_positive_count++` (az NFP azt mondja "kívül van" = nincs ütközés, de exact check szerint van)
4. **Boundary sampling** — N pont az NFP határán:
   - Kis pozitív perturbáció → exact collision True
   - Kis negatív perturbáció → exact collision False
   - Eltérés: `boundary_penetration_max_mm` maximuma

**stdout JSON output:**
```json
{
  "benchmark_version": "nfp_correctness_v1",
  "nfp_source": "reduced_convolution_v1",
  "pair_id": "lv8_pair_01",
  "sample_count_inside": 1000,
  "sample_count_outside": 1000,
  "sample_count_boundary": 200,
  "false_positive_count": 0,
  "false_negative_count": 3,
  "false_positive_rate": 0.0,
  "false_negative_rate": 0.003,
  "boundary_penetration_max_mm": 0.001,
  "correctness_verdict": "MARGINAL",
  "nfp_was_available": true,
  "notes": "false_negative_rate > 0: NFP konzervatív (safe de suboptimal)"
}
```

**correctness_verdict értékek:**
- `PASS` — false_positive_rate = 0.0 ÉS false_negative_rate < 0.001
- `MARGINAL` — false_positive_rate = 0.0 ÉS false_negative_rate < 0.01 (konzervatív NFP)
- `FAIL_FALSE_POSITIVE` — false_positive_rate > 0.0 (ütközések lehetségesek → TILOS production-ban)
- `FAIL_FALSE_NEGATIVE` — false_negative_rate > 0.01 (több mint 1% kihasználtság veszteség)
- `NOT_AVAILABLE` — NFP output nem volt elérhető (T05 NotImplemented)

**Kritikus szabály:** `FAIL_FALSE_POSITIVE` esetén az NFP NEM fogadható el.
A `false_positive_count > 0` kritikus hiba — explicit stop feltétel.

### 4. Mock NFP mód (tesztelési célra)

Ha T05 még `NOT_IMPLEMENTED`, a `--nfp-source mock_exact` mód egy exact NFP-t számít
(konvex dekompozícióval) és azon méri a correctness validator-t.
Ez bizonyítja, hogy a correctness validator infrastruktúra működik.

## Adatmodell / contract változások
Új Rust bin (`nfp_correctness_benchmark.rs`). Nincs module change.

## Backward compatibility
Additive bin. A meglévő NFP pipeline érintetlen.

## Hibakódok / diagnosztikák
- `correctness_verdict: NOT_AVAILABLE` — NFP nem volt elérhető (T05 NotImplemented)
- `correctness_verdict: FAIL_FALSE_POSITIVE` — KRITIKUS: NFP production-ban tilos
- `nfp_was_available: false` — ha RC kernel NotImplemented-et adott

## Tesztelési terv
```bash
# 1. Bin help fut
cargo run --bin nfp_correctness_benchmark -- --help

# 2. T01 fixture-n lefut (NOT_AVAILABLE is elfogadható ha T05 NotImplemented)
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source reduced_convolution_v1 \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'correctness_verdict' in d
assert 'false_positive_rate' in d
assert 'false_negative_rate' in d
v = d['correctness_verdict']
assert v in ('PASS', 'MARGINAL', 'FAIL_FALSE_POSITIVE', 'FAIL_FALSE_NEGATIVE', 'NOT_AVAILABLE')
print('PASS: verdict =', v)
"

# 3. Mock NFP mód: correctness validator infrastruktúra tesztelése
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source mock_exact \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['false_positive_rate'] == 0.0, 'mock_exact should have 0 false positives'
print('mock_exact: false_positive_rate = 0.0 PASS')
"

# 4. false_positive_count > 0 esetén FAIL_FALSE_POSITIVE verdict
# (unit tesztben ellenőrizve)
```

## Elfogadási feltételek

**validator_infra_pass (kötelező T07 PASS-hoz, de nem elegendő T08-hoz):**
- [ ] `cargo run --bin nfp_correctness_benchmark -- --help` fut
- [ ] `false_positive_rate` és `false_negative_rate` a JSON output-ban explicit szerepelnek
- [ ] Mock NFP mód (`--nfp-source mock_exact`): `false_positive_rate = 0.0`
- [ ] `correctness_verdict` értékkészlete dokumentált (PASS / MARGINAL / FAIL_FALSE_POSITIVE / FAIL_FALSE_NEGATIVE / NOT_AVAILABLE)

**rc_correctness_pass (T08 indításának feltétele):**
- [ ] Tényleges RC NFP outputon fut a validator (T05 `verdict = SUCCESS` szükséges)
- [ ] `correctness_verdict` nem `NOT_AVAILABLE` — valódi RC NFP mérés történt
- [ ] `false_positive_rate = 0.0` — FAIL_FALSE_POSITIVE esetén T08 NEM INDÍTHATÓ
- [ ] `false_negative_rate < 0.01` (PASS vagy MARGINAL elfogadható)

**A report tartalmazza:**
- `validator_infra_pass: true/false`
- `rc_correctness_pass: true/false`
- `t08_unblocked: true/false`
- Ha `rc_correctness_pass = false`: explicit ok (NOT_AVAILABLE / FAIL_FALSE_POSITIVE / FAIL_FALSE_NEGATIVE)

## Rollback / safety notes
Kizárólag új bin. A meglévő placer, concave.rs, convex.rs érintetlen.

## Dependency
- T01: lv8_pair_01–03 fixture-ök
- T05: RC NFP output (ha NOT_IMPLEMENTED: NOT_AVAILABLE verdict)
- T06: nfp_validation.rs (polygon_is_valid)
- T08: ha T07 FAIL_FALSE_POSITIVE → T08 NEM integrálhat production-ba
