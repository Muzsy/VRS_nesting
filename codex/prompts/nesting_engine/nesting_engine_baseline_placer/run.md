# VRS Nesting Codex Task — NFP Nesting Engine: Baseline placer + Python runner + benchmark
TASK_SLUG: nesting_engine_baseline_placer

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `rust/nesting_engine/src/geometry/pipeline.rs` — `run_inflate_pipeline()` API (F1-3)
6. `rust/nesting_engine/src/io/pipeline_io.rs` — `PipelineRequest`, `PipelineResponse` (F1-3)
7. `rust/nesting_engine/src/main.rs` — meglévő CLI (inflate-parts subcommand)
8. `rust/nesting_engine/Cargo.toml` — meglévő dependency-k
9. `docs/nesting_engine/io_contract_v2.md` — input/output séma (F1-2)
10. `docs/nesting_engine/json_canonicalization.md` — `determinism_hash` szabály (F1-2)
11. `docs/nesting_engine/tolerance_policy.md` — SCALE, TOUCH_TOL (F1-1)
12. `docs/nesting_engine/architecture.md` — nominális vs. inflated szabály (F1-3)
13. `vrs_nesting/runner/vrs_solver_runner.py` — runner architektúra minta
14. `poc/nesting_engine/sample_input_v2.json` — poc fixture
15. `canvases/nesting_engine/nesting_engine_baseline_placer.md` — feladat specifikációja
16. `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer.yaml` — lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

Ez a Fázis 1 utolsó taskja. A végeredmény egy futó, determinisztikus nesting
rendszer: az io_contract_v2 input JSON-ból BLF placement engine-nel elhelyezi
a darabokat, multi-sheet greedy stratégiával, és io_contract_v2 output JSON-t
ad — benne valódi `determinism_hash`-sel.

Deliverable-ök:
- `feasibility/` — `can_place()` AABB + polygon narrow-phase
- `placement/blf.rs` — BLF placer, determinisztikus rács traversal
- `multi_bin/greedy.rs` — iteratív multi-sheet
- `export/output_v2.rs` — io_contract_v2 output + `determinism_hash` (RFC 8785 / JCS)
- `nest` subcommand a Rust binárisban
- `vrs_nesting/runner/nesting_engine_runner.py` — Python adapter
- `poc/nesting_engine/baseline_benchmark.md` — valós mérési eredmény

## 3) Nem cél

- NFP számítás (F2-x)
- Simulated Annealing (F2-4)
- `vrs_solver` bármilyen módosítása
- `vrs_nesting/cli.py` módosítása
- `vrs_nesting/runner/vrs_solver_runner.py` módosítása (csak minta)

---

## 4) Architekturális invariáns — soha nem szeghet meg

```
A BLF placer KIZÁRÓLAG inflated geometriával hívja a can_place()-t.
Az output JSON placement koordinátái (x_mm, y_mm) NOMINÁLISAK
(a nominális origóra vonatkozó eltolás).
DXF export (ha lesz) MINDIG nominális geometriából történik.
```

---

## 5) Kritikus implementációs döntések

**`determinism_hash` — kötelező, nem placeholder**

Az F1-4 elfogadásának egyik kemény feltétele, hogy a `meta.determinism_hash`
valódi SHA-256 hash legyen, nem `"sha256:placeholder"`. A `json_canonicalization.md`
normative dokumentum pontosan leírja a hash-view struktúrát és a számítási módot.

Rust implementációs javaslat ha nincs JCS crate:
```rust
// BTreeMap garantálja a kulcsok lexikografikus sorrendjét → RFC 8785 kompatibilis
// integers-only hash-view → float formatting nem probléma
use std::collections::BTreeMap;
let canonical = serde_json::to_string(&btreemap_value)?;
let hash = sha2::Sha256::digest(canonical.as_bytes());
format!("sha256:{}", hex::encode(hash))
```

**Touching = infeasible (TOUCH_TOL)**

A `can_place()` a `TOUCH_TOL = 1i64` (= 1 µm) alapján dönt: ha két polygon
érintkezik, az infeasible. Ez a konzervatív oldal — a gyártási biztonság miatt.

**BLF rács traversal determinizmus**

A rács traversal sorrendje kőbe vésett: Y külső ciklus (alulról felfelé),
X belső ciklus (balról jobbra), rotation a `allowed_rotations_deg` eredeti
sorrendjében. Ez garantálja, hogy azonos input → azonos placement sorrend.

**Python runner stdin/stdout**

A `nesting_engine nest` subcommand stdin-ről olvassa az input JSON-t és
stdout-ra írja az output JSON-t. A Python runner ennek megfelelően
`subprocess.run(..., input=..., capture_output=True)` mintát követ.

---

## 6) Munkaszabályok (nem alkuképes)

