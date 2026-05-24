# SGH-04 — Separator-backed sheet elimination V2

## Kontextus

SGH-00 lezárta a Sparrow/SparrowGH kódauditot és a VRS migrációs tervet. A stratégiai döntés változatlan:

```text
Do not run SparrowGH as an external backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port / reimplement the selected algorithms inside the VRS jagua_optimizer.
```

SGH-01 bevezette a `WorkingLayout`-ot, amely explicit, akár infeasible keresési állapotot tarthat, de csak commit gate után adhat elfogadott outputot.

SGH-02 bevezette a belső `VrsCollisionTracker` + `VrsSeparator` V1 réteget.

SGH-03 bekötötte a separatort az initial constructionbe: LBF-scored clear placement után separator fallback indulhat `WorkingLayout`-on, accepted output pedig csak `validate_for_commit()` után lehet.

SGH-04 célja a SparrowGH `bp_explore.rs` / bin-reduction szemlélet első VRS-portja: a meglévő `SheetEliminationEngine` V1-et úgy kell továbbfejleszteni, hogy a sheet elimináció ne csak egyszerű collision-free reinsertet próbáljon, hanem separator-backed redistributiont is.

Ez még **nem** solution pool, perturbáció, multi-restart, large benchmark suite vagy külső SparrowGH adapter task.

---

## Task cél

Fejleszd tovább a jelenlegi `rust/vrs_solver/src/optimizer/sheet_elimination.rs` V1 logikát SparrowGH-szerű V2 irányba:

```text
valid layout snapshot
    ↓
select sheet to eliminate, sheet-count reducing módon
    ↓
remove displaced items from target sheet
    ↓
largest-first redistribution to remaining lower-index sheets
    ↓
per-item LBF clear reinsertion
    ↓
if LBF fails: separator-backed fallback on WorkingLayout
    ↓
commit only if no target sheet reuse, no violations, sheet_count_used decreased
    ↓
else full rollback
```

A cél nem pusztán az, hogy egy toy esetet megoldjon, hanem hogy a VRS-ben megjelenjen a SparrowGH bin-reduction alapmintája:

```text
bin/sheet elimination attempt
redistribute displaced items
separator repair
commit/rollback discipline
```

---

## Kötelező dependency gate

SGH-04 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-04_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a report/checklist dependency evidence részét frissítsd.

---

## Kötelező repo anchorok

Olvasd el és auditáld, ne feltételezd:

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
codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md
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

---

## Kötelező kódaudit megállapítások

A reportban rögzítsd legalább ezeket:

1. `SheetEliminationEngine::run()` jelenleg legfeljebb egy eliminációs próbát futtat, snapshot/rollback discipline-nel.
2. A jelenlegi `try_eliminate()` eltávolítja a target sheet itemjeit, majd egyszerű collision-free candidate loopbal próbálja visszatenni őket.
3. A jelenlegi V1 nem használ `WorkingLayout`-ot, `VrsSeparator`-t vagy separator fallbacket a displaced itemek visszaosztásánál.
4. A VRS `compute_sheet_count_used()` contract `max(sheet_index)+1`, ezért sheet-count csökkentéshez V2-ben alapértelmezés szerint a legmagasabb használt sheetet kell eliminálni, vagy explicit, bizonyítottan safe reindexinget kell implementálni. SGH-04-ben default: **nincs reindexing**, ezért target sheet = highest used sheet.
5. Candidate redistribution alatt a target sheet és az annál magasabb indexű sheetek nem használhatók, különben `sheet_count_used` nem csökken.
6. A jelenlegi `VrsSeparator` alapból minden sheeten generálhat candidate-et; SGH-04-ben vagy be kell vezetni egy optional allowed-sheet filtert, vagy a separator fallback eredményét commit előtt szigorúan rejectálni kell, ha target/higher sheetet használ. Preferált: optional allowed-sheet filter default kompatibilis módon.
7. Accepted output továbbra is csak `find_violations()` / `WorkingLayout::validate_for_commit()` után lehet.
8. `io.rs`, `adapter.rs`, Python runner, exact validator és külső backend nem módosulhat.

