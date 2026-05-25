# SGH-Q00 — Sparrow/jagua-rs quality-feature parity audit

## Cél

Stop-the-line audit. A cél nem új implementáció, hanem annak bizonyítása és dokumentálása, hogy a VRS saját solver iránya legalább az eredeti `jagua-rs` / `Sparrow` nesting-minőségét célozza, nem annak lebutított proxyját.

A task eredménye egy minőségi parity report és gap mátrix legyen:

```text
Sparrow/jagua-rs feature
→ VRS current equivalent
→ quality risk if missing/simplified
→ required migration/port strategy
→ required tests/benchmarks
→ decision: full port / VRS-adapted port / wrapper/dependency / reject with evidence
```

## Stratégiai szabály

```text
Ha jagua-rs/Sparrow tudja, és nesting minőséghez számít,
akkor nem hagyjuk ki és nem helyettesítjük gyengébb bbox/greedy/proxy megoldással
csak explicit audit + mérési indoklás alapján.
```

## Dependency gate

SGH-Q00 az SGH-05 után indulhat, de nem folytatja SGH-06-ot. Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

Elvárás:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-06_STATUS: READY
```

Ha nem teljesül, `BLOCKED` report.

## Kötelező auditforrások

Külső források, ideiglenes repo-n kívüli könyvtárba clone-olva/olvasva:

```text
https://github.com/JeroenGar/jagua-rs
https://github.com/JeroenGar/sparrow
https://github.com/coroush/sparrow
https://github.com/coroush/sparrow-grasshopper  # ha releváns / elérhető
```

A külső kódot tilos vendorolni vagy production dependencyként bekötni ebben a taskban.

## Kötelező VRS auditforrások

```text
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md
docs/egyedi_solver/sgh_05_move_operators_contract.md
rust/vrs_solver/src/optimizer/*.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
```

## Kötelező vizsgált minőségfunkciók

Legalább ezeket auditáld kódból, ne emlékezetből:

```text
1. RotationRange / continuous rotation / discrete rotation handling
2. Item transformation model: translation + rotation
3. Continuous rotation sampling and local wiggle/refinement
4. jagua-rs CDE / collision detection engine usage
5. true geometry collision severity vs bbox proxy
6. penetration/depth/smooth collision quantification
7. shape-based penalty / concavity or complexity weighting
8. Guided Local Search dynamic pair weights
9. separator incumbent/restore/strike/best-state loop
10. move_items / move_items_multi / multi-worker or multi-order search
11. BLF / LBF construction role and limits
12. exploration phase
13. compression phase
14. infeasible solution pool
15. disruption / large-item swap / perturbation
16. time budget and phase split
17. deterministic seeds and reproducibility
18. bin-packing / BPP fork logic if present
19. sheet/bin reduction logic
20. scoring/objective model
21. caching/preprocessing / shape simplification / geometric acceleration
22. support for irregular container / remnant geometry
23. API boundaries suitable for modular VRS integration
```

## Kötelező kimenetek

```text
docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q00_modular_architecture_principles.md
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
codex/reports/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.verify.log
codex/codex_checklist/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
```

## Report minimum tartalom

```text
- source repos + pinned refs + license evidence
- file-by-file audit
- quality feature parity matrix
- VRS simplification risk list
- features currently lebutított / proxy implementation
- must-port list
- modular architecture principles
- corrected roadmap
- SGH tasks to pause / revise / continue
- next task recommendation
```

## Döntési kimenet

A report végén legyen egyértelmű marker:

```text
SGH-Q01_STATUS: READY
```

vagy:

```text
SGH-Q01_STATUS: BLOCKED
```

PASS csak akkor, ha a gap mátrix konkrét, kódból bizonyított és végrehajtható.