- **Outputs szabály:** csak olyan fájlt hozhatsz létre / módosíthatsz, ami
  szerepel az adott YAML step `outputs` listájában.
- **vrs_solver érintetlen:** a regressziós baseline nem változhat.
- **inflate-parts érintetlen:** az F1-3 subcommand változatlan marad.
- **Gate csak wrapperrel.**

---

## 7) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit **sorrendben**:

```
codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer.yaml
```

---

## 8) Kötelező gate (a végén, egyszer)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer.md
```

A gate előtt ellenőrizd manuálisan:

```bash
# Unit tesztek
cargo test --manifest-path rust/nesting_engine/Cargo.toml

# vrs_solver regresszió
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml

# nest smoke
cat poc/nesting_engine/sample_input_v2.json \
  | ./rust/nesting_engine/target/release/nesting_engine nest \
  > /tmp/baseline_out.json
python3 -m json.tool /tmp/baseline_out.json > /dev/null

# determinism_hash valódi
python3 -c "
import json; a = json.load(open('/tmp/baseline_out.json'))
h = a['meta']['determinism_hash']
assert h.startswith('sha256:') and h != 'sha256:placeholder', f'bad hash: {h}'
print('hash OK:', h[:30], '...')
"

# determinizmus (két futás)
cat poc/nesting_engine/sample_input_v2.json \
  | ./rust/nesting_engine/target/release/nesting_engine nest \
  > /tmp/baseline_out2.json
python3 -c "
import json
a = json.load(open('/tmp/baseline_out.json'))
b = json.load(open('/tmp/baseline_out2.json'))
assert a['meta']['determinism_hash'] == b['meta']['determinism_hash'], 'HASH MISMATCH'
print('determinism OK')
"

# 0 out-of-bounds
python3 -c "
import json
inp = json.load(open('poc/nesting_engine/sample_input_v2.json'))
out = json.load(open('/tmp/baseline_out.json'))
m = inp['sheet']['margin_mm']
for p in out['placements']:
  assert p['x_mm'] >= m - 0.001 and p['y_mm'] >= m - 0.001, f'OOB: {p}'
print('0 out-of-bounds OK, placed:', len(out['placements']))
"
```

---

## 9) Elvárt kimenetek

**Új fájlok:**
- `rust/nesting_engine/src/feasibility/mod.rs`
- `rust/nesting_engine/src/feasibility/aabb.rs`
- `rust/nesting_engine/src/feasibility/narrow.rs`
- `rust/nesting_engine/src/placement/mod.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/multi_bin/mod.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/export/mod.rs`
- `rust/nesting_engine/src/export/output_v2.rs`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `poc/nesting_engine/baseline_benchmark.md`
- `codex/codex_checklist/nesting_engine/nesting_engine_baseline_placer.md`
- `codex/reports/nesting_engine/nesting_engine_baseline_placer.md`
- `codex/reports/nesting_engine/nesting_engine_baseline_placer.verify.log`

**Módosuló fájlok:**
- `rust/nesting_engine/src/main.rs` — `nest` subcommand hozzáadva
- `rust/nesting_engine/Cargo.toml` — sha2, hex, esetleg rstar hozzáadva
- `rust/nesting_engine/Cargo.lock` — dependency lock frissítve

**Érintetlen (ellenőrizd):**
- `rust/vrs_solver/` — egyetlen fájl sem változik
- `rust/nesting_engine/src/geometry/pipeline.rs` — nem változik
- `rust/nesting_engine/src/io/` — nem változik
- `vrs_nesting/runner/vrs_solver_runner.py` — nem változik
- `vrs_nesting/cli.py` — nem változik

---

## 10) Elfogadási kritériumok

1. `cargo test --manifest-path rust/nesting_engine/Cargo.toml` — PASS (can_place tesztek benne)
2. `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` — PASS (regresszió)
3. `nest` subcommand fut és valid io_contract_v2 JSON-t ad a poc fixture-ön
4. `meta.determinism_hash` — valódi `"sha256:..."` érték, nem placeholder
5. Két egymást követő `nest` futás azonos `determinism_hash`-t ad
6. 0 out-of-bounds: minden `placement.x_mm >= margin_mm` és `placement.y_mm >= margin_mm`
7. `poc/nesting_engine/baseline_benchmark.md` — valós `sheets_used`, `utilization_pct`, `determinism_hash`
8. `./scripts/verify.sh` gate — PASS

---

## 11) Ez a Fázis 1 lezárása

Az F1-4 PASS után a Fázis 1 (Truth Layer) teljes. A következő task az F2-1
(`nfp_computation_convex`) — az NFP motor első lépése. A `baseline_benchmark.md`-ben
rögzített mérési eredmény az a baseline, amelyhez képest az F2-x javulást mérjük.