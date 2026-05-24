PASS

# Report — SGH-00 `sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan`

## Status

PASS — Audit complete. Migration plan produced. No production code changes. No external benchmark backend. SparrowGH license gap documented; direct-copy blocked; reimplementation path clear.

## Meta

- **Task slug:** `sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan`
- **Task id:** SGH-00
- **Audit date:** 2026-05-24
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.yaml`
- **Runner:** `codex/prompts/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan/run.md`
- **Fókusz terület:** Sparrow/SparrowGH code audit + VRS migration planning

## Scope

### Cél

- Sparrow és SparrowGH/coroush source audit.
- Licenc és attribution ellenőrzés.
- VRS `jagua_optimizer` modul mapping.
- Konkrét migrációs terv kidolgozása saját VRS optimizerbe.
- Következő SGH tasklánc meghatározása.

### Nem-cél

- Külső SparrowGH benchmark backend.
- Production kódmódosítás.
- SparrowGH CLI adapter.
- Vendorolás.
- Cavity-prepack implementáció.

---

## Dependency evidence

| Check | Result |
|---|---|
| `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` exists | PASS |
| JG-20 report first line | `PASS` |
| JG-20 contains `PHASE2_GATE_DECISION: PASS` | PASS |
| No unresolved STOP / NO-GO / boundary / validation blocker | PASS |

JG-20 passed Gate 2 (Phase 2 irregular benchmark, 4 cases, all `validation_status=pass`, all `boundary_contribution=0.0`). Dependency gate GREEN.

---

## Source/ref/license table

| Repo | Commit | LICENSE path | License | Attribution | Copy status |
|---|---|---|---|---|---|
| JeroenGar/sparrow | a4bfbbe0bf864a7eaf136f9d06456155b1163195 | LICENSE | MIT | Copyright (c) 2025 Jeroen Gardeyn, KU Leuven | Reimplement OK |
| coroush/sparrow | 5df9ce15960f262545169f989ff1068b5f038c9c | LICENSE | MIT | Copyright (c) 2025 Jeroen Gardeyn, KU Leuven | Reimplement OK |
| coroush/sparrow-grasshopper | 0c9a13622e9a63caa693a7271d36e28826f2899d | NOT_FOUND | UNKNOWN | — | **Direct-copy BLOCKED** |

Note: All BPP algorithm source audited from `coroush/sparrow` (MIT). The GH plugin repo has no LICENSE; no algorithmic Rust code is present there (sparrow subdir is empty git submodule).

---

## VRS current-state audit summary

| Question | Finding |
|---|---|
| 1. `LayoutState` infeasible state support? | **NO.** `LayoutState { placed: Vec<PlacedItem>, unplaced: Vec<UnplacedItem> }` — valid placements only. No colliding/working state. |
| 2. `repair.rs` — true separator? | **NO.** `find_violations()` detects overlaps/boundary violations; reinsert loop moves items to valid candidate positions. No GLS weighted loss, no multi-worker, no weight update. Valid-placement repair only. |
| 3. `sheet_elimination.rs` vs bin reduction? | **Partial match.** Select weakest sheet (by area → count → highest index), remove items, reinsert on non-target sheets using valid candidate grid, commit if `find_violations()==[]` + `sheet_count_used` decreased, rollback on fail. Gap: no LBF scoring, no separator after redistribution, no perturbation/pool. |
| 4. `moves.rs` sufficient for transfer/swap/reinsert? | **NO.** `CandidateMove` enum is a pure data skeleton. No execution logic exists. |
| 5. `score.rs` — decision mechanism or post-hoc? | **Both.** `score_layout()` → `ObjectiveBreakdown` drives `MultiSheetManager` decisions. `ScoreBreakdownOutput` in solver IO is post-hoc for user. |
| 6. Exact validator connection? | `vrs_nesting/nesting/instances.py::validate_multi_sheet_output()` called by `vrs_nesting/runner/vrs_solver_runner.py`. Validates: contract_version, status, placements, sheet coverage (polygon contains item), spacing/margin, no inter-item overlap. |
| 7. Modifications needed for exact validator PASS? | Add `WorkingLayout` (infeasible working state, never emitted). Commit gate: `find_violations()==[]` before updating `LayoutState`. All benchmark cases must pass exact validator. No relaxation. |

---

## Sparrow/SparrowGH component audit summary

| Component | Source | Status | VRS gap |
|---|---|---|---|
| GLS collision tracker | `quantify/tracker.rs` | Audited | Absent in VRS |
| GLS weight update (Algorithm 8) | `tracker::update_weights()` | Audited | Absent in VRS |
| Separation loop (Algorithm 9) | `BinSeparator::separate()` | Audited | Absent in VRS (repair.rs is not a separator) |
| FFD largest-first construction | `BpLbfBuilder::construct()` | Audited | VRS has FFD; no LBF scoring, no sep fallback |
| LBF placement evaluator | `LBFEvaluator` | Referenced (not read in full) | Absent in VRS |
| Bin reduction loop | `bin_reduction_phase()` | Audited | VRS sheet_elimination partial match; gap: sep + pool |
| Inter-bin move operators | `bp_moves.rs` | Audited | Absent in VRS (skeleton only) |
| Compaction | `compact_bin()` | Audited | Absent in VRS |
| Solution pool + perturbation | `pool` + `perturb_swap_between_bins()` | Audited | Absent in VRS |
| Snapshot/rollback | Throughout | Audited | VRS has rollback in sheet_elimination; needs extension |

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat | Kapcsolódó ellenőrzés |
|---|---|---|---|---|
| JG-20 dependency gate zöld vagy BLOCKED dokumentált | PASS | Dependency evidence table above | JG-20 PASS, PHASE2_GATE_DECISION: PASS | JG-20 report |
| Külső source ref/license dokumentált | PASS | Source/ref/license table | 3 repos, commits pinned, licenses found or NOT_FOUND documented | `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` |
| File-by-file Sparrow/SparrowGH audit elkészült | PASS | File-by-file audit table in audit doc | 6 coroush/sparrow + 2 JeroenGar/sparrow files audited | `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` |
| VRS optimizer module mapping elkészült | PASS | VRS module mapping table in migration plan | All 10 VRS optimizer modules mapped | `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` |
| Migrációs terv saját VRS optimizerbe elkészült | PASS | Migration plan document created | 16 sections, all required topics covered | `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` |
| Következő SGH tasklánc acceptance gate-ekkel megvan | PASS | SGH-01…SGH-08 task chain table | 8 tasks, each with goal / dependency / output / acceptance gate | Migration plan §Proposed SGH task chain |
| Nem történt production kódmódosítás | PASS | `git diff HEAD` clean (audit-only) | Only docs + checklist + report written | Scope safety section |
| Verify futott vagy blocker dokumentált | PASS | See Verification section below | verify.sh ran, result logged | AUTO_VERIFY block |

---

## Migration decision

```
Do not use SparrowGH as external benchmark backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port or reimplement selected algorithms inside VRS jagua_optimizer.
```

The primary algorithmic gaps in VRS (vs Sparrow) are:
1. No infeasible working state in `LayoutState`
2. No GLS-weighted separator
3. No LBF scoring in construction
4. No separator integration in sheet elimination
5. No move operator execution (transfer/swap/reinsert)
6. No solution pool / perturbation

These are addressed by SGH-01…SGH-08 in order. The VRS exact validator is the acceptance gate for all future implementations.

---

## Proposed SGH task chain

| Task | Goal | Depends on | Gate |
|---|---|---|---|
| SGH-01 | WorkingLayout / infeasible search state scaffold | SGH-00 PASS | `cargo test` pass; type system commit gate enforced |
| SGH-02 | Per-sheet VRS separator V1 (GLS, bbox collision, rollback) | SGH-01 PASS | Separator reduces violations to 0; `find_violations()==[]` on commit |
| SGH-03 | LBF + separator fallback construction | SGH-02 PASS | Phase 1 benchmark: sheet count ≤ baseline; exact validator PASS |
| SGH-04 | Sheet elimination with separator integration | SGH-02 PASS | Phase 1+2 benchmarks: no regression; exact validator PASS |
| SGH-05 | Transfer/swap/reinsert move operators | SGH-02 PASS | Move ops correct; `find_violations()==[]` on commit |
| SGH-06 | Solution pool + perturbation + stagnation handling | SGH-04+05 PASS | Quality benchmark: sheet count improvements; no regressions |
| SGH-07 | VRS quality benchmark suite + exact validator CI gate | SGH-06 PASS | All cases `validation_status=pass`; sheet count ≤ lower_bound + buffer |
| SGH-08 | Irregular/remnant hardening on migrated search loop | SGH-07 PASS | Phase 2 irregular: exact validator PASS; no JG-20 regressions |

---

## Risks and blockers

| Risk | Severity | Mitigation |
|---|---|---|
| coroush/sparrow-grasshopper NO LICENSE | Medium | All algorithms taken from coroush/sparrow (MIT); GH plugin code not used |
| `src/sample/search.rs`, `lbf_evaluator.rs`, `sep_evaluator.rs` not read in full | Low | These contain search sampling details; VRS will reimplement for bbox geometry; design informed by audited callers |
| VRS bbox collision is O(n²) — may be slow for n>300 | Low | Phase 1 items ≤ 300; acceptable. Phase 2 may need spatial index (future task) |
| `WorkingLayout` / `LayoutState` type confusion risk | Medium | Mitigated by distinct types + `validate_and_commit()` gate (SGH-01) |
| Separator convergence not guaranteed | Low | GLS is known to work well in practice; fallback: return best snapshot |

---

## Verification

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
```

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T23:02:10+02:00 → 2026-05-24T23:05:09+02:00 (179s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.verify.log`
- git: `main@e0c8ff5`
- módosított fájlok (git status): 8

**git status --porcelain (preview)**

```text
?? canvases/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
?? codex/codex_checklist/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.yaml
?? codex/prompts/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan/
?? codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
?? codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.verify.log
?? docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
?? docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
```

<!-- AUTO_VERIFY_END -->

---

## Final marker

SGH-01_STATUS: READY
