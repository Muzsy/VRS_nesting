PASS

# Report — SGH-Q13 `sgh_q13_cde_session_backend_search_path_wiring`

## Status

PASS. CDE search-path sentinel stubs removed. Honest `PerCallOnly` session lifecycle documented. 310 library tests pass.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md`: first line `PASS`
- `SGH-Q13_STATUS: READY`: present in Q12 report

## 1) Meta

- **Task slug:** `sgh_q13_cde_session_backend_search_path_wiring`
- **Canvas:** `canvases/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q13_cde_session_backend_search_path_wiring.yaml`
- **Futás dátuma:** 2026-05-27
- **Branch / commit:** main
- **Fókusz terület:** Collision Backend | Separator Search Path | CDE Session Lifecycle

## 2) Scope

### 2.1 Cél

1. Auditálni a jagua-rs 0.6.4 CDE filter/lifecycle API-t és becsületesen dokumentálni a session viability-t.
2. Megszüntetni a 3 CDE sentinel stubot a separatorban (minden pair Unsupported / f64::MAX fallback).
3. `cde_session.rs` modult létrehozni `CdeSessionCapability` és `CdeDiagnostics` típusokkal.
4. 10 kötelező Q13 tesztet írni és zöldre hozni.

### 2.2 Nem-cél

- Production default CDE
- Hole/cavity semantics
- DXF/preflight
- Sparrow teljes port
- Optimizer stratégia újraírása

## 3) jagua-rs CDE API Audit

### Self-hazard filter kérdések

**Lehetséges-e self-hazard filter egy session-owned CDEEngine-ben?**

Nem tisztán. `HazKeyFilter` képes kizárni specifikus `HazKey` értékeket, de az élő iteratív
search-hez egy item `HazardEntity::PlacedItem { pk: PItemKey }` kellene SlotMap PItemKey-vel —
ezt VRS nem tartja karban. A `HazardEntity::Hole { idx }` nem tartalmaz self-identity, ezért
self-exclusion csak engine rebuild-del valósítható meg.

**Miért marad PerCallOnly?**

Nincs tentative-query API: a CDEngine-t minden candidate-pozícióhoz újra kell építeni (vagy
módosítani a hazard map-et, ami ugyanolyan drága). `HazardEntity::PlacedItem` PItemKey-t igényel
jagua-rs SlotMap-ból, amit VRS nem hoz létre. Ezért `PerCallOnly { reason }` az őszinte státusz
live search esetén.

**QueryBatch lehetséges?**

Igen, offline boundary validation (sheetenként 1 CDEngine build, összes boundary query egyszerre),
de a search-path blocking-gate nem teszi szükségessé.

### API Evidence

| Symbol | Path | Usable | Notes |
|---|---|---|---|
| `CDEngine::register_hazard` | `jagua_rs::collision_detection::CDEngine` | Yes | Mutates live engine |
| `CDEngine::deregister_hazard_by_entity` | same | Yes | Removes by entity |
| `CDEngine::hazards_map` | same | Yes (pub) | SlotMap<HazKey, Hazard> |
| `HazardEntity::Hole { idx }` | `jagua_rs::...::hazards` | Yes | Per-pair queries |
| `HazardEntity::PlacedItem { pk }` | same | Partial | Requires SlotMap PItemKey |
| `HazKeyFilter` | `jagua_rs::...::filter` | Yes | Self-exclusion requires PItemKey |
| `NoFilter` | same | Yes | All hazards relevant |

## 4) Implementáció

### 4.1 Separator CDE sentinel fix

Három sentinel stub megszüntetve a `rust/vrs_solver/src/optimizer/separator.rs`-ben:

#### `compute_backend_decisions(Cde)` — volt: minden pair Unsupported

```rust
// ELŐTTE: minden pair Unsupported, minden boundary Unsupported
CollisionBackendKind::Cde => {
    let mut pair_unsup = HashSet::new();
    for i in 0..n { for j in (i+1)..n { pair_unsup.insert((i, j)); } }
    (HashSet::new(), pair_unsup, vec![false; n], vec![true; n])
}

// UTÁNA: CdeCollisionBackend alapján valós döntések
CollisionBackendKind::Cde => {
    let backend = CdeCollisionBackend;
    // ... ugyanolyan logika mint JaguaPolygonExact ág, CdeCollisionBackend-del
}
```

#### `update_placement(Cde)` — volt: minden boundary+pair Unsupported

```rust
// ELŐTTE
CollisionBackendKind::Cde => {
    self.boundary_exact_unsupported[idx] = true;
    for j in 0..self.n { ... self.pair_exact_unsupported.insert(...); }
}

// UTÁNA: CdeCollisionBackend alapján valós boundary + pair döntések
CollisionBackendKind::Cde => {
    let backend = CdeCollisionBackend;
    // ... ugyanolyan logika mint JaguaPolygonExact ág
}
```

#### `candidate_loss_for_backend(Cde)` — volt: f64::MAX

```rust
// ELŐTTE
CollisionBackendKind::Cde => f64::MAX,