---

## Tervezett implementáció

### 1. Sheet-count reducing target selection

A VRS jelenlegi `sheet_count_used` metrikája:

```rust
max(sheet_index) + 1
```

Ezért SGH-04-ben az eliminációs target legyen a **highest used sheet**. Ez garantálja, hogy ha minden target item sikeresen alacsonyabb sheetre kerül, akkor `sheet_count_used` ténylegesen csökken.

Elvárás:

```text
- select_target_sheet() vagy új helper dokumentáltan highest-used targetet választ V2-ben;
- a reportban magyarázd el, miért térünk el a tiszta SparrowGH least-loaded bin választástól;
- nincs silent non-reducing elimination attempt;
- nincs sheet reindexing SGH-04-ben, kivéve ha teljesen bizonyítottan safe és külön dokumentált.
```

### 2. Redistribution csak lower-index receiving sheetekre

A target sheet eltávolítása után minden displaced itemet csak ezekre szabad visszarakni:

```text
sheet_index < target_sheet
```

Ne használj:

```text
target_sheet
sheet_index > target_sheet
unused higher sheet
```

Ez legyen explicit helper vagy explicit filter:

```text
allowed_receiving_sheets = 0..target_sheet
```

Ha nincs receiving sheet, rollback.

### 3. Largest-first displaced queue

A target sheetről levett itemeket determinisztikusan rendezd:

```text
area desc
max_dim desc
instance_id asc
```

Ez közelebb áll a SparrowGH largest-first redisztribúciójához, és stabil futást ad.

### 4. LBF clear reinsertion

Minden displaced itemhez először próbálj collision-free LBF reinsertet az allowed receiving sheetekre.

Elvárt scoring:

```text
primary: used receiving sheet előnyben unused receiving sheet előtt
secondary: kisebb y
tertiary: kisebb x
quaternary: kisebb sheet_index
stable rotation order
```

Használj valós VRS helpereket:

```text
generate_candidates_with_sheets()
rect_within_boundary()
dims_for_rotation()
placement_anchor_from_rect_min()
PlacedBbox::overlaps()
bbox_from_placement()
```

### 5. Separator-backed fallback

Ha LBF clear reinsertion nem talál helyet, próbálj separator fallbacket:

1. Válassz determinisztikus receiving sheetet az allowed receiving sheetek közül, lehetőleg a legtöbb becsült free area alapján.
2. Seedeld be az aktuális displaced itemet azon a sheeteen, lehetőleg origin/bbox-min `(0,0)` vagy a legjobb boundary-valid seed ponton.
3. Építs `WorkingLayout`-ot az aktuális base placements + seed placement alapján.
4. Futtasd `VrsSeparator::run()`-t.
5. Csak akkor fogadd el, ha:
   - `best_loss == 0.0` vagy `converged == true`,
   - `validate_for_commit(parts, sheets)` sikeres,
   - egyetlen placement sem használ `sheet_index >= target_sheet`,
   - `find_violations()` üres,
   - a végső `sheet_count_used` csökkenhet.
6. Siker esetén cseréld a working placement state-et a separator eredményére és rebuildeld a bbox cache-t.
7. Failure esetén rollback az eliminációs attempt előtti snapshotra.

### 6. Optional allowed-sheet filter a separatorhoz

Preferált megoldás: bővítsd `VrsSeparatorConfig`-ot backward-compatible módon egy optional receiving sheet filterrel, például:

```rust
pub allowed_sheet_indices: Option<Vec<usize>>
```

vagy ekvivalens, determinisztikus struktúrával.

Default értéke `None`, hogy SGH-02/SGH-03 viselkedés ne változzon.

`VrsSeparator::run()` candidate generálásakor, ha a filter be van állítva, csak engedélyezett sheetekre adhat relocation candidate-et.

Ha ezt a módosítást nem tudod biztonságosan megcsinálni, akkor a fallback eredmény commit gate-jében kötelező szigorúan rejectálni minden target/higher sheet használatot. A reportban indokold, melyik megoldást választottad.

