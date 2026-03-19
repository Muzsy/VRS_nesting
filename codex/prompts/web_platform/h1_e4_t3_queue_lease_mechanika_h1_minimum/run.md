# DXF Nesting Platform Codex Task - H1-E4-T3 Queue lease mechanika (H1 minimum)
TASK_SLUG: h1_e4_t3_queue_lease_mechanika_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `api/services/run_creation.py`
- `worker/main.py`
- `worker/README.md`
- `canvases/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t vagy API-konvenciot: a H0/H1 docsbol,
  migraciokbol es a meglevo worker mintakbol indulj ki.
- Ez a task H1 minimum **queue lease** scope: ne csussz at solver futtatas,
  result normalizer, layout/projection vagy artifact scope-ba.
- A canonical queue truth: `app.run_queue`, `app.nesting_runs`,
  `app.nesting_run_snapshots`.
- A `worker/main.py` claim/heartbeat logikaja explicit helperre legyen
  realignalva; ne inline SQL string maradjon a canonical truth.
- A lease TTL legyen explicit; ne maradjon implicit 10 perces magic value.
- A heartbeat legyen tokenhez kotott; wrong-token / lost-lease helyzetet
  kontrollaltan kell kezelni.
- A duplafutas elleni vedelem kulcsa az atomikus claim; ezt ne gyengitsd.

Implementacios elvarasok:
- Vezess be explicit `worker/queue_lease.py` helper modult.
- A helper valositson meg legalabb claim + heartbeat funkcionalitast.
- Sikeres claim eseten a sor `queue_state='leased'` allapotba keruljon, es
  toltse a canonical lease mezoket: `leased_by`, `lease_token`, `leased_at`,
  `heartbeat_at`, `lease_expires_at`.
- A `attempt_no` / `attempt_status` H1 minimum szinten ertelmesen frissuljon.
- Legyen minimalis expired-lease reclaim szemantika, es ezt dokumentald is.
- A `worker/main.py` a helperre epuljon, de a task ne terjeszkedjen a teljes
  worker lifecycle / solver execution ujratervezese fele.
- Keszits task-specifikus smoke scriptet a fo lease agakra.
- Ha kiderul valos kompromisszum vagy legacy maradvany, azt a reportban
  expliciten nevezd meg. Ne fedd el.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum lease scope-ban;
- hogy mit NEM szallit le meg (solver start, result, artifact, terminalis
  queue lifecycle);
- hogyan keruli el a duplafutast;
- hogyan kezeli a heartbeatet es az expired-lease reclaimet.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
