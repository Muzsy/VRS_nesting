PASS

# Report — SGH-05 `sgh_05_transfer_swap_reinsert_move_operators`

## Status

PASS — all DoD items satisfied, 140/140 Rust tests pass, verify.sh exit 0.

## Meta

- **Task slug:** `sgh_05_transfer_swap_reinsert_move_operators`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_05_transfer_swap_reinsert_move_operators.yaml`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** main (post-SGH-04)
- **Fókusz terület:** Rust optimizer / move operators (`moves.rs`)

## Scope

### Cél

- SGH-04 dependency gate ellenőrzése.
- `moves.rs` skeleton → rollback-safe move execution API.
- `try_reinsert`, `try_transfer`, `try_swap`, `resolve_by_transfers` implementálása.
- `MoveDiagnostics`, `MoveFailureReason`, `MoveExecutor` típusok.
- 16 új unit teszt.
- Contract dokumentáció.

### Nem-cél

- Pipeline-integráció (initializer / sheet_elimination bekötés).
- Solution pool / perturbáció.
- Solver IO contract módosítás.
- SparrowGH backend / vendor.

---

## Dependency evidence

| Check | Result | Evidence |
|---|---:|---|
| SGH-04 report exists | PASS | `codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md` létezik |
| SGH-04 first line PASS | PASS | Első sor: `PASS` |
| SGH-04 contains `SGH-05_STATUS: READY` | PASS | Report végén megtalálható |

---

## VRS current-state audit findings

1. **`moves.rs`** — csak `CandidateMove` enum skeleton (Place/Move/Reinsert/Rotate) + 3 serialization teszt; tényleges execution logika nélkül.

2. **`WorkingLayout::validate_for_commit()`** — non-consuming commit gate, `Result<WorkingCommitDiagnostics, WorkingCommitError>` visszatérési értékkel. SGH-05 minden operatora ezt a kaput használja elfogadás előtt.

3. **`VrsSeparatorConfig.allowed_sheet_indices: Option<Vec<usize>>`** — SGH-04 óta elérhető; SGH-05 operátorok erre scope-olják a separator futást (pl. transfer → only to_sheet, swap → {sheet_a, sheet_b}).

4. **`find_violations()`** — a VRS oldali accepted-output safety gate; minden `commit_gate_ok` hívásban szerepel.

5. **`Placement` IO contract** — nem módosult; `moves.rs` csak `Vec<Placement>` bevitelt/kimenetet kezel.

6. **Pipeline-integráció** — nem készült; a move operátorok unit teszt szinten elérhetők, de az optimizer loop nem hívja őket automatikusan.

7. **Determinizmus** — `generate_candidates_with_sheets` determinisztikus, `VrsSeparator` determinisztikus (nincs RNG), `resolve_by_transfers` sorrendje explicit és stabil.

8. **SparrowGH** — nincs közvetlen portolás; az algoritmus mintát (transfer/swap/reinsert) önálló VRS-belső implementációként valósítottuk meg.

---

## Change summary

Egyetlen production fájl módosult:

- **`rust/vrs_solver/src/optimizer/moves.rs`** — teljes SGH-05 implementáció a skeleton megtartásával

Új dokumentáció:

- `docs/egyedi_solver/sgh_05_move_operators_contract.md`
- `codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md`
- `codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.verify.log`
- `codex/codex_checklist/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md`

---

## Implementation summary

### Új típusok (`moves.rs`)

**`MoveFailureReason`** enum: `UnknownInstanceId`, `InvalidSheetIndex`, `UnsupportedRotation`, `NoValidSeedPlacement`, `SeparatorDidNotConverge`, `CommitGateRejected`, `PlacementCountMismatch`, `InstanceSetMismatch`.

**`MoveDiagnostics`**: `attempted`, `committed`, `rolled_back`, `separator_attempts`, `separator_successes`, `commit_gate_rejections`, `last_reason`. `summary()` tartalmaz minden mezőt.

**`MoveExecutor<'a>`**: `parts: &'a [Part]`, `sheets: &'a [SheetShape]`.

### Privát helperek

| Helper | Feladat |
|---|---|
| `rebuild_bboxes` | Placement lista → PlacedBbox vektor |
| `commit_gate_ok` | Count + instance set + sheet bounds + find_violations |
| `run_separator_fix` | WorkingLayout → VrsSeparator → validate_for_commit gate |
| `seed_at_origin` | Origin seed placement adott sheeten, adott rotációval |
| `lbf_clear_on_sheet` | LBF clear candidate keresés adott sheeten (y asc, x asc) |
| `resolve_part_dims` | Part dims + normalize_allowed_rotations |

### Operátorok

**`try_reinsert`**: seed at origin of `to_sheet` → separator scoped to `to_sheet` → commit gate.

**`try_transfer`**: 3 prioritásos path: (1) explicit rotation + separator; (2) LBF clear (no separator); (3) origin seed + separator. Mindhárom path commit gate-et alkalmaz.

**`try_swap`**: same-sheet → no-op success (dokumentált, tesztelt). Cross-sheet → A seeds at B's old sheet, B seeds at A's old sheet → separator scoped to `{sheet_a, sheet_b}` → commit gate.

**`resolve_by_transfers`**: source sheets asc → items (area desc, instance_id asc) → dest sheets asc. Budget decremented per attempt. Skip if item already moved. Failed attempts rollback-safe.

