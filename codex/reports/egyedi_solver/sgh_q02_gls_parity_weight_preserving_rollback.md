PASS

# Report — SGH-Q02 `sgh_q02_gls_parity_weight_preserving_rollback`

## Status

PASS — multiplicative GLS + restore_but_keep_weights implemented; 6 new tests added; 146/146 pass; verify.sh exit 0.

## Meta

- **Task slug:** `sgh_q02_gls_parity_weight_preserving_rollback`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** main (post-SGH-Q01)
- **Fókusz terület:** GLS formula parity (F07) + weight-preserving rollback (F08)

---

## Dependency evidence

| Check | Result | Evidence |
|---|---:|---|
| SGH-Q01 report létezik | PASS | `codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md` |
| SGH-Q01 első sora PASS | PASS | Első sor: `PASS` |
| SGH-Q01 tartalmazza `SGH-Q02_STATUS: READY` | PASS | Report végén megtalálható |

---

## Source evidence

Sparrow Algorithm 8 (`sparrow/quantify/tracker.rs`, commit `a4bfbbe0`):

```
max_loss = max over all CTEntry losses
for each CTEntry:
  if loss == 0: new_weight = old_weight * GLS_WEIGHT_DECAY (decay)
  else: ratio = loss / max_loss
        mult = MIN_INC + (MAX_INC - MIN_INC) * ratio
        new_weight = clamp(old_weight * mult, 1.0, weight_max)
restore_but_keep_weights(): restore solution geometry, keep CTEntry weights
```

---

## Current-state audit

| Elem | Állapot SGH-Q01 után | Állapot SGH-Q02 után |
|---|---|---|
| GLS formula | Additive (QUALITY_RISK: AdditiveGlsProxy) | Multiplicative + max_loss (Algorithm 8) |
| max_loss normalizáció | Hiányzott | Implementálva |
| No-collision decay | Nem volt | Implementálva (→ 1.0 floor) |
| Rollback loss-state | `restore_item` (per-item) | `restore_but_keep_weights(LossSnapshot)` |
| Config fields | `gls_weight_decay=0.01`, `gls_weight_max` | + `gls_weight_min_inc_ratio=1.01`, `gls_weight_max_inc_ratio=1.05`; decay default=0.98 |
| AdditiveGlsProxy annotáció | Jelen volt | Eltávolítva (már nem proxy) |

---

## Change summary

**File:** `rust/vrs_solver/src/optimizer/separator.rs`

```
+ LossSnapshot { bboxes, boundary_valid } pub struct
+ VrsCollisionTracker::snapshot_loss() -> LossSnapshot
+ VrsCollisionTracker::restore_but_keep_weights(LossSnapshot)
~ VrsCollisionTracker::update_weights: 2→4 params; multiplicative formula
~ VrsSeparatorConfig: +gls_weight_min_inc_ratio, +gls_weight_max_inc_ratio; decay default 0.01→0.98
~ VrsSeparator::run: rollback uses restore_but_keep_weights; update_weights calls updated
+ pair_weight pub; boundary_weight pub accessor
- AdditiveGlsProxy QUALITY_RISK annotation removed
+ 6 new tests (Test 11–16)
```

---

## Config semantics

| Field | Default | Semantics |
|---|---|---|
| `gls_weight_decay` | 0.98 | Multiplicative decay per iteration for non-colliding weight entries. |
| `gls_weight_max` | 100.0 | Maximum weight cap. |
| `gls_weight_min_inc_ratio` | 1.01 | Min multiplier for lowest-loss colliding pair. |
| `gls_weight_max_inc_ratio` | 1.05 | Max multiplier for highest-loss colliding pair. |

---

## F07/F08 parity status update

| Feature | Status SGH-Q01 | Status SGH-Q02 | Evidence |
|---|---|---|---|
| F07 GLS dynamic weights | PARTIAL (additive) | **FULL** | Multiplicative formula + max_loss normalization + decay, matching Sparrow Algorithm 8 |
| F08 Separator incumbent / restore | PARTIAL | **PARTIAL→improved** | `restore_but_keep_weights` at every rollback point; full incumbent swap remains SGH-Q03 scope |

