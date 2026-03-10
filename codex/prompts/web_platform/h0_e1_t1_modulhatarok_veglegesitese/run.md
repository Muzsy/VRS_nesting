# DXF Nesting Platform Codex Task - H0-E1-T1 modulhatarok veglegesitese
TASK_SLUG: h0_e1_t1_modulhatarok_veglegesitese

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e1_t1_modulhatarok_veglegesitese.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez docs-first es docs-only task: ne nyulj API, worker, frontend, solver vagy supabase
  implementacios fajlokhoz, hacsak azok nincsenek explicit felsorolva a YAML outputs-ban.
- Minimal-invaziv modon dolgozz: a cel nem a docs/web_platform teljes atszerkesztese,
  hanem a modulhatarok source-of-truth dokumentumanak letrehozasa es a kulcs
  hivatkozasok szinkronba hozasa.
- A boundary dokumentum legyen implementaciohoz eleg konkret:
  ownership, input/output contract, tiltott felelosseg, source-of-truth szerepeljen.
- Rogzitsd egyertelmuen:
  - definicio != hasznalat != snapshot != artifact != projection
  - a worker / engine adapter csak snapshotbol dolgozik
  - a viewer source of truth projection, nem SVG
  - a manufacturing es a postprocess helye kulon reteg, nem a nesting truth resze

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md
  (ez letrehozza/frissiti: codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.verify.log,
  es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md
  - codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md
  - codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.verify.log
- Add meg a vegleges fajltartalmakat.