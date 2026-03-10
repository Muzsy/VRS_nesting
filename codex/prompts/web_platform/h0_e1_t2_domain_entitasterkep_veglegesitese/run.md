# DXF Nesting Platform Codex Task - H0-E1-T2 domain entitasterkep veglegesitese
TASK_SLUG: h0_e1_t2_domain_entitasterkep_veglegesitese

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e1_t2_domain_entitasterkep_veglegesitese.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez docs-first es docs-only task: ne nyulj API, worker, frontend, solver vagy supabase
  implementacios fajlokhoz, hacsak azok nincsenek explicit felsorolva a YAML outputs-ban.
- Minimal-invaziv modon dolgozz: a cel nem a docs/web_platform teljes atszerkesztese,
  hanem a domain entitasterkep source-of-truth dokumentumanak letrehozasa es a kulcs
  hivatkozasok szinkronba hozasa.
- A dokumentum legyen eleg konkret a kovetkezo H0-E2 core schema taskhoz.

Rogzitsd egyertelmuen:
- mely objektumok elso osztalyu domain entitasok;
- mely objektumok value objectek;
- mely objektumok immutable snapshotok;
- mely objektumok result/projection/artifact jelleguek;
- mi az aggregate root es ownership logika;
- mi a kulonbseg a definition, usage, demand, snapshot, result es export vilagok kozott.

Kulon figyelj:
- ne keverd a Part Definition-t a Part Demand-del;
- ne keverd a Sheet Definition-t a Sheet Inventory Unit-tal;
- ne keverd a Run Snapshot-ot a Run Result-tal;
- ne kezeld a projectiont vagy export artifactot domain truth-kent;
- maradj osszhangban a
  `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  dokumentummal.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md

Ez frissitse:
- codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md
- codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.