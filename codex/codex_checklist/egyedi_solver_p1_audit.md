# Codex checklist - egyedi_solver_p1_audit

## Kotelezo inputok

- [x] P1 lista beolvasva: `codex/reports/egyedi_solver_backlog.md`
- [x] P0 baseline beolvasva: `codex/reports/egyedi_solver_p0_audit.md`
- [x] Kotelezo 4 db `tmp/egyedi_solver` dokumentum beolvasva

## Audit tartalom

- [x] Scope + Inputs szekcio kitoltve
- [x] Evidence szekcio path-szintu bizonyitekokkal kitoltve
- [x] P1 Requirement Matrix kitoltve (Req ID, forras, lefedettseg, bizonyitek)
- [x] P1 task-artefakt ellenorzes (canvas/yaml/report/checklist/prompt) elvegezve
- [x] Kod/integracios pontok req mappinggel rogzitve
- [x] Findings severity szerint listazva (BLOCKER/MAJOR/MINOR)
- [x] Minden findinghez van javasolt fix + DoD + regresszios kockazat

## Kapuk es futtatasok

- [x] `python3 scripts/smoke_dxf_import_convention.py` lefutott
- [x] `python3 scripts/smoke_geometry_pipeline.py` lefutott
- [x] `python3 scripts/smoke_time_budget_guard.py --require-real-solver` lefutott
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver_p1_audit.md` lefutott
- [x] Verify log hivatkozas szerepel a report AUTO_VERIFY blokkjaban

## Vegso allapot

- [x] Verdict szerepel a reportban: `P1 coverage: RESZLEGES`
