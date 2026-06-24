# Q62 Codex Checklist

Task: `sgh_q62_full276_lv8_spacing5_two_sheet_rerun`
Canvas: `canvases/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q62_full276_lv8_spacing5_two_sheet_rerun.yaml`
Report: `codex/reports/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md`

## DoD

- [x] Repo szabályfájlok és a Q49/Q61 előzmények elolvasva, reportban rögzítve.
- [x] Minden létrehozott/módosított fájl szerepel a YAML outputs listájában.
- [x] A benchmark ugyanazt a full276 LV8 package-et használja, mint a Q49, csak a futási konfiguráció változik.
- [x] A current-solver run a Q61-ben dokumentált gate-kombinációval fut.
- [x] A benchmark artefaktok Q49-szerűek: input, outputs, logs, summary, report, renders.
- [x] A report egyértelműen rögzíti, hogy a 2-sheet / spacing-5 target teljesült-e.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [x] `python3 scripts/bench_sgh_q62_full276_spacing5_two_sheet.py`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md`
