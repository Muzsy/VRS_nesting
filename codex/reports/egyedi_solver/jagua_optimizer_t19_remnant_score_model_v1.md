PASS

# Report — JG-19 `jagua_optimizer_t19_remnant_score_model_v1`

## Meta

- **Task slug:** `jagua_optimizer_t19_remnant_score_model_v1`
- **Task id:** JG-19
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t19_remnant_score_model_v1.yaml`
- **Runner:** `codex/prompts/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1/run.md`
- **Fókusz terület:** Remnant/sheet-cost score model V1

---

## Dependency evidence

- `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md` első sora: `PASS`
- JG-18 report tartalmazza: `JG-19_STATUS: READY`
- `generate_candidates_with_sheets` implementálva: `rust/vrs_solver/src/optimizer/candidates.rs`
- `rust/vrs_solver/src/optimizer/boundary.rs` facade aktív

---

## Code audit summary

| Fájl | Találat |
|---|---|
| `score.rs` | `ScoreWeights`, `ObjectiveBreakdown`, `score_layout` — Phase 1 ScoreModel V1 |
| `sheet.rs` | `SheetShape.area`, `has_irregular_outer`, `outer_vertices` — inventory-cost mező hiányzott |
| `multisheet.rs` | `MultiSheetDiagnostics.per_sheet` — per-sheet placed_area elérhető |
| `adapter.rs` | diagnostics `let _ = diag` — score output nem volt bekötve |
| `io.rs` | `Metrics` minimális — score breakdown mező hiányzott |
| `boundary.rs` | facade `rect_within_boundary` — validity-score kapcsolat dokumentált |

**Explicit remnant/inventory-cost input hiánya:** Pre-JG-19 nincs `cost_per_use` mező a `Stock` struktban. V1 döntés: opcionális `cost_per_use: Option<f64>` `#[serde(default)]`-tal.

---

## Sheet cost metadata strategy (V1 proxy)

**Döntés:** Explicit opcionális `cost_per_use: Option<f64>` a `Stock` struktban.

**Indoklás:**
- `Stock` már tartalmaz anyag-specifikus metaadatot (`width`, `height`, `outer_points`).
- `#[serde(default)]` biztosítja a backward-kompatibilitást (hiányzó mező → `None` → `1.0`).
- Nem szükséges teljes inventory/costing séma.

**Változtatás:**
```rust
// sheet.rs — Stock
#[serde(default)]
pub cost_per_use: Option<f64>,

// sheet.rs — SheetShape
pub cost_per_use: f64,

// stock_to_shape()
let cost_per_use = stock.cost_per_use.unwrap_or(1.0).max(0.0);
```

---

## Default weight profile

| Komponens | Default súly | Megjegyzés |
|---|---|---|
| `placed_area_reward` | 1.0 | Jutalom egységnyi² területenként |
| `unplaced_penalty_per_item` | 1_000_000.0 | Erős ösztönzés minden item elhelyezésére |
| `sheet_count_penalty_per_sheet` | 10_000.0 | Alkalmazva: `sheet_cost_total * weight` (JG-19) |
| `overlap_penalty_per_pair` | 1_000_000_000.0 | Érvényességi guard — mindent dominál |
| `boundary_penalty_per_item` | 1_000_000_000.0 | Érvényességi guard — mindent dominál |
| `compactness_weight` | 0.001 | Csak tie-breakerként hat |

**Penalty hierarchy:**
```
overlap/boundary (1e9) >> unplaced (1e6) >> sheet_cost (1e4 * cost_per_use) >> placed_area (1.0) >> compactness (0.001)
```

---

## Implementált változások

### `rust/vrs_solver/src/sheet.rs`

