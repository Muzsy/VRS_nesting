PASS

# Report — SGH-Q01 `sgh_q01_sparrow_quality_migration_correction_plan`

## Status

PASS — audit + planning task; 6 proxy annotations added to production files (comment-only); three docs created; cargo test 140/140; verify.sh exit 0.

## Meta

- **Task slug:** `sgh_q01_sparrow_quality_migration_correction_plan`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** main (post-SGH-Q00)
- **Fókusz terület:** Sparrow quality migration correction plan + proxy annotations + no-downgrade gates

## Scope

### Cél
- SGH-Q00 gap matrix alapján korrekciós migrációs terv dokumentálása.
- 6 jelöletlen PROXY kódhely P06 `// QUALITY_RISK:` annotációval ellátása.
- Corrected task roadmap (SGH-Q01..Q08) és no-downgrade acceptance gates dokumentálása.

### Nem-cél
- Production logika módosítása.
- Külső forrás vendorálása.
- Benchmark kampány futtatása.
- SGH-06 scope megnyitása.

---

## Dependency evidence

| Check | Result | Evidence |
|---|---:|---|
| SGH-Q00 report létezik | PASS | `codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md` |
| SGH-Q00 report első sora PASS | PASS | Első sor: `PASS` |
| SGH-Q00 tartalmazza `SGH-Q01_STATUS: READY` | PASS | Report végén megtalálható |

---

## SGH-Q00 gap summary

| Státusz | Darab | Feature-ök |
|---|---:|---|
| FULL | 1 | F15 (seed determinism) |
| PARTIAL | 4 | F07 (GLS weights), F08 (rollback), F13 (disruption), F16 (BPP) |
| PROXY | 6 | F03 (transformation), F04 (CDE/collision), F05 (smooth loss), F10 (LBF), F18 (irregular container), F06 (shape penalty) |
| MISSING | 7 | F01 (continuous rotation), F02 (stochastic sampling), F09 (multi-worker), F11 (exploration/compression), F12 (infeasible pool), F14 (time budget), F17 (geometry preprocessing) |
| WRONG | 0 | — |

**Legfontosabb megállapítás:** A VRS rectangular Phase 1-ben PROXY szinten helyes; a legnagyobb quality gap a stochasztikus keresés (F02, F09) és a kétfázisú orchestration (F11–F14) hiánya.

---

## Keep / stop / replace decision table

| Elem | Döntés | Indoklás |
|---|---|---|
| `WorkingLayout` + commit gate | **KEEP** | Helyes absztrakció (SGH-01) |
| `VrsCollisionTracker` (AABB loss, binary boundary) | **KEEP + ANNOTATE** | PROXY, de helyes Phase 1-ben; annotálva |
| `VrsSeparator` (single-threaded, additive GLS) | **KEEP + EXTEND** | Alap jó; F07, F09 hiányok kiegészítendők |
| `initializer.rs` LBF deterministic | **KEEP** | Phase 1 baseline |
| `sheet_elimination.rs` | **KEEP + EXTEND** | SGH-04 operátorok OK; phase loop hiányzik |
| `moves.rs` MoveExecutor (SGH-05) | **KEEP + EXTEND** | Primitívek OK; disruption loop hiányzik |
| `score.rs` ScoreModel | **KEEP** | Helyes, `cost_per_use` megvan (JG-19) |
| `stopping.rs` StoppingPolicy | **KEEP + EXTEND** | Nincs per-phase time split |
| Hardcoded `[0, 90, 180, 270]` (`item.rs`) | **ANNOTATE now, REPLACE SGH-Q07** | DiscreteRotationOnly PROXY; annotálva |
| AABB `bbox_overlap_area` + `BOUNDARY_LOSS_PROXY` | **ANNOTATE now, REPLACE SGH-Q06** | PROXY-ok; annotálva |
| SGH-06 (eredeti scope) | **PAUSE** | Orchestration prereqs hiányoznak |

---

## Corrected migration order

```
SGH-Q01 (annotáció + planning)           ← ez a task
  → SGH-Q02 (GLS parity + rollback)
    → SGH-Q03 (multi-worker)
      → SGH-Q04 (phase orchestration)
        → SGH-Q05 (BPP phase loop)
          → SGH-Q06 (smooth loss)
            → SGH-Q07 (rotation policy)
              → SGH-Q08 (collision backend + geometry)
```

Részletes leírás: `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md`

**Kötelező döntések:**
- `SGH-06 is paused.`
- `SGH-01..SGH-05 are structural scaffolds, not quality parity.`
- `No future simplified proxy is acceptable without explicit quality-risk flag and benchmark gate.`
- `Every MISSING / PROXY / PARTIAL feature from SGH-Q00 gets a migration path.`

---

## Proxy annotations added (SGH-Q01 production scope)

