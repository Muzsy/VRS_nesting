# Codex checklist - dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] `frontend/src/lib/dxfIntakePresentation.ts` elkészült közös TONE, INTAKE_COPY és badge helper réteggel
- [x] A TONE paletta lefedi a success / attention / blocked / queued / neutral szinteket — nincs ad-hoc indigo repair badge
- [x] Az INTAKE_COPY három szintet különít el: status, next step, tech note
- [x] A badge helper függvények (runStatusBadge, acceptanceOutcomeBadge, stb.) a presentation modulba kerültek, nem a page-ben definiáltak
- [x] A `DxfIntakePage` importálja a presentation modult — nincs inline badge helper duplikáció
- [x] A diagnostics overlay (`Preflight diagnostics`) és a review overlay (`Review required`) külön, egyértelmű szerepkörű copy-t kap
- [x] A review overlay guidance szekciója elkülönül a tech note szekciótól (két külön vizuális blokk)
- [x] Az accepted files → parts szekció INTAKE_COPY.acceptedParts copy-t használ
- [x] Az üres állapot / pending / blokkolt szövegek egységes hangnemet kaptak
- [x] Nincs új backend route, projection, workflow vagy persisted domain
- [x] A T4 diagnostics drawer nyitás/zárás funkció regressziómentes
- [x] A T5 replacement upload flow regressziómentes
- [x] A T6 create-part flow regressziómentes
- [x] Elkészült task-specifikus smoke (`scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py`)
- [x] `python3 scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py` OK
- [x] `npm --prefix frontend run build` OK
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md` PASS
