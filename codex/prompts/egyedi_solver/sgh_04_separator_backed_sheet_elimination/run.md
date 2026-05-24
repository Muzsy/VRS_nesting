# Runner prompt — SGH-04 `sgh_04_separator_backed_sheet_elimination`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-04 taskot:

```text
SGH-04 — Separator-backed sheet elimination V2
```

Ez belső Rust optimizer migrációs task. A cél: a SparrowGH bin-reduction mintáját portolni a saját VRS `SheetEliminationEngine` rétegbe úgy, hogy a target sheet itemjeit largest-first sorrendben visszaossza alacsonyabb indexű sheetekre, először LBF clear reinsert próbával, majd szükség esetén `WorkingLayout` + `VrsSeparator` fallbackkel.

**Ne építs külső SparrowGH backendet. Ne vendorolj külső kódot. Ne módosíts Python runnert, exact validatort vagy SolverOutput IO contractot.**

---

## Kötelező dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
```

Feltételek:

- a report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `SGH-04_STATUS: READY`.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: SGH-03 LBF + separator construction integration
```

Ilyenkor csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
codex/codex_checklist/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
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
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
canvases/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_04_separator_backed_sheet_elimination.yaml
codex/codex_checklist/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
```

Az `AGENTS.md` outputs szabálya kötelező: csak a YAML step `outputs` listáiban szereplő fájlokat módosíthatod.

---

## Valós kód audit

A megvalósítás előtt nézd át:

```text
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/stopping.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

A reportban külön igazold:

1. A jelenlegi `SheetEliminationEngine::run()` V1 működését és korlátait.
2. A `compute_sheet_count_used()` `max(sheet_index)+1` contractját.
3. Miért kell SGH-04-ben highest-used target sheetet választani, ha nincs safe reindexing.
4. Hogyan fogod kizárni a target/higher sheet reuse-t.
5. A `VrsSeparator` jelenlegi candidate scope-ját, és hogy kell-e optional allowed-sheet filter.
6. Accepted output commit gate: `find_violations()` / `WorkingLayout::validate_for_commit()`.

---

## Implementációs irány

### 1. Sheet-count reducing target

A `select_target_sheet()` V2-ben targetként a legmagasabb használt sheetet válassza, vagy vezess be külön V2 helper nevet. A reportban dokumentáld, hogy ez VRS-specifikus adaptáció a SparrowGH least-loaded bin választásához képest, mert a VRS `sheet_count_used` metrikája `max(sheet_index)+1`.

Ne legyen silent non-reducing elimination attempt.

### 2. Receiving sheets restriction

A target sheet itemjeit kizárólag alacsonyabb sheetekre lehet visszatenni:

```text
sheet_index < target_sheet
```

Minden candidate generálás, LBF scoring és separator fallback commit gate tartsa be ezt.

### 3. Largest-first displaced queue

A target sheetről eltávolított itemek sorrendje:

```text
area desc → max_dim desc → instance_id asc
```

### 4. LBF clear reinsertion

Minden displaced itemhez először LBF clear reinsert:

```text
used receiving sheet first → lower y → lower x → lower sheet_index → stable rotation order
```

Valós VRS helpereket használj:

```text
generate_candidates_with_sheets()
rect_within_boundary()
dims_for_rotation()
placement_anchor_from_rect_min()
PlacedBbox::overlaps()
bbox_from_placement()
```

### 5. Separator-backed fallback

Ha LBF nem talál clear helyet:

1. Válassz deterministic receiving sheetet az allowed lower-index sheetek közül, lehetőleg a legtöbb becsült free area alapján.
2. Adj hozzá seed placementet.
3. Építs `WorkingLayout`-ot.
4. Futtasd `VrsSeparator::run()`-t.
5. Fogadd el csak akkor, ha:
   - `best_loss == 0.0` vagy `converged == true`,
   - `validate_for_commit(parts, sheets)` Ok,
   - nincs placement `sheet_index >= target_sheet`,
   - `find_violations()` üres.

### 6. Optional separator allowed-sheet filter

Preferált: bővítsd `VrsSeparatorConfig`-ot backward-compatible optional fielddel:

```rust
pub allowed_sheet_indices: Option<Vec<usize>>
```

vagy ekvivalens megoldással. Default: `None`.

`VrsSeparator::run()` candidate generálásakor, ha a filter aktív, csak ezekre a sheetekre adhat relocation candidate-et.

Ha nem ezt választod, akkor a commit gate-ben kötelező rejectálni minden target/higher sheetet használó separator eredményt, és ezt reportban indokolni.

### 7. Diagnostics

Bővítsd `SheetEliminationDiagnostics`-ot úgy, hogy mérhető legyen:

```text
displaced items count
LBF reinsertion successes
separator fallback attempts
separator fallback successes
separator fallback failures
commit gate rejections
target/higher sheet reuse rejections
receiving sheet count
```

A `summary()` tartalmazza az új mezőket.

### 8. Commit/rollback

Commit csak akkor:

```text
minden displaced item visszakerült
nem használ target/higher sheetet
find_violations üres
sheet_count_used csökkent
placed+unplaced invariant megmaradt
```

Minden más eset rollback az eredeti snapshotra. Partial success nincs.

---

## Tilos

Ne csináld ebben a taskban:

```text
- külső SparrowGH backend adapter
- Sparrow/SparrowGH vendor/submodule
- Python runner vagy exact validator módosítás
- io.rs / SolverOutput contract módosítás
- adapter.rs módosítás
- score.rs objective modell átírása
- moves.rs transfer/swap execution implementáció
- solution pool / perturbáció / multi-restart
- continuous rotation
- LV8 vagy nagy benchmark kampány
- cavity-prepack
- unsafe sheet reindexing
```

Engedélyezett production módosítások:

```text
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/separator.rs
```

---

## Kötelező unit tesztek

Minimum:

```text
1. meglévő sheet_elimination tesztek továbbra is zöldek;
2. target selection highest used sheetet választ;
3. redistribution nem használ target sheetet;
4. redistribution nem használ target feletti unused sheetet;
5. egyszerű 2 sheet → 1 sheet elimináció PASS;
6. impossible elimination rollback-safe és byte-identical placement snapshot;
7. separator-backed fallback aktiválható és valid layoutot ad egy célzott fixture/helper tesztben;
8. separator fallback rejectálódik target/higher sheet reuse esetén;
9. diagnostics summary tartalmazza az új mezőket;
10. final committed output find_violations szerint valid.
```

---

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md
```

Kötelező szekciók:

```text
# SGH-04 Separator-backed sheet elimination contract

## Purpose
## Current SheetElimination V1 gap
## SparrowGH bin-reduction mapping
## VRS sheet_count_used constraint
## Target sheet selection V2
## Receiving sheet restriction
## LBF reinsertion V2
## Separator-backed fallback V1
## Commit/rollback gates
## Diagnostics
## Scope exclusions
## Preparation for SGH-05
```

---

## Report és checklist

Töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
```

A report első sora csak akkor lehet `PASS`, ha minden DoD teljesült és a verify zöld.

A report tartalmazzon DoD → Evidence Matrixot konkrét fájl/funkció bizonyítékokkal.

---

## Teszt / gate

Futtasd legalább:

```bash
cargo test -p vrs_solver sheet_elimination separator
```

vagy a helyi cargo által elfogadott ekvivalens célzott Rust tesztet.

Majd kötelezően:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
```

Ha a verify zöld, a report végén szerepeljen:

```text
SGH-05_STATUS: READY
```
