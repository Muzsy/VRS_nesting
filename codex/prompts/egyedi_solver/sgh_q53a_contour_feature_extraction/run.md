Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `canvases/egyedi_solver/sgh_q53a_contour_feature_extraction.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53a_contour_feature_extraction.yaml`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Kemény szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel az adott YAML step `outputs` listájában.
- Dolgozz valós repo alapján. Ne találj ki nem létező API-t; ha valami nincs, jelöld BLOCKED/DEVIATION státusszal.
- CDE marad a collision truth.
- Nincs NFP, nincs bbox collision shortcut, nincs part-id hack.
- Continuous rotationt nem szabad diszkrét foklistára cserélni.
- Cavity/hole logika nem kerülhet a fő solverbe.
- Report Standard v2 szerint töltsd ki a reportot.

Kötelező célzott ellenőrzések:
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml contour_features`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml shape_profile`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md`

Végső gate:
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md`

Eredményként frissítsd:
- `codex/codex_checklist/egyedi_solver/sgh_q53a_contour_feature_extraction.md`
- `codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md`
- `codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.verify.log`

A végén add meg a módosított fájlok listáját, a gate-ek eredményét, és ha van, a BLOCKED/DEVIATION okát.
