# Q56A Codex Checklist

Task: `sgh_q56a_orientation_catalog_alap`
Canvas: `canvases/egyedi_solver/sgh_q56a_orientation_catalog_alap.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56a_orientation_catalog_alap.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q56a_orientation_catalog_alap/run.md`
Report: `codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md`

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

- [x] OrientationCatalog létezik vagy meglévő struktúrába integrált (SPInstance-hez kötve)
- [x] vertical/horizontal alignment angle-ek előállnak (artifact: vert 1, horiz 1)
- [x] spacing-offset extrema diagnosztika elérhető (spacing_collision_base_shape forgatott pontjaiból)
- [x] continuous part nem snappel 0/90/180/270-re, hacsak a számolt eredmény nem az (92.75° min-width)
- [x] diszkrét part nem kap illegális continuous jelöltet
- [x] katalógus part-típusonként egyszer számolódik (nem placement-kísérletenként)
- [x] dedup determinisztikus (0.01° identitás tolerancia)
- [x] valós LV8 kritikus part JSON artifact generálva
- [x] Q55B one-part true-extreme sheet-edge proof nem regresszál (determinizmus 10/10 byte-azonos)
