# Q56B Codex Checklist

Task: `sgh_q56b_part_analysis_shape_profile_v2`
Canvas: `canvases/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b_part_analysis_shape_profile_v2.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2/run.md`
Report: `codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md`

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

- [x] PartAnalysis / ShapeProfileV2 létezik és SPInstance-hez kötött
- [x] Rc<PartShapeProfile> + ContourFeatureSummary újrahasználva (nem duplikálva)
- [x] fit_difficulty_score külön riportolva a priority_score-tól (0.6274 vs 0.6153)
- [x] shape tag-ek determinisztikusak, geometriából/mennyiségből (nem part-ID)
- [x] tiny filler nem kap anchor osztályozást
- [x] hole_free_solver_input flag rögzítve (worker prepack tisztelete)
- [x] egyetlen shape tag sem enged bbox collision shortcutot
- [x] part_analysis_summary.json artifact generálva top-listákkal
- [x] Q55B sheet-edge proof nem regresszál (determinizmus 10/10 byte-azonos)