---

## Tests

**Futás:** `cargo test -p vrs_solver moves` — 19 teszt, 19/19 PASS  
**Teljes suite:** `cargo test -p vrs_solver` — 140 teszt, 140/140 PASS

| Teszt neve | Mit ellenőriz |
|---|---|
| `candidate_move_place_creates` (existing) | Serialization — Place |
| `candidate_move_all_variants_create` (existing) | Serialization — all 4 variants |
| `candidate_move_json_stable` (existing) | Serialization determinism |
| `try_reinsert_valid_commits` | Reinsert success + find_violations üres |
| `try_reinsert_unknown_instance_id_fails` | UnknownInstanceId → None |
| `try_reinsert_invalid_sheet_index_fails` | InvalidSheetIndex → None |
| `try_transfer_success` | Transfer: item sheet 1-re kerül, valid layout |
| `try_transfer_invalid_destination_fails` | InvalidSheetIndex → None |
| `try_transfer_unsupported_rotation_fails` | UnsupportedRotation → None |
| `try_swap_cross_sheet_success` | Swap: mindkét item valid helyre kerül |
| `try_swap_same_sheet_is_noop_success` | Same-sheet no-op success |
| `try_swap_unknown_instance_fails` | UnknownInstanceId → None |
| `resolve_by_transfers_budget_zero_no_changes` | Budget=0 → no attempts, layout unchanged |
| `resolve_by_transfers_no_partial_invalid_output` | Failed transfers → layout violation-free |
| `resolve_by_transfers_transfers_item_to_dest` | Tényleges transfer megtörténik |
| `diagnostics_summary_contains_expected_fields` | summary() tartalmaz minden mezőt |
| `placement_count_and_instance_set_invariant` | Count + instance set megmarad |
| `deterministic_smoke` | Azonos input + move → azonos output (twice) |
| `committed_output_find_violations_valid` | Committed output violation-free |

---

## Scope safety

| Tiltott fájl | Módosult? |
|---|---|
| `rust/vrs_solver/src/io.rs` | NEM |
| `rust/vrs_solver/src/adapter.rs` | NEM |
| `rust/vrs_solver/src/optimizer/sheet_elimination.rs` | NEM |
| `rust/vrs_solver/src/optimizer/initializer.rs` | NEM |
| `rust/vrs_solver/src/optimizer/multisheet.rs` | NEM |
| `rust/vrs_solver/src/optimizer/score.rs` | NEM |
| Python runner / exact validator | NEM |
| SparrowGH vendor/submodule | NEM |
| Continuous rotation | NEM |
| Solution pool / perturbáció | NEM |
| Cavity-prepack | NEM |
| Pipeline-integráció | NEM |

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Fájl / Függvény |
|---|---:|---|---|
| SGH-04 dependency gate zöld | PASS | `sgh_04_...md` első sor `PASS`, tartalmaz `SGH-05_STATUS: READY` | `codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md` |
| `moves.rs` execution API elkészült | PASS | `MoveExecutor`, `MoveDiagnostics`, `MoveFailureReason` típusok | `moves.rs` |
| `try_reinsert` rollback-safe | PASS | `try_reinsert_valid_commits` + `try_reinsert_*_fails` tesztek | `moves.rs` — `try_reinsert()` |
| `try_transfer` rollback-safe, LBF + separator | PASS | `try_transfer_success` + failure tesztek | `moves.rs` — `try_transfer()` |
| `try_swap` rollback-safe, same-sheet no-op dokumentált | PASS | `try_swap_cross_sheet_success` + `try_swap_same_sheet_is_noop_success` | `moves.rs` — `try_swap()` |
| `resolve_by_transfers` budget-aware, rollback-safe | PASS | `resolve_by_transfers_budget_zero_no_changes`, `resolve_by_transfers_no_partial_invalid_output` | `moves.rs` — `resolve_by_transfers()` |
| Accepted output find_violations szerint valid | PASS | `committed_output_find_violations_valid`, `try_swap_cross_sheet_success` | `moves.rs` — `commit_gate_ok()` |
| Placement count + instance set invariant | PASS | `placement_count_and_instance_set_invariant` | `moves.rs` — `commit_gate_ok()` |
| Deterministic move output | PASS | `deterministic_smoke` teszt | `moves.rs` — `try_transfer()` |
| Focused Rust tests zöldek | PASS | `cargo test -p vrs_solver moves`: 19/19; full: 140/140 | CI output |
| Nincs külső backend/vendor | PASS | git diff — csak `moves.rs` módosult production kódban | scope safety tábla |
| Contract doksi elkészült | PASS | 13 kötelező szekció megvan | `docs/egyedi_solver/sgh_05_move_operators_contract.md` |
| Repo verify zöld | PASS | `./scripts/verify.sh ...` exit 0; DONE smoketest OK | `sgh_05_...verify.log` |

---

## Verification

```bash
# Focused moves tests
cargo test -p vrs_solver moves
# Result: 19 passed; 0 failed

# Full test suite
cargo test -p vrs_solver
# Result: 140 passed; 0 failed

# Repo gate
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
# Result: [DONE] smoketest OK (exit 0)
```

Verify log: `codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.verify.log`

SGH-06_STATUS: READY
