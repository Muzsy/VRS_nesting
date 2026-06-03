Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
- codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q26_single_sheet_sparrow_validation_suite.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Kemény szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- Ez tesztcsomag-task, nem solver-portolás és nem tuning.
- Új Q26 pozitív Rust fixture-ben pontosan egy stock lehet, `quantity=1`; minden placementnek `sheet_index == 0` kell lennie.
- Pozitív fixture csak `status == "ok"` esetén PASS. Partial/unsupported pozitív fixture = FAIL, nem PASS_WITH_NOTES.
- A negatív overcapacity fixture-nek őszintén partial/unsupported eredményt és diagnosztikát kell adnia.
- A Q26 integrációs tesztek production útvonalat használjanak: `solver_profile=jagua_optimizer_phase1_outer_only`, `optimizer_pipeline=sparrow_cde`, `collision_backend=cde`.
- Kötelező assert-ek: native Sparrow model/tracker aktív, old core false, compression passes 0, bbox proxy primary false, CDE adapter backend, bbox fallback 0.
- Kötelező LV8-derived gate: `samples/real_work_dxf/0014-01H/lv8jav` valós DXF-ekből 40–80 instance, egyetlen 1500×3000 sheet, status ok, unplaced 0, nincs `sheet_002.dxf`.
- A LV8-derived gate nem benchmark. Ne használd a 191 first-sheet vagy full-276 csomagot acceptance-ként.
- Ne adj hozzá compressiont, multisheet acceptance-t vagy benchmark-tuningot.
- Ne módosíts production solver kódot, kivéve ha a reportban bizonyítottan test-infra miatt elkerülhetetlen; algoritmusjavítás nem része ennek a tasknak.
- Ne vezesd vissza a `WorkingLayout`, `VrsCollisionTracker`, bbox/AABB ranking, legacy VRS-core vagy dense-specific shortcut logikát.

Kötelező végső gate:
- cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
- cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
- cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation -- --nocapture
- python3 scripts/smoke_sgh_q26_single_sheet_validation_suite.py
- python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py
- python3 scripts/smoke_real_dxf_sparrow_pipeline.py
- ./scripts/check.sh
- ./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md

Eredményként frissítsd:
- codex/codex_checklist/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
- codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
- codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.verify.log

A végén add meg a módosított fájlok listáját és a gate-ek eredményét.