---

## No-downgrade gates G01–G08

| Gate | Elvárás | Státusz |
|---|---|---|
| G01 `cargo test --lib` | 146/146 | PASS |
| G02 `verify.sh` | exit 0 | PASS |
| G03 `find_violations` | 0 violation minden accepted output-on | PASS (commit gate változatlan) |
| G04 Proxy annotáció | AdditiveGlsProxy eltávolítva (már nem proxy); egyéb PROXY annotációk érintetlenek | PASS |
| G05 Determinism | `separator_is_deterministic` test zöld | PASS |
| G06 Parity non-regression | F07: PARTIAL→FULL; F08: improved; semmi sem csökkent | PASS |
| G07 No new proxy without gate | Nincs új PROXY | PASS |
| G08 Production scope | Csak `separator.rs` módosítva | PASS |

---

## Tests run

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
# Result: 20 passed; 0 failed

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Result: 146 passed; 0 failed
```

Új tesztek (Test 11–16):
- `multiplicative_gls_larger_loss_gets_larger_weight` — ok
- `multiplicative_gls_max_loss_pair_gets_max_ratio` — ok
- `multiplicative_gls_no_collision_decay` — ok
- `multiplicative_gls_boundary_weight_updates` — ok
- `restore_but_keep_weights_preserves_gls` — ok
- `multiplicative_gls_no_spurious_entries_for_zero_loss` — ok

---

## Scope safety

| Tiltott művelet | Megtörtént? |
|---|---|
| multi-worker / rayon | NEM |
| stochastic ordering | NEM |
| phase orchestration | NEM |
| IO contract módosítás | NEM |
| Python runner módosítás | NEM |
| Külső backend/vendor | NEM |
| Más production fájl módosítása | NEM |

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték |
|---|---:|---|
| Dependency gate (SGH-Q01 PASS + READY) | PASS | SGH-Q01 report `PASS`, `SGH-Q02_STATUS: READY` |
| Multiplicative GLS implementálva | PASS | `update_weights` 4-param, max_loss normalizáció, multiplicative mult |
| max_loss normalizáció jelen van | PASS | `let mut max_loss = 0.0_f64; ... max_loss.max(...)` |
| Pair + boundary azonos elvvel frissül | PASS | Közös max_loss pool, azonos formula |
| No-collision decay implementálva | PASS | `*w = (*w * decay).max(1.0)` |
| Nulla-loss pairekhez nincs felesleges entry | PASS | Test 16 `pair_weights.is_empty()` |
| Config mezők nem törtek el | PASS | Meglévő mezők érintetlenek; új mezők defaulttal |
| AdditiveGlsProxy annotáció frissítve | PASS | Eltávolítva; doc comment Algorithm 8 parity jelzi |
| `restore_but_keep_weights` implementálva | PASS | `LossSnapshot` + `snapshot_loss` + `restore_but_keep_weights` |
| Rollback pontok helper-t használnak | PASS | `VrsSeparator::run` rollback: `restore_but_keep_weights(loss_snap)` |
| 7 kötelező teszt mind zöld | PASS | Test 11–16 + meglévő 7, 8 |
| Contract doc elkészült | PASS | `docs/egyedi_solver/sgh_q02_...contract.md` |
| `cargo test separator` 100% | PASS | 20/20 |
| `cargo test --lib` 100% | PASS | 146/146 |
| Verify green | PASS | `verify.sh` exit 0 |

---

## Verification

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
# 20 passed; 0 failed

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# 146 passed; 0 failed

./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
# [DONE] smoketest OK (exit 0)
```

SGH-Q03_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T13:12:53+02:00 → 2026-05-25T13:15:57+02:00 (184s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.verify.log`
- git: `main@5449247`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/separator.rs | 300 +++++++++++++++++++++++++++--
 1 file changed, 281 insertions(+), 19 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
?? codex/codex_checklist/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q02_gls_parity_weight_preserving_rollback.yaml
?? codex/prompts/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback/
?? codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
?? codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.verify.log
?? docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
```

<!-- AUTO_VERIFY_END -->