### 7. Diagnostics bővítés

Bővítsd `SheetEliminationDiagnostics`-ot mérhető mezőkkel, például:

```rust
pub displaced_items: usize,
pub reinsertion_lbf_successes: usize,
pub reinsertion_separator_attempts: usize,
pub reinsertion_separator_successes: usize,
pub reinsertion_separator_failures: usize,
pub commit_gate_rejections: usize,
pub rejected_target_or_higher_sheet_reuse: usize,
pub receiving_sheet_count: usize,
```

A pontos nevek eltérhetnek, de a reportban és tesztekben legyen egyértelmű:

```text
hány itemet vettünk le
hány ment vissza LBF-fel
hány separator fallback indult
hány separator fallback sikerült
hány rollback/reject történt
miért nem lett commit
```

`summary()` tartalmazza az új mezőket.

### 8. Commit/rollback gate

A teljes elimináció csak akkor commitolható, ha minden feltétel teljesül:

```text
all displaced items reinserted
no placement uses sheet_index >= target_sheet
find_violations() empty
WorkingLayout::validate_for_commit() Ok, ha WorkingLayout-ot használtál
compute_sheet_count_used(new_placements) < compute_sheet_count_used(original_placements)
placed.len() + unplaced.len() invariant megmarad
```

Minden más esetben rollback. Partial success nem commitolható.

---

## Tilos ebben a taskban

Ne csináld:

```text
- külső SparrowGH backend adapter
- Sparrow/SparrowGH vendor/submodule hozzáadás
- Python runner vagy exact validator módosítás
- io.rs / SolverOutput contract módosítás
- adapter.rs módosítás
- score.rs objective modell átírása
- moves.rs transfer/swap execution implementáció
- solution pool / perturbáció / multi-restart
- continuous rotation
- LV8 vagy nagy benchmark kampány
- cavity-prepack
- sheet reindexing, ha nincs külön bizonyított safety gate identical sheets/cost mellett
```

Engedélyezett production módosítások:

```text
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/separator.rs     # csak optional allowed-sheet filter miatt, backward-compatible módon
```

Dokumentáció/report/checklist fájlok természetesen módosíthatók a YAML outputs szerint.

---

## Kötelező unit tesztek

Adj vagy frissíts Rust unit teszteket, lehetőleg `sheet_elimination.rs` és szükség esetén `separator.rs` tesztmodulban.

Minimum tesztek:

```text
1. SGH-03 előtti sheet_elimination tesztek továbbra is zöldek.
2. target selection highest used sheetet választ sheet-count reducing okból.
3. redistribution nem használ target sheetet.
4. redistribution nem használ target feletti unused sheetet.
5. egyszerű 2 sheet → 1 sheet elimináció továbbra is PASS.
6. impossible elimination rollback-safe és byte-identical placement snapshotot ad vissza.
7. separator-backed fallback képes olyan esetben segíteni, ahol LBF clear reinsert nem talál helyet, de separator feloldható ütköző seedből.
8. separator fallback eredménye rejectálódik, ha target/higher sheetet használna.
9. diagnostics summary tartalmazza az új SGH-04 mezőket.
10. final committed output `find_violations()` szerint valid.
```

Ha a 7. pont természetes fixture-rel nehezen aktiválható, lehet privát helper unit tesztet írni `sheet_elimination.rs` modulon belül, de valós `WorkingLayout`, `VrsSeparator`, `Part`, `SheetShape`, `Placement` típusokkal dolgozzon, ne mockolt commit gate-tel.

---

## Kötelező dokumentáció

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

## Done feltételek

PASS csak akkor adható, ha:

```text
- dependency gate zöld;
- target selection sheet-count reducing módon működik;
- redistribution target/higher sheet reuse nélkül működik;
- separator fallback legalább teszt szinten be van kötve;
- rollback discipline bizonyított;
- output validáció kapu megmaradt;
- Rust focused tesztek zöldek;
- repo verify zöld;
- nincs külső backend/vendor;
- report végén szerepel: SGH-05_STATUS: READY.
```
