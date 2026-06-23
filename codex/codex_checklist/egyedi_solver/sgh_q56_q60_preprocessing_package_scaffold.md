# Q56–Q60 preprocessing package scaffold — Codex Checklist

Task: `sgh_q56_q60_preprocessing_package_scaffold`
Canvas: `canvases/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56_q60_preprocessing_package_scaffold.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold/run.md`
Report: `codex/reports/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md`

## DoD

- [ ] repo rules elolvasva
- [ ] valós kód anchorok ellenőrizve
- [ ] minden módosított/létrehozott fájl szerepel a YAML outputs listában
- [ ] task-specifikus implementation elkészült (10 package + index + master runner + self-package)
- [ ] task-specifikus diagnosztika elkészült (sanity OK)
- [ ] task-specifikus tesztek lefutottak (Python sanity)
- [ ] verify wrapper lefutott
- [ ] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal

## Task-specifikus kapuk

- [ ] mind a 10 Q56–Q60 task package létrejött (canvas + YAML + runner + checklist + report)
- [ ] minden YAML megfelel a docs/codex/yaml_schema.md steps sémának
- [ ] minden YAML utolsó stepje "Repo gate (automatikus verify)" verify.sh paranccsal
- [ ] minden runner önállóan használható
- [ ] minden canvas valós repo anchorokra hivatkozik (## Valós repo anchorok blokk)
- [ ] Q56B2 rögzíti: cavity prepack v2 már meglévő worker/pre-solver réteg
- [ ] nincs solver/runtime/API/quality profile módosítás
- [ ] a forrás markdown tasktervek nem módosultak
- [ ] task-index + master runner létrejött (Q56A->...->Q60 + dependency graph)
- [ ] Python sanity: "Q56-Q60 package sanity: OK"
