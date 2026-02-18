# canvases/web_platform/phase2_p2_worker_loop_and_queue_processing.md

# Phase 2 P2.2 worker loop + queue processing

## Funkcio
A feladat a Phase 2.2 worker logika implementacioja: queue poll/claim, run status
atmenetek, ideiglenes workdir, input letoltes, CLI futtatas, artifact feltoltes,
DB frissites, cleanup.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `worker/main.py` worker loop implementacio;
  - queue claim (`FOR UPDATE SKIP LOCKED`) SQL alapu feldolgozas;
  - run status kezeles (`queued -> running -> done/failed`);
  - temp workdir + input download + `vrs_nesting.cli dxf-run` futtatas;
  - artifact upload es `run_artifacts` insert;
  - worker image CMD frissites a loop futtatashoz.
- Nincs benne:
  - SVG fallback renderer (`P2.3`);
  - runs API endpointek (`P2.4+`);
  - deployment/orchestration.

### Erintett fajlok
- `canvases/web_platform/phase2_p2_worker_loop_and_queue_processing.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p2_worker_loop_and_queue_processing.yaml`
- `codex/codex_checklist/web_platform/phase2_p2_worker_loop_and_queue_processing.md`
- `codex/reports/web_platform/phase2_p2_worker_loop_and_queue_processing.md`
- `worker/__init__.py`
- `worker/main.py`
- `worker/Dockerfile`
- `worker/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] P2.2/a-j pontok worker oldalon implementalva.
- [ ] Worker image alap CMD a worker loopot futtatja.
- [ ] Master checklist P2.2 pontok frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p2_worker_loop_and_queue_processing.md` PASS.

### Kockazat + rollback
- Kockazat: DB/storage API kulonbozo auth csatornai miatt runtime integracios hiba.
- Mitigacio: idempotens queue SQL + hibaturo cleanup + retry status kezeles.
- Rollback: worker modul + Dockerfile CMD visszaallitas kulon commitban.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase2_p2_worker_loop_and_queue_processing.md`

## Kapcsolodasok
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx` (Phase 2.2)
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md` (3.7 worker)
