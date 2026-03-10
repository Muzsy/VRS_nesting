# DXF Nesting Platform Codex Task - H0-E1-T3 snapshot-first futasi es adatkontraktus formalizalasa
TASK_SLUG: h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez docs-first es docs-only task: ne nyulj API, worker, frontend, solver vagy supabase
  implementacios fajlokhoz, hacsak azok nincsenek explicit felsorolva a YAML outputs-ban.
- Minimal-invaziv modon dolgozz: a cel nem a docs/web_platform teljes atszerkesztese,
  hanem a snapshot-first futasi es adatkontraktus source-of-truth dokumentumanak
  letrehozasa es a kulcs hivatkozasok szinkronba hozasa.
- A dokumentum legyen eleg konkret a kovetkezo H0-E2 core schema taskhoz.

Rogzitsd egyertelmuen:
- mi a kulonbseg a run request, run snapshot, run attempt, run state, run result,
  projection es export artifact kozott;
- milyen elo domain allapotbol epul a snapshot;
- mi masolodik immutable snapshot adatkent, es mi marad csak referencia/manifest;
- mit kap a worker bemenetnek;
- mit kell kotelezoen eloallitani outputkent;
- mit tilos kozvetlenul olvasni vagy visszairni;
- hogyan mukodik a retry, timeout, lease, cancel es idempotencia szemantika.

Kulon figyelj:
- a worker ne legyen elo domain-tabla olvaso;
- a snapshot ne legyen helyben modosithato truth;
- ne keverd a run resultot a projectionnel vagy export artifacttal;
- maradj osszhangban a
  `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  es a
  `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
  dokumentumokkal.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md

Ez frissitse:
- codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md
- codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.