| Fájl | Kódhely | Proxy neve | Annotáció hozzáadva |
|---|---|---|---|
| `optimizer/separator.rs` | `BOUNDARY_LOSS_PROXY = 1.0` | BinaryBoundaryLoss | PASS |
| `optimizer/separator.rs` | `bbox_overlap_area` fn | BboxOnlyProxy | PASS |
| `optimizer/separator.rs` | `update_weights` fn | AdditiveGlsProxy | PASS |
| `optimizer/boundary.rs` | `rect_within_boundary` fn | BboxBoundaryProxy | PASS |
| `item.rs` | `normalize_allowed_rotations` fn | DiscreteRotationOnly | PASS |
| `optimizer/candidates.rs` | `PlacedBbox::overlaps` fn | BboxOnlyProxy | PASS |

Minden annotáció a P06 formátumot követi:
```rust
// QUALITY_RISK: <ProxyName>
// Exact for: <when exact>
// Proxy for: <when not exact>
// Parity: <STATUS> (<F-number>, SGH-Q00)
```

---

## Risk register

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| GLS formula csere (SGH-Q02) megsérti meglévő teszteket | ALACSONY | KÖZEPES | Backward-compat test + determinism gate |
| Multi-worker (SGH-Q03) non-determinizmusa | KÖZEPES | MAGAS | Seed-based determinism gate; rayon par_iter seed |
| Phase orchestration (SGH-Q04) időtúllépés | ALACSONY | ALACSONY | Per-phase time budget config |
| Geometry layer (SGH-Q08) CDE integráció breaking change | MAGAS | MAGAS | `CollisionBackend` trait; AABB backend backward-compat |
| SGH-Q01 annotáció véletlenül logikát érint | NINCS | — | Csak komment-szintű változtatás; 140/140 teszt zöld |

---

## No-downgrade gates

Részletes leírás: `docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md`

| Gate | Elvárás | Státusz |
|---|---|---|
| G01 `cargo test` | 140/140 | PASS |
| G02 `verify.sh` | exit 0 | PASS |
| G03 `find_violations` | 0 violation minden accepted output-on | PASS (nem változott logika) |
| G04 Proxy annotáció | 6 kódhely annotálva P06 szerint | PASS |
| G05 Determinism | nem érintett (nincs stochasztikus komponens ebben a taskban) | N/A |
| G06 Parity non-regression | nincs parity státusz csökkentés | PASS |
| G07 No new proxy without gate | nem kerül be új PROXY | PASS |
| G08 Production scope | csak `separator.rs`, `boundary.rs`, `item.rs`, `candidates.rs` (komment) | PASS |

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Fájl |
|---|---:|---|---|
| Dependency gate (SGH-Q00 PASS + READY) | PASS | SGH-Q00 report `PASS`, `SGH-Q01_STATUS: READY` | `sgh_q00_...md` |
| Correction plan created | PASS | Fájl létezik, mandatory decisions szerepelnek | `docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md` |
| Corrected roadmap created | PASS | SGH-Q01..Q08 minden task leírva | `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md` |
| No-downgrade gates created | PASS | G01..G08 definiálva | `docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md` |
| All MISSING/PROXY/PARTIAL features mapped | PASS | 18 feature mind migration path-ot kapott | `sgh_q01_corrected_task_roadmap.md` |
| 6 proxy kódhely annotálva (P06) | PASS | `// QUALITY_RISK:` annotáció minden kódhelyen | 4 production fájl |
| Nem történt production logika változtatás | PASS | Csak komment-szintű változtatás; 140/140 teszt | `cargo test` |
| Verify green | PASS | exit 0, `[DONE] smoketest OK` | `verify.sh` output |

---

## Scope safety

| Tiltott művelet | Megtörtént? |
|---|---|
| Production logika módosítása | NEM — csak komment |
| Külső forrás vendorálása | NEM |
| Benchmark kampány futtatása | NEM |
| Python runner módosítás | NEM |
| IO contract módosítás | NEM |
| SGH-06 scope megnyitása | NEM |

---

## Verification

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Result: 140 passed; 0 failed

./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
# Result: [DONE] smoketest OK (exit 0)
```

SGH-Q02_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T12:09:04+02:00 → 2026-05-25T12:12:05+02:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.verify.log`
- git: `main@278ba5c`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 rust/vrs_solver/src/item.rs                 |  4 ++++
 rust/vrs_solver/src/optimizer/boundary.rs   |  4 ++++
 rust/vrs_solver/src/optimizer/candidates.rs |  4 ++++
 rust/vrs_solver/src/optimizer/separator.rs  | 12 ++++++++++++
 4 files changed, 24 insertions(+)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/item.rs
 M rust/vrs_solver/src/optimizer/boundary.rs
 M rust/vrs_solver/src/optimizer/candidates.rs
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
?? codex/codex_checklist/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q01_sparrow_quality_migration_correction_plan.yaml
?? codex/prompts/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan/
?? codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
?? codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.verify.log
?? docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
?? docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
?? docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
```

<!-- AUTO_VERIFY_END -->
