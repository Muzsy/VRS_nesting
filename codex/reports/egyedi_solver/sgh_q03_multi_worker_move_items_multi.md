PASS

# Report — SGH-Q03 `sgh_q03_multi_worker_move_items_multi`

## Status

PASS — deterministic multi-worker separator branch implemented with backward-compatible single-worker behavior; SGH-Q03 test set added; required Rust gates green.

## Meta

- **Task slug:** `sgh_q03_multi_worker_move_items_multi`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q03_multi_worker_move_items_multi.yaml`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** `main@39c88cf`
- **Fókusz terület:** `Mixed` (Rust optimizer + docs/report)

---

## Scope

### Cél

- Multi-worker `move_items_multi` jellegű keresés bevezetése a VRS separatorban.
- `worker_count=1` mellett SGH-Q02 kompatibilis viselkedés megtartása.
- Determinisztikus seedelt worker-ordering és stabil tie-break.
- Dense fixture no-regression: 3-worker ne legyen rosszabb 1-workernél.

### Nem-cél (explicit)

- exploration/compression phase orchestration
- infeasible solution pool/disruption loop
- continuous rotation, smooth loss model
- CDE collision backend
- IO contract/Python runner módosítás

---

## Dependency evidence

| Check | Result | Evidence |
|---|---:|---|
| SGH-Q02 report létezik | PASS | `codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md` |
| SGH-Q02 első sora PASS/PASS_WITH_NOTES | PASS | Első sor: `PASS` |
| SGH-Q02 tartalmazza `SGH-Q03_STATUS: READY` | PASS | Marker megtalálva |

---

## Source evidence

Lokálisan elérhető Sparrow source alapján:

- `.cache/sparrow/src/optimizer/separator.rs`:
  - `move_items_multi()` hívás és implementáció (Algorithm 10)
- `.cache/sparrow/src/optimizer/worker.rs`:
  - `move_items()` és shuffle-alapú worker iteráció (Algorithm 5)

VRS mapping:
- Worker fan-out ugyanazon master snapshotról
- Worker-specifikus seedelt item sorrend
- Best-worker-wins commit stabil tie-breakkel

---

## Current-state audit

SGH-Q02 után az `separator.rs` csak single-worker pályát használt:
- worst-collider célválasztás, egy iterációs move próbálkozás
- GLS rollback/weight-preserving logika már SGH-Q02-ben rendben volt
- worker fan-out és worker-seedelt sorrend hiányzott (F09 MISSING)

---

## Change summary

**Production:**
- `rust/vrs_solver/src/optimizer/separator.rs`

Fő módosítások:
- `VrsSeparatorConfig` új mezők: `worker_count`, `seed`
- `worker_count=0` normalizálás `max(1)`
- `SeparatorWorker`, `WorkerCandidate`, `DeterministicRng` privát modellek
- determinisztikus Fisher-Yates shuffle
- multi-worker ág a `run()`-ban (`worker_count>1`)
- stabil candidate tie-break: raw loss, weighted loss, accepted moves, worker_id, placement ordering
- SGH-Q03 unit tesztek (7 új teszt)

**Docs/Task artifacts:**
- `docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md`
- `codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md`
- `codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md`

---

## Config semantics

| Field | Default | Semantics |
|---|---:|---|
| `worker_count` | 1 | `<=1` esetén single-worker kompatibilis ág; `>1` esetén multi-worker ág |
| `seed` | 0 | determinisztikus worker-seed alap; azonos input + seed + worker_count mellett bit-stabil output |

---

## Worker model summary

- Minden worker ugyanarról a master `WorkingLayout` + `VrsCollisionTracker` snapshotról indul.
- Worker 0 baseline-kompatibilis (worst-collider célzással).
- Worker 1..N seedelt shuffle sorrenddel fut.
- Workers nem osztanak közös mutable state-et.
- Master csak javító candidate-et commitol.

---

## Determinism contract

Determinista összetevők:
- `worker_seed(iteration, worker_id)` fix mix formula
- `deterministic_shuffle` fix xorshift + Fisher-Yates
- stabil tie-break comparator

Bizonyíték:
- `multi_worker_same_seed_is_deterministic`
- `worker_seed_shuffle_smoke_distinct_and_deterministic`
- `worker_candidate_tiebreak_is_deterministic`

---

## F09 parity status update

| Feature | SGH-Q02 | SGH-Q03 | Evidence |
|---|---|---|---|
| F09 multi-worker / move_items_multi | MISSING | PARTIAL→FULL(rectangular separator scope) | worker model + multi-worker run branch + deterministic tie-break |

---

## No-downgrade gates G01–G08

| Gate | Elvárás | Státusz |
|---|---|---|
| G01 | `cargo test --lib` 0 failed | PASS (153/153) |
| G02 | `verify.sh` exit 0 | PASS |
| G03 | accepted output violations empty | PASS (dense zero-loss gate test) |
| G04 | proxy annotációk nem sérülnek | PASS |
| G05 | determinism stochasztikus komponenseknél | PASS |
| G06 | parity non-regression | PASS (F09 javult, nem romlott) |
| G07 | nincs új jelöletlen proxy | PASS |
| G08 | production scope only | PASS (`separator.rs` only) |

---

## Tests run

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
# Result: 27 passed; 0 failed

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Result: 153 passed; 0 failed
```

