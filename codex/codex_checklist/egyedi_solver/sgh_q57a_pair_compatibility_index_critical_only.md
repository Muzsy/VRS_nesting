# Q57A Codex Checklist

Task: `sgh_q57a_pair_compatibility_index_critical_only`
Canvas: `canvases/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57a_pair_compatibility_index_critical_only.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only/run.md`
Report: `codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md`

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

- [x] PairCompatibilityIndex létezik (pair_matrix.rs stub lecserélve)
- [x] bounded + default critical-only (top-K env-konfigurálható: VRS_PAIR_INDEX_*)
- [x] PartAnalysis/OrientationCatalog/ContourFeatureSet újrahasználva (nincs feature-duplikáció)
- [x] ismételt kritikus típus same-part flip candidate-et ad (nincs part-ID hardcode)
- [x] valid candidate-ek spacing-expanded clearance-checked (grid proxy; CDE marad a truth)
- [x] pair candidate-eknek van rotation source metaadata
- [x] env-gate default off → no-regression bizonyítva (determinizmus 10/10 byte-azonos)
- [x] pair_compatibility_index.json artifact generálva
- [x] nem kényszerít solver placement döntést (Interlock változatlan)