- `Stock.cost_per_use: Option<f64>` hozzáadva (`#[serde(default)]`)
- `SheetShape.cost_per_use: f64` hozzáadva
- `stock_to_shape()`: `cost_per_use = stock.cost_per_use.unwrap_or(1.0).max(0.0)` + `SheetShape` inicializáció
- Minden teszthely `Stock` literal: `cost_per_use: None` hozzáadva (boundary.rs, candidates.rs, repair.rs, initializer.rs, sheet_elimination.rs, bin/*.rs)

### `rust/vrs_solver/src/optimizer/score.rs`

- `ObjectiveBreakdown` bővítve:
  - `sheet_cost_total: f64` — a használt sheet slotok `cost_per_use` összege
  - `usable_area_utilization: f64` — `placed_area / total_used_sheet_area` ∈ [0, 1]
- `score_layout` frissítve: `sheet_count_contribution = sheet_cost_total * weights.sheet_count_penalty_per_sheet`
- 4 új JG-19 teszt:
  - `test_remnant_preference_lower_cost_wins`
  - `test_usable_area_utilization_computed`
  - `test_invalid_layout_dominates_over_remnant_benefit`
  - `test_backward_compat_default_cost_equals_sheet_count`
- `test_is_better_lower_cost_wins` literal fixálva: `sheet_cost_total: 1.0, usable_area_utilization: 0.0`

### `rust/vrs_solver/src/io.rs`

- `ScoreBreakdownOutput` struct hozzáadva (`#[derive(Debug, Serialize)]`)
- `SolverOutput.score_breakdown: Option<ScoreBreakdownOutput>` hozzáadva (`#[serde(skip_serializing_if = "Option::is_none")]`)

### `rust/vrs_solver/src/adapter.rs`

- `use crate::io::ScoreBreakdownOutput` és `use crate::optimizer::score::ScoreModel` importok
- Phase 1 profil esetén: score kiszámítva placement/unplaced referenciákon (move előtt), `score_breakdown` bekötve a `SolverOutput`-ba
- `_unsupported_output`: `score_breakdown: None` hozzáadva

### `rust/vrs_solver/src/optimizer/multisheet.rs`

- `SheetSummary.sheet_usable_area: f64` hozzáadva — `SheetShape.area`-ból

---

## Backward-compatibility

**`sheet_count_contribution` képlet változás:**
- Pre-JG-19: `sheet_count_used * sheet_count_penalty_per_sheet`
- JG-19: `sheet_cost_total * sheet_count_penalty_per_sheet`
- Default `cost_per_use = None → 1.0` esetén: `sheet_cost_total = sheet_count_used * 1.0 = sheet_count_used`
- **Numerikusan azonos minden meglévő fixture-nél.**

Bizonyítva: `test_backward_compat_default_cost_equals_sheet_count`

---

## Sheet-choice döntési példa

Forgatókönyv: 3 × 50×50-es item, két 200×200-as sheet:
- Sheet 0: `cost_per_use = 1.0` (teljes lap)
- Sheet 1: `cost_per_use = 0.2` (remnant)

| Elhelyezés | sheet_cost_total | sheet_cost_contribution | total_cost |
|---|---|---|---|
| Itemek teljes lapon | 1.0 | 1.0 × 10,000 = 10,000 | ~5,000 |
| Itemek remnant lapon | 0.2 | 0.2 × 10,000 = 2,000 | ~-3,000 |

**Remnant előnyben részesül** (alacsonyabb total_cost).

---

## Invalid-vs-valid dominancia bizonyítéka

`test_invalid_layout_dominates_over_remnant_benefit` (score.rs):
- Valid layout teljes lapon: `total_cost ≈ -500`
- Átfedő layout remnant lapon (cost=0.001): `overlap_contribution = 1e9` → `total_cost >> 1e9`
- **Érvényes layout mindig nyer**, függetlenül a remnant előnytől.

---

## Rectangular regression evidence

Összes pre-JG-19 Rust unit teszt átment:
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml` → **97/97 PASS** (93 prior + 4 new JG-19)
- `score.rs` meglévő tesztek: PASS (backward-compat default cost)
- `boundary.rs`, `candidates.rs`, `repair.rs`, `initializer.rs`, `sheet_elimination.rs`: PASS

JG-18 regression:
- `python3 scripts/smoke_jagua_irregular_candidate_generation.py` → **10/10 PASS**

---

## Fixtures

`tests/fixtures/egyedi_solver/jagua_remnant_score_model_v1.json`:
- `solver_profile: "jagua_optimizer_phase1_outer_only"`
- Stocks: `regular_200x200` (`cost_per_use: 1.0`), `remnant_200x200` (`cost_per_use: 0.2`)
- Parts: `square_50` qty=3, rotations=[0]
- Hole-free, Phase 2 scope-on belül

---

## Smoke results

`python3 scripts/smoke_jagua_remnant_score_model_v1.py` → **12/12 PASS**

Kiemelések:
```
[Check 5: usable_area_utilization in (0, 1]]
  PASS: usable_area_utilization=0.187500 in (0, 1] for placed=3

[Check 7: Remnant preference score evidence]
  PASS: remnant total_cost=-3000.00 < regular total_cost=5000.00
        (sheet_cost_total: remnant=0.20, regular=1.00)

[Check 8: sheet_cost_contribution ratio matches cost ratio]
  PASS: remnant sc_contrib=2000.00, regular sc_contrib=10000.00, ratio=0.200 matches cost ratio=0.200

=== RESULTS: 12 PASS, 0 FAIL ===
OVERALL: PASS
```

---

## Documentation

- `docs/egyedi_solver/jagua_remnant_score_model_v1.md` — létrejött
- `docs/solver_io_contract.md` — JG-19 "Sheet-cost score model" szakasz hozzáadva:
  - `cost_per_use` mező leírás
  - `score_breakdown` JSON példa
  - `sheet_count_contribution` szemantika
  - `usable_area_utilization`
  - Penalty hierarchy
  - V1 korlátozások

---

## Deviations from plan

Nincs érdemi eltérés. A `multisheet.rs` `SheetSummary.sheet_usable_area` opcionálisan hozzáadva diagnosztikai célra (tervben nem szerepelt explicit, de koherens JG-19 scope-on belül).

---

## Verify

```
cargo test --manifest-path rust/vrs_solver/Cargo.toml  →  97/97 PASS
python3 scripts/smoke_jagua_remnant_score_model_v1.py  →  12/12 PASS
python3 scripts/smoke_jagua_irregular_candidate_generation.py  →  10/10 PASS
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
```

---

JG-20_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T18:38:39+02:00 → 2026-05-24T18:41:34+02:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.verify.log`
- git: `main@c7eff7a`
- módosított fájlok (git status): 23

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     |  32 ++---
 docs/solver_io_contract.md                         |  63 +++++++++
 rust/vrs_solver/src/adapter.rs                     |  24 +++-
 rust/vrs_solver/src/bin/jagua_adapter_smoke.rs     |   1 +
 .../src/bin/jagua_irregular_sheet_spike.rs         |   1 +
 rust/vrs_solver/src/io.rs                          |  22 ++++
 rust/vrs_solver/src/optimizer/boundary.rs          |   2 +
 rust/vrs_solver/src/optimizer/candidates.rs        |   2 +
 rust/vrs_solver/src/optimizer/initializer.rs       |   2 +-
 rust/vrs_solver/src/optimizer/multisheet.rs        |   4 +
 rust/vrs_solver/src/optimizer/repair.rs            |   1 +
 rust/vrs_solver/src/optimizer/score.rs             | 145 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sheet_elimination.rs |   1 +
 rust/vrs_solver/src/sheet.rs                       |  14 ++
 14 files changed, 294 insertions(+), 20 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M docs/solver_io_contract.md
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/bin/jagua_adapter_smoke.rs
 M rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/boundary.rs
 M rust/vrs_solver/src/optimizer/candidates.rs
 M rust/vrs_solver/src/optimizer/initializer.rs
 M rust/vrs_solver/src/optimizer/multisheet.rs
 M rust/vrs_solver/src/optimizer/repair.rs
 M rust/vrs_solver/src/optimizer/score.rs
 M rust/vrs_solver/src/optimizer/sheet_elimination.rs
 M rust/vrs_solver/src/sheet.rs
?? canvases/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t19_remnant_score_model_v1.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1/
?? codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
?? codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.verify.log
?? docs/egyedi_solver/jagua_remnant_score_model_v1.md
?? scripts/smoke_jagua_remnant_score_model_v1.py
?? tests/fixtures/egyedi_solver/jagua_remnant_score_model_v1.json
```

<!-- AUTO_VERIFY_END -->
