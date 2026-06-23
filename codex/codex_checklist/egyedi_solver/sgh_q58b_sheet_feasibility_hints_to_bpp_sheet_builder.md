# Q58B Codex Checklist

Task: `sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder`
Canvas: `canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder/run.md`
Report: `codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md`

## DoD

- [x] repo rules elolvasva
- [x] valós kód anchorok ellenőrizve
- [x] minden módosított/létrehozott fájl szerepel a YAML outputs listában
- [x] task-specifikus implementation elkészült
- [x] task-specifikus diagnosztika elkészült
- [x] task-specifikus tesztek lefutottak
- [x] verify wrapper lefutott (PASS, exit 0)
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal

## Task-specifikus kapuk

- [x] hint-fogyasztó decision-piece API VRS_SHEET_FEASIBILITY_HINTS gate-tel (production átkötés DEFERRED, §7)
- [x] critical queue ordering hint-aware (priority_score megőrizve, kombinálva)
- [x] sheet target kritikus kvóta számolva + diagnosztikában látható (LV8 quota=2)
- [x] critical phase frontier hint-aware, de bounded (base+8 felső korlát; nincs végtelen retry)
- [x] best-partial preservation implementált + diagnosztikával bizonyított
- [x] 2/3 → final 1/3 regresszió konstrukció szerint lehetetlen (downgrades_rejected=1)
- [x] gate off → byte-azonos no-regression (determinizmus 10/10)
- [x] sheet_builder_hints_integration.json artifact generálva
- [x] best-partial gate-független invariáns; minden placement upstream exact-validált marad
