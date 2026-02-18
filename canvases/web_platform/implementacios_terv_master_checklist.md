# canvases/web_platform/implementacios_terv_master_checklist.md

# Web platform implementacios terv master checklist

## Funkcio
A feladat egy egyseges, pipalhato checklist fajl letrehozasa a web platform teljes
implementacios tervere, a `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
feladatpontjai alapjan, a `codex/codex_checklist/web_platform/` mappaban.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a docx-ben szereplo Phase 0-4 osszes konkret feladatlepese checklist formaban;
  - fozis-DoD checkpointok felvetele;
  - Phase 0 checkpointok bepipalasa (elkeszult allapot);
  - kapcsolodo codex task artefaktok (canvas, yaml, report).
- Nincs benne:
  - uj implementacio (API/worker/frontend/security);
  - Phase 1-4 pontok kipipalasa;
  - a web platform spec tartalmi atiras.

### Erintett fajlok
- `canvases/web_platform/implementacios_terv_master_checklist.md`
- `codex/goals/canvases/web_platform/fill_canvas_implementacios_terv_master_checklist.yaml`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
- `codex/reports/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] Letrejott egy checklist fajl a `codex/codex_checklist/web_platform/` alatt.
- [ ] A checklist a docx Phase 0-4 osszes feladatpontjat tartalmazza.
- [ ] A checklistben a Phase 0 checkpointok `[x]` allapotban vannak.
- [ ] A checklistben a Phase 1-4 pontok nyitottak (`[ ]`).
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/implementacios_terv_master_checklist.md` PASS.

### Kockazat + rollback
- Kockazat: egy-egy docx feladatpont kimaradhat az atvezetes soran.
- Mitigacio: phase-by-phase 1:1 mapping a docx sorsorrend szerint.
- Rollback: a checklist/task artefaktok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/implementacios_terv_master_checklist.md`

## Kapcsolodasok
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md`