Új SGH-Q03 tesztek:
- `separator_worker_count_one_backward_compatible`
- `separator_worker_count_zero_normalized_to_one`
- `multi_worker_same_seed_is_deterministic`
- `worker_seed_shuffle_smoke_distinct_and_deterministic`
- `dense_fixture_three_worker_not_worse_than_single_worker`
- `dense_fixture_three_worker_output_no_violations_if_zero_loss`
- `worker_candidate_tiebreak_is_deterministic`

---

## 1-worker vs 3-worker dense fixture comparison

Fixture: `dense_fixture_21` (21 db 20×20 item, 1 db 200×200 sheet, azonos seed=777)

| Run | best_loss | iterations | moves_attempted | moves_accepted | rollback_count |
|---|---:|---:|---:|---:|---:|
| 1 worker | 0 | 21 | 20 | 20 | 0 |
| 3 workers | 0 | 2 | 41 | 41 | 0 |

Acceptance:
- `3-worker best_loss <= 1-worker best_loss` → PASS (`0 <= 0`)
- zero-loss accepted output violation-free gate → PASS

---

## Scope safety

| Tiltott módosítás | Eredmény |
|---|---|
| Phase orchestration / pool / disruption | NEM történt |
| Continuous rotation / smooth loss / CDE | NEM történt |
| IO contract / Python runner | NEM történt |
| Production fájl allowed-on kívül | NEM történt |

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték |
|---|---:|---|
| Dependency gate teljesül | PASS | SGH-Q02 report: PASS + `SGH-Q03_STATUS: READY` |
| Config bővítés (`worker_count`, `seed`) | PASS | `separator.rs` `VrsSeparatorConfig` mezők |
| `worker_count=0` guard/normalizálás | PASS | `normalized_worker_count()` + teszt |
| worker_count=1 backward compatibility | PASS | `separator_worker_count_one_backward_compatible` |
| Multi-worker worker modell | PASS | `SeparatorWorker`, `WorkerCandidate`, `run_worker_iteration` |
| Seedelt deterministic shuffle | PASS | `DeterministicRng`, `deterministic_shuffle`, shuffle smoke test |
| Deterministic tie-break | PASS | `compare_worker_candidates` + tie-break test |
| 3-worker non-regression dense fixture | PASS | `dense_fixture_three_worker_not_worse_than_single_worker` |
| 3-worker zero-loss no-violation gate | PASS | `dense_fixture_three_worker_output_no_violations_if_zero_loss` |
| Kötelező Rust tesztek | PASS | `cargo test ... separator`, `cargo test ... --lib` |
| Repo gate verify | PASS | `./scripts/verify.sh --report ...` |

---

## Advisory notes

- Multi-worker futtatás jelenleg determinisztikus, de nem rayon-alapú; SGH-Q04 előtt ez célszerűen benchmark-alapon döntendő.
- Dense fixture-ben a 3-worker ág jelentősen kevesebb iterációval érte el a zéró loss-t, de ez nem általános teljesítmény-ígéret.

SGH-Q04_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T13:39:58+02:00 → 2026-05-25T13:42:59+02:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.verify.log`
- git: `main@39c88cf`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/separator.rs | 728 ++++++++++++++++++++++++-----
 1 file changed, 608 insertions(+), 120 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/separator.rs
?? README_SGH_Q03_PACKAGE.md
?? canvases/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
?? codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q03_multi_worker_move_items_multi.yaml
?? codex/prompts/egyedi_solver/sgh_q03_multi_worker_move_items_multi/
?? codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
?? codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.verify.log
?? docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md
```

<!-- AUTO_VERIFY_END -->
