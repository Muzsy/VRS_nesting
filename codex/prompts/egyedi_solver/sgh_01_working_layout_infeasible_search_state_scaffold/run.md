# Runner prompt — SGH-01 `sgh_01_working_layout_infeasible_search_state_scaffold`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-01 taskot:

```text
SGH-01 — WorkingLayout / infeasible search state scaffold
```

Ez implementációs scaffold task. A cél: előkészíteni a SparrowGH/Sparrow separator-alapú migrációt egy külön, explicit `WorkingLayout` állapottal, amely ideiglenesen lehet colliding/infeasible, de csak validációs commit gate után válhat elfogadott solver layouttá.

**Ne implementálj separatort. Ne módosítsd a repair/sheet_elimination/initializer algoritmust. Ne építs külső SparrowGH backend adaptert. Ne vendorolj külső kódot.**

---

## Kötelező dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
```

Feltételek:

- a report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `SGH-01_STATUS: READY`.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: SGH-00 migration plan
```

Ilyenkor csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
codex/codex_checklist/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
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
canvases/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_01_working_layout_infeasible_search_state_scaffold.yaml
codex/codex_checklist/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
```

Az `AGENTS.md` outputs szabálya kötelező: csak a YAML step `outputs` listáiban szereplő fájlokat módosíthatod.

---

## Valós kód audit

A megvalósítás előtt nézd át:

```text
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

Külön igazold a reportban:

1. `LayoutState` jelenleg nem explicit infeasible working state.
2. `repair::find_violations()` alkalmas Rust oldali commit gate előszűrőnek.
3. A solver output `io::SolverOutput` schema nem módosul.
4. A `Placement`/`Unplaced` típusok a real runner-output állapothoz tartoznak.

---

## Implementációs irány

Preferált megoldás:

```text
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/mod.rs
```

A `working.rs` tartalmazza a `WorkingLayout` típust és a hozzá tartozó commit gate-et.

A konkrét API-t a valós Rust kódhoz igazítsd, de az alábbi koncepciót valósítsd meg:

```rust
pub struct WorkingLayout {
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub sheet_count: usize,
    pub seed: i64,
}
```

Adj hozzá diagnosztikát/hibatípust, például:

```rust
pub struct WorkingCommitDiagnostics {
    pub violation_count: usize,
    pub overlap_count: usize,
    pub boundary_count: usize,
}

pub enum WorkingCommitError {
    Violations(WorkingCommitDiagnostics),
}
```

A pontos név lehet más, de a funkció nem maradhat el.

Kötelező metódusok vagy ekvivalens API:

```rust
impl WorkingLayout {
    pub fn new(placements: Vec<Placement>, unplaced: Vec<Unplaced>, sheet_count: usize, seed: i64) -> Self;
    pub fn snapshot(&self) -> Self;
    pub fn validate_for_commit(&self, parts: &[Part], sheets: &[SheetShape]) -> Result<WorkingCommitDiagnostics, WorkingCommitError>;
    pub fn validate_and_commit(self, parts: &[Part], sheets: &[SheetShape]) -> Result<(Vec<Placement>, Vec<Unplaced>), WorkingCommitError>;
}
```

`validate_for_commit()` vagy `validate_and_commit()` belül kötelezően használja:

```text
optimizer::repair::find_violations(...)
```

Az elfogadott layout csak akkor adható vissza, ha a violation lista üres.

---

## Tilos

Ne csináld ebben a taskban:

```text
- separator / GLS tracker teljes implementáció
- repair.rs átírása
- sheet_elimination.rs átírása
- initializer.rs LBF fallback
- move operator execution
- IO contract vagy Python runner módosítás
- external Sparrow/SparrowGH backend adapter
- vendor/submodule hozzáadás
- continuous rotation
```

---

## Kötelező tesztelés

Adj unit teszteket a `working.rs` modulban vagy a választott modul mellett.

Minimum:

```text
1. overlapping placements tárolhatók WorkingLayoutban;
2. overlap commit hiba;
3. boundary/sheet violation commit hiba;
4. valid layout commit siker;
5. snapshot/clone/restore determinisztikus;
6. diagnosztika overlap_count és boundary_count mezői helyesek.
```

A tesztek használjanak valós `Placement`, `Unplaced`, `Part`, `Stock`/`SheetShape` struktúrákat és a valós `find_violations()` logikát.

---

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
```

Tartalma:

```text
# SGH-01 WorkingLayout state contract

## Purpose
## Relationship to LayoutState and SolverOutput
## Infeasible working state rules
## Commit gate
## Forbidden implicit conversions
## Snapshot / rollback contract
## Preparation for SGH-02 VrsSeparator
```

---

## Report és checklist

Töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
```

A report első sora csak akkor lehet `PASS`, ha minden DoD teljesült és a verify zöld.

A report tartalmazzon DoD → Evidence Matrixot konkrét fájl/funkció bizonyítékokkal.

---

## Kötelező repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
```

Ha zöld, a report végén szerepeljen:

```text
SGH-02_STATUS: READY
```

Ha fail, ne adj PASS státuszt. Dokumentáld a pontos hibát és a következő javítási lépést.