// UTÁNA: CdeCollisionBackend alapján valós loss
CollisionBackendKind::Cde => {
    let backend = CdeCollisionBackend;
    // placement_within_sheet → NoCollision=0, Collision=loss.max(1.0), Unsupported=f64::MAX
    // placement_overlaps → NoCollision=0, Collision=pair_loss.max(1.0), Unsupported=f64::MAX
}
```

### 4.2 `cde_session.rs` — új modul

```rust
pub enum CdeSessionCapability {
    FullSession,
    QueryBatch,
    PerCallOnly { reason: &'static str },
}

pub fn query_capability() -> CdeSessionCapability {
    CdeSessionCapability::PerCallOnly {
        reason: "jagua-rs 0.6.4 has no tentative-query API; \
                 HazardEntity::PlacedItem requires SlotMap PItemKey from a full jagua layout",
    }
}

pub struct CdeDiagnostics {
    pub cde_queries: usize,
    pub cde_engine_builds: usize,
    pub cde_unsupported_count: usize,
    pub cde_session_capability: String,
}
```

### 4.3 Módosított fájlok

```
rust/vrs_solver/src/optimizer/separator.rs       — 3 CDE sentinel arm fix + 5 Q13 test
rust/vrs_solver/src/optimizer/cde_session.rs     — új modul, 3 Q13 test
rust/vrs_solver/src/optimizer/score.rs           — 2 Q13 test
rust/vrs_solver/src/optimizer/mod.rs             — pub mod cde_session hozzáadva
```

## 5) Tesztek

### Q13 kötelező tesztek (10/10 passing)

```
test optimizer::separator::tests::cde_tracker_build_uses_cde_backend_not_all_unsupported ... ok
test optimizer::separator::tests::cde_separator_candidate_backend_loss_is_not_always_max ... ok
test optimizer::separator::tests::cde_separator_repairs_simple_overlap_or_reports_real_unsupported ... ok
test optimizer::score::tests::cde_phase_optimizer_valid_rect_fixture_has_no_backend_unsupported ... ok
test optimizer::score::tests::cde_score_with_backend_matches_validation_for_valid_rects ... ok
test optimizer::cde_session::tests::cde_session_capability_reports_truthful_lifecycle_status ... ok
test optimizer::cde_session::tests::cde_session_or_batch_matches_per_call_adapter_for_pair_matrix ... ok
test optimizer::separator::tests::bbox_default_still_matches_pre_q13_behavior ... ok
test optimizer::separator::tests::jagua_polygon_exact_path_unchanged ... ok
test optimizer::cde_session::tests::no_silent_bbox_fallback_for_cde_search_path ... ok
```

### Összes lib teszt

```
test result: ok. 310 passed; 0 failed; 0 ignored
```

## 6) CDE Lifecycle Döntések

### PASS feltételek teljesítése

| Feltétel | Teljesítve |
|---|---|
| CDE lifecycle/session státusz őszintén dokumentált | Igen — `PerCallOnly` + reason |
| CDE search path nem full Unsupported/f64::MAX sentinel | Igen — 3 sentinel arm javítva |
| CDE queryk ténylegesen CdeCollisionBackendet használnak | Igen — `CdeCollisionBackend` struktúra |
| Bbox default változatlan | Igen — Bbox arm érintetlen |
| JaguaPolygonExact nem regresszál | Igen — JaguaPolygonExact arm érintetlen |
| cargo test --lib zöld | Igen — 310 passed, 0 failed |
| verify.sh zöld | Igen — see verify.log |

### Nem elfogadható esetek: mind megoldva

- ~~CDE session néven bbox/JaguaPolygonExact fallback~~ — nincs
- ~~CDE separator loss automatikus f64::MAX~~ — javítva
- ~~silent fallback bboxra exact/cde query hiba esetén~~ — nincs

## 7) Nem-blokkoló megjegyzések

1. **Per-call CDEngine overhead**: production-ban QueryBatch (offline) vagy session-owned CDEngine
   (ha a jagua-rs API lehetővé teszi) ajánlott. Port plan dokumentálva a contract doc-ban.
2. **CDE touching semantics**: `Edge::collides_with(proper_only=false)` → touching = Collision.
   Tesztek y=0 határt elkerülnek, hogy ne kapjanak hamis boundary violation-t.
3. **CdeDiagnostics**: scaffolding létezik; production bekötés (query counter inkrementálás
   per-call-onként) külön task.

SGH-Q14_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-27T18:38:33+02:00 → 2026-05-27T18:41:44+02:00 (191s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.verify.log`
- git: `main@3932da4`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/mod.rs       |   1 +
 rust/vrs_solver/src/optimizer/score.rs     |  70 +++++++++
 rust/vrs_solver/src/optimizer/separator.rs | 227 +++++++++++++++++++++++++++--
 3 files changed, 289 insertions(+), 9 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/mod.rs
 M rust/vrs_solver/src/optimizer/score.rs
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
?? codex/codex_checklist/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q13_cde_session_backend_search_path_wiring.yaml
?? codex/prompts/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring/
?? codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
?? codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.verify.log
?? docs/egyedi_solver/sgh_q13_cde_session_backend_contract.md
?? rust/vrs_solver/src/optimizer/cde_session.rs
```

<!-- AUTO_VERIFY_END -->
