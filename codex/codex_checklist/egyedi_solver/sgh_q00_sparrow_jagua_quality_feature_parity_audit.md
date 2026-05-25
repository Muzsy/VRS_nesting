# Checklist — SGH-Q00 `sgh_q00_sparrow_jagua_quality_feature_parity_audit`

## Gate
- [x] SGH-05 report PASS/PASS_WITH_NOTES.
- [x] SGH-05 report tartalmazza: `SGH-06_STATUS: READY`.

## External source audit
- [x] `JeroenGar/jagua-rs` ref/license dokumentálva (commit `43e81373`, MPL-2.0).
- [x] `JeroenGar/sparrow` ref/license dokumentálva (commit `a4bfbbe0`, MIT).
- [x] `coroush/sparrow` / `sparrow-grasshopper` státusz dokumentálva (coroush/sparrow `5df9ce15` prior SGH-00 audit; sparrow-grasshopper `0c9a1362` C# wrapper).
- [x] File-by-file audit elkészült (18 feature, 8 sparrow forrás, 6 VRS forrás).

## Quality features
- [x] RotationRange / continuous rotation audit (F01 MISSING).
- [x] CDE / geometry collision audit (F04 PROXY).
- [x] collision severity / smooth loss audit (F05 PROXY).
- [x] shape penalty audit (F06 MISSING).
- [x] GLS weights audit (F07 PARTIAL).
- [x] separator loop audit (F08 PARTIAL).
- [x] move_items_multi audit (F09 MISSING).
- [x] exploration/compression audit (F11 MISSING).
- [x] infeasible pool / perturbation audit (F12 MISSING, F13 PARTIAL).
- [x] BPP/bin reduction audit (F16 PARTIAL).
- [x] caching/preprocessing audit (F17 MISSING).
- [x] irregular/remnant support audit (F18 PROXY).

## VRS parity
- [x] VRS `working.rs` audit (commit gate, validate_for_commit).
- [x] VRS `separator.rs` audit (VrsCollisionTracker, VrsSeparator, GLS weights).
- [x] VRS `initializer.rs` audit (LBF + separator fallback).
- [x] VRS `sheet_elimination.rs` audit (sheet eliminator — SGH-04).
- [x] VRS `moves.rs` audit (MoveExecutor, try_transfer/swap/reinsert — SGH-05).
- [x] VRS rotation model audit (discrete only: 0/90/180/270).
- [x] Gap mátrix FULL/PARTIAL/PROXY/MISSING/WRONG státuszokkal elkészült (18 feature, 1 FULL, 4 PARTIAL, 6 PROXY, 7 MISSING, 0 WRONG).

## Outputs
- [x] `docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md`
- [x] `docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md`
- [x] `docs/egyedi_solver/sgh_q00_modular_architecture_principles.md`
- [x] report DoD → Evidence mátrixszal.
- [x] verify log létrejött.
- [x] `SGH-Q01_STATUS: READY` marker.
