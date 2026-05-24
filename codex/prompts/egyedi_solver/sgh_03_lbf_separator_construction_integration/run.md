# Runner prompt — SGH-03 `sgh_03_lbf_separator_construction_integration`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-03 taskot:

```text
SGH-03 — LBF + separator fallback construction integration
```

Ez belső Rust optimizer integrációs task. A cél: a SGH-02-ben elkészült `VrsSeparator` első kontrollált bekötése az initial construction szintjére. A konstrukció továbbra is valid accepted outputot adhat csak, de belső fallbackként már használhat `WorkingLayout`-alapú separator repairt.

**Ne építs külső SparrowGH backendet. Ne vendorolj külső kódot. Ne módosítsd a sheet elimination, moves, IO contract vagy Python validator réteget.**

---

## Kötelező dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

Feltételek:

- a report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `SGH-03_STATUS: READY`.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: SGH-02 VrsSeparator + VrsCollisionTracker V1
```

Ilyenkor csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
codex/codex_checklist/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
```

---

## Kötelező olvasmányok

Olvasd el és kövesd:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
canvases/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_03_lbf_separator_construction_integration.yaml
codex/codex_checklist/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
```

Az `AGENTS.md` outputs szabálya kötelező: csak a YAML step `outputs` listáiban szereplő fájlokat módosíthatod.

---

## Valós kód audit

A megvalósítás előtt nézd át:

```text
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

A reportban külön igazold:

1. `build_initial_layout()` jelenlegi candidate elfogadási módját.
2. `generate_candidates_with_sheets()` determinisztikus candidate sorrendjét.
3. `ConstructionDiagnostics` jelenlegi és új mezőit.
4. `VrsSeparator::run()` és `WorkingLayout` commit gate kapcsolatát.
5. `repair::find_violations()` továbbra is accepted-output gate.
6. Solver IO contract nem változhat.

---

## Implementációs irány

### 1. Diagnostics

Bővítsd a `ConstructionDiagnostics`-ot LBF/separator fallback számlálókkal, például:

```rust
pub lbf_candidates_scored: usize,
pub lbf_clear_accepts: usize,
pub separator_fallback_attempts: usize,
pub separator_fallback_successes: usize,
pub separator_fallback_failures: usize,
pub separator_fallback_rejected_by_commit_gate: usize,
```

Frissítsd a `summary()`-t.

### 2. LBF-scored clear selection

A clear placement választás ne csak első valid jelölt legyen. Implementálj determinisztikus scoringot:

```text
used sheet előnyben unused sheet előtt
kisebb y jobb
kisebb x jobb
kisebb sheet_index jobb
stabil rotation order
```

Használd:

```text
generate_candidates_with_sheets()
rect_within_boundary()
dims_for_rotation()
placement_anchor_from_rect_min()
PlacedBbox::overlaps()
```

### 3. Separator fallback

Ha nincs clear LBF candidate:

1. Készíts seed placementet determinisztikusan.
2. Építs `WorkingLayout`-ot az eddigi placements + seed placement alapján.
3. Futtasd `VrsSeparator::run()`-t.
4. Csak akkor fogadd el, ha `diag.best_loss == 0.0` vagy `diag.converged == true`, és `validate_for_commit(parts, sheets)` sikeres.
5. Siker esetén cseréld a placement listát a commitolható eredményre, és rebuildeld a `placed_bboxes` cache-t.
6. Sikertelenség esetén rollback-safe módon hagyd változatlanul az előző state-et, majd az aktuális item legyen unplaced.

### 4. Bbox cache rebuild

Mivel fallback során korábbi placementek is mozdulhatnak, legyen helper vagy ekvivalens logika a `placed_bboxes` újraépítésére a teljes `placements` listából.

---

## Tilos

Ne csináld ebben a taskban:

```text
- sheet_elimination.rs módosítás
- moves.rs transfer/swap execution implementáció
- multisheet.rs átírás
- score.rs objective modell átírás
- SolverOutput / io.rs módosítás
- adapter.rs módosítás
- Python runner vagy exact validator módosítás
- külső SparrowGH backend adapter
- Sparrow/SparrowGH vendor/submodule hozzáadás
- continuous rotation
- solution pool / perturbáció
- nagy benchmark suite vagy LV8 futtatási kampány
```

---

## Kötelező unit tesztek

Adj vagy frissíts Rust unit teszteket, lehetőleg `initializer.rs`-ben.

Minimum:

```text
1. meglévő initializer tesztek továbbra is zöldek;
2. LBF scorer használt sheetet preferál unused sheet előtt;
3. build_initial_layout determinisztikus;
4. placed + unplaced == expanded instances;
5. separator fallback helper sikeres egy kényszerített colliding seedből;
6. fallback failure rollback-safe;
7. successful construction output find_violations szerint valid;
8. diagnostics summary tartalmazza az új LBF/separator mezőket.
```

Ha a public `build_initial_layout()` természetes fixture-jein a fallback nem aktiválódik, tesztelheted a fallbacket privát helperen keresztül ugyanazon modul unit tesztjeiben.

---

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
```

Kötelező szekciók:

```text
# SGH-03 LBF + separator construction contract

## Purpose
## Current initializer gap
## LBF candidate scoring V1
## Separator fallback V1
## Commit/rollback rules
## Diagnostics
## Scope exclusions
## Preparation for SGH-04
```

---

## Report és checklist

Töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
```

A report első sora csak akkor lehet `PASS`, ha minden DoD teljesült és a verify zöld.

A report tartalmazzon DoD → Evidence Matrixot konkrét fájl/funkció bizonyítékokkal.

---

## Teszt / gate

Futtasd legalább:

```bash
cargo test initializer separator working
```

vagy a helyi cargo által elfogadott ekvivalens célzott Rust tesztet.

Majd kötelezően:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
```

Ha a verify zöld, a report végén szerepeljen:

```text
SGH-04_STATUS: READY
```
