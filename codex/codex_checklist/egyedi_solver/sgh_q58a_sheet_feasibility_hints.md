# Q58A Codex Checklist

Task: `sgh_q58a_sheet_feasibility_hints`
Canvas: `canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58a_sheet_feasibility_hints.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q58a_sheet_feasibility_hints/run.md`
Report: `codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md`

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

- [x] SheetFeasibilityHints modell létezik (sheet_feasibility.rs)
- [x] area lower bound determinisztikus + margin-shrunk basis explicit
- [x] kritikus kapacitás státusz (unknown/plausible/...), nem exact proof
- [x] ismételt kritikus típus target distribution hintet kap (nincs LV8 hardcode; LV8 [2,2,2])
- [x] danger parts lista tartalmazza a magas-criticality large anchorokat
- [x] becslések confidence/basis címkével
- [x] nincs placement mutáció (Q58B köti be)
- [x] sheet_feasibility_hints.json artifact szerializálható + stabil
