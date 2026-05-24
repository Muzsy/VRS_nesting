PASS

# Report — SGH-03 `sgh_03_lbf_separator_construction_integration`

## Status

PASS — all DoD items satisfied, 121/121 Rust tests pass, verify.sh exit 0.

## Meta

- **Task slug:** `sgh_03_lbf_separator_construction_integration`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_03_lbf_separator_construction_integration.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_03_lbf_separator_construction_integration.yaml`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** main (post-SGH-02 commit `6085a71`)
- **Fókusz terület:** Rust optimizer / initial construction (`initializer.rs`)

## Scope

### Cél

- SGH-02 dependency gate ellenőrzése.
- `build_initial_layout()` initial construction LBF-scored clear candidate selectionre átállítása.
- `VrsSeparator` fallback bekötése construction szinten, kizárólag commit-gate zöld eredmény elfogadásával.
- `ConstructionDiagnostics` bővítése LBF/separator mezőkkel.
- Rust unit tesztek bővítése (8 új teszt).
- Contract dokumentáció elkészítése.

### Nem-cél

- Külső SparrowGH backend / vendor.
- Sheet elimination, move operators, solution pool vagy perturbáció.
- Solver IO contract / Python runner / exact validator módosítás.
- Continuous rotation vagy nagy benchmark kampány.

---

## Dependency evidence

| Check | Result | Evidence |
|---|---:|---|
| SGH-02 report exists | PASS | `codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md` létezik |
| SGH-02 first line PASS/PASS_WITH_NOTES | PASS | Első sor: `PASS` |
| SGH-02 contains `SGH-03_STATUS: READY` | PASS | Report utolsó sorában: `SGH-03_STATUS: READY` |

---

## VRS current-state audit findings

Az SGH-03 implementáció előtt elvégzett kódaudit megállapításai:

1. **`build_initial_layout()`** — FFD/largest-first sorrendű instance iterálás, de a candidate választás korábban első-valid jellegű volt: az első boundary-valid, collision-free candidate-et fogadta el automatikusan, LBF scoring nélkül.

2. **`generate_candidates_with_sheets()`** (`candidates.rs`) — Determinisztikus, sheet_index→y→x sorrendű candidate forrás, EPS-deduplikációval. Tartalmaz regular (corner + edge) és irregular (vertex, edge, interior) pontokat is. Ez az SGH-03 LBF scorer természetes bemenete.

3. **`ConstructionDiagnostics`** — Korábban tartalmazott: `candidates_tried`, `rejected_boundary`, `rejected_collision`, `irregular_candidates_tried`, `irregular_candidates_rejected`. LBF/separator fallback metrikák nem voltak.

4. **`VrsSeparator::run()`** — Elérhető a `separator.rs`-ben (SGH-02). `WorkingLayout` bemenetet fogad, `(WorkingLayout, VrsSeparatorDiagnostics)` párt ad vissza. Nem commitol belsőleg. `VrsSeparatorDiagnostics.best_loss` és `.converged` ellenőrizhetők.

5. **`WorkingLayout::validate_for_commit()`** — Non-consuming check, `Result<WorkingCommitDiagnostics, WorkingCommitError>` visszatérési értékkel. Ez az SGH-03 commit gate.

6. **`repair::find_violations()`** — `Vec<(usize, ViolationType)>` visszatérési értékkel (Overlap / BoundaryOrSheet). Az exact validator ekvivalense a Rust unit tesztekben; a commit gate előszűrő.

7. **Solver IO contract** — `io.rs`, `adapter.rs`, Python runner, exact validator érintetlen maradt.

---

## Change summary

Egyetlen production fájl módosult:

- **`rust/vrs_solver/src/optimizer/initializer.rs`** — 566 sor hozzáadás, 73 sor törlés (nettó: +493 sor)

Új fájlok:

- `docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md`
- `codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md`
- `codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.verify.log`
- `codex/codex_checklist/egyedi_solver/sgh_03_lbf_separator_construction_integration.md`
- SGH-03 task files (canvas, checklist template, goal YAML, run.md prompt)

---

## Implementation summary

### 1. ConstructionDiagnostics bővítés (`initializer.rs`)

Hat új mező:

```rust
pub lbf_candidates_scored: usize,
pub lbf_clear_accepts: usize,
pub separator_fallback_attempts: usize,
pub separator_fallback_successes: usize,
pub separator_fallback_failures: usize,
pub separator_fallback_rejected_by_commit_gate: usize,
```

`summary()` frissítve: `lbf_scored=N lbf_clear=N sep_attempts=N sep_ok=N sep_fail=N sep_commit_reject=N`.

### 2. LBF-scored clear candidate selection

Új privát helperek:

- **`lbf_key_better_than()`** — Összehasonlítja `(is_unused, y, x, sheet_index)` kulcsokat; kisebb érték jobb. `is_unused=false` beats `is_unused=true`.
- **`lbf_select_clear_candidate()`** — Iterál minden `CandidatePoint × rotation` páron; `rect_within_boundary()` és `PlacedBbox::overlaps()` szűrők után a legjobb LBF-kulcsú candidate-et adja vissza. Kandidátusonként csak az első valid rotation számít.

A `build_initial_layout()` most `lbf_select_clear_candidate()` eredményét fogadja el az első-valid logika helyett. Nyomon követi a `used_sheets: HashSet<usize>` halmazt.

### 3. Separator fallback

Új privát helperek:

- **`find_seed_sheet_index()`** — Visszaadja a legtöbb szabad területű használt sheet indexét; ha nincs használt sheet, 0-t ad.
- **`rebuild_placed_bboxes()`** — A teljes `placements` lista alapján újraépíti a `PlacedBbox` vektort (`bbox_from_placement()`-t hív minden elemre).
- **`try_separator_fallback_for_instance()`** — Seed placement az origin-en, `WorkingLayout::new()` az aktuális placementekből + seed-ből, `VrsSeparator::run()` futtatása, commit gate (`best_loss==0.0 || converged` ÉS `validate_for_commit` Ok), siker esetén visszaadja az új `(Vec<Placement>, Vec<PlacedBbox>)` párt.

A `build_initial_layout()` fallback ágában:
- Siker: `placements` és `placed_bboxes` teljesen kicserélődnek; `used_sheets` újraépül.
- Sikertelenség: korábbi state érintetlen; az item `Unplaced(NO_CANDIDATE)` lesz.

### 4. Public signature

`build_initial_layout()` aláírása változatlan:

```rust
pub fn build_initial_layout(
    instances: &[Instance],
    parts: &[Part],
    sheets: &[SheetShape],
) -> (Vec<Placement>, Vec<Unplaced>, ConstructionDiagnostics)
```

---

## Tests

**Futtatás:** `cargo test -p vrs_solver initializer` — 15 teszt, 15/15 PASS  
**Teljes suite:** `cargo test -p vrs_solver` — 121 teszt, 121/121 PASS

### Meglévő tesztek (7 db, mind zöld)

| Teszt neve | Mit ellenőriz |
|---|---|
| `bbox_from_placement_rot0` | bbox visszafejtés rot=0 |
| `bbox_from_placement_rot90` | bbox visszafejtés rot=90 |
| `no_capacity_item_goes_to_unplaced` | nulla kapacitású item unplaced |
| `placed_plus_unplaced_equals_total` | item-count invariant |
| `small_fixture_all_placed` | kis fixture mind elhelyezett |
| `sort_instances_area_descending` | FFD sorrend |
| `rotation_90_only_fits` | 90 fokos rotation elfogad |

### Új SGH-03 tesztek (8 db, mind zöld)

| Teszt neve | Mit ellenőriz |
|---|---|
| `lbf_used_sheet_preferred_over_unused` | Két egyforma sheet: mindkét item sheet_0-ra kerül (used-first policy) |
| `deterministic_two_runs_identical` | Két azonos hívás azonos placementet ad |
| `placed_plus_unplaced_equals_instances` | Item-count invariant vegyes fixture-rel |
| `separator_fallback_succeeds_on_forced_collision` | `try_separator_fallback_for_instance` kényszerített colliding seedből commitálható layoutot csinál |
| `separator_fallback_failure_is_rollback_safe` | 50×50 lap + 40×40 elemek: fallback sikertelen, korábbi placement érintetlen |
| `successful_construction_output_is_valid` | `find_violations()` üres a végső outputon |
| `diagnostics_summary_contains_lbf_separator_fields` | `summary()` tartalmaz: `lbf_scored`, `lbf_clear`, `sep_attempts`, `sep_ok`, `sep_fail`, `sep_commit_reject` |
| `rebuild_placed_bboxes_matches_incremental` | Rebuild eredménye illeszkedik a placements hosszához |

---

## Scope safety

| Tiltott fájl | Módosult? |
|---|---|
| `rust/vrs_solver/src/io.rs` | NEM |
| `rust/vrs_solver/src/adapter.rs` | NEM |
| `rust/vrs_solver/src/optimizer/sheet_elimination.rs` | NEM |
| `rust/vrs_solver/src/optimizer/moves.rs` | NEM |
| `rust/vrs_solver/src/optimizer/multisheet.rs` | NEM |
| `rust/vrs_solver/src/optimizer/score.rs` | NEM |
| Python runner / exact validator | NEM |
| SparrowGH vendor/submodule | NEM |
| Continuous rotation | NEM |
| Solution pool / perturbáció | NEM |

Ellenőrzés alapja: `git diff --stat HEAD` és `git status --porcelain` a verify.sh futás idején (lásd verify log).

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Fájl / Függvény |
|---|---:|---|---|
| SGH-02 dependency gate zöld | PASS | `sgh_02_...v1.md` első sora `PASS`, tartalmaz `SGH-03_STATUS: READY` | `codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md` |
| `ConstructionDiagnostics` bővült LBF/separator mezőkkel | PASS | 6 új pub mező hozzáadva | `initializer.rs` — `ConstructionDiagnostics` struct |
| `summary()` tartalmazza az új mezőket | PASS | `diagnostics_summary_contains_lbf_separator_fields` teszt zöld | `initializer.rs` — `ConstructionDiagnostics::summary()` |
| Clear placement explicit LBF scoringot használ | PASS | `lbf_select_clear_candidate()` hívva `build_initial_layout()` belül | `initializer.rs` — `lbf_select_clear_candidate()` |
| Used-sheet first policy determinisztikus | PASS | `lbf_used_sheet_preferred_over_unused` teszt: mindkét item sheet_0-ra kerül | `initializer.rs` — `lbf_key_better_than()` |
| LBF selection valós candidate/boundary/rotation helpereket használ | PASS | `generate_candidates_with_sheets()`, `rect_within_boundary()`, `dims_for_rotation()`, `placement_anchor_from_rect_min()` direkt hívva | `initializer.rs` — `lbf_select_clear_candidate()` |
| Separator fallback be van kötve construction szinten | PASS | `try_separator_fallback_for_instance()` hívva ha LBF None | `initializer.rs` — `build_initial_layout()` fallback ág |
| Fallback csak commit-gate success után fogad el eredményt | PASS | `best_loss==0.0 \|\| converged` ÉS `validate_for_commit` Ok feltétel | `initializer.rs` — `try_separator_fallback_for_instance()` |
| Fallback failure rollback-safe | PASS | `separator_fallback_failure_is_rollback_safe` teszt: `placed_a` érintetlen | `initializer.rs` — `try_separator_fallback_for_instance()` None ág |
| Placed bbox cache rebuild megtörténik fallback success után | PASS | `rebuild_placed_bboxes()` hívva success ágban | `initializer.rs` — `rebuild_placed_bboxes()` |
| Public construction item-count invariant megmarad | PASS | `placed_plus_unplaced_equals_instances` teszt zöld | `initializer.rs` — `build_initial_layout()` |
| Determinizmus tesztelve | PASS | `deterministic_two_runs_identical` teszt: azonos placement, unplaced, diag. | `initializer.rs` — teszt modul |
| `io.rs`, `adapter.rs`, tiltott fájlok érintetlen | PASS | `git diff --stat HEAD` — csak `initializer.rs` módosult a production kódban | scope safety tábla fent |
| `docs/.../sgh_03_lbf_separator_construction_contract.md` elkészült | PASS | Fájl létezik, mind 8 kötelező szekciót tartalmazza | `docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md` |
| Focused Rust teszt lefutott | PASS | `cargo test -p vrs_solver initializer`: 15/15 PASS; full suite 121/121 PASS | CI output (verify log) |
| Repo verify zöld | PASS | `./scripts/verify.sh ...` exit code 0; DONE smoketest OK | `sgh_03_...integration.verify.log` |

---

## Verification

```bash
# Focused initializer tests
cargo test -p vrs_solver initializer
# Result: 15 passed; 0 failed

# Full test suite
cargo test -p vrs_solver
# Result: 121 passed; 0 failed

# Repo gate
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
# Result: [DONE] smoketest OK (exit 0)
```

Verify log: `codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.verify.log`

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- exit kód: `0`
- futás: 2026-05-25
- parancs: `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md`
- log: `codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.verify.log`
- git: `main@6085a71` (SGH-02 commit, pre-SGH-03 commit)

<!-- AUTO_VERIFY_END -->

SGH-04_STATUS: READY
