# canvases/web_platform/phase2_p1_worker_image_bootstrap.md

# Phase 2 P2.1 worker image bootstrap

## Funkcio
A feladat a Phase 2.1 worker image blokk repo-szintu implementacioja:
Docker image definicio a worker futtatasahoz, ami tartalmazza a Python runtime-ot,
a `vrs_nesting` csomagot, a `vrs_solver` es `sparrow` binarisokat, valamint
publish workflow alapot container registry-hez.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - worker Dockerfile letrehozasa multi-stage builddel;
  - Python deps telepitese (`requirements.txt`);
  - `vrs_nesting` forras csomagolasa image-be;
  - `vrs_solver` es `sparrow` binaris build/copy image-be;
  - GHCR publish workflow definicio.
- Nincs benne:
  - worker loop implementacio (`P2.2`);
  - run API endpointek (`P2.4+`);
  - runtime orchestration/deployment (cloud service setup).

### Erintett fajlok
- `canvases/web_platform/phase2_p1_worker_image_bootstrap.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p1_worker_image_bootstrap.yaml`
- `codex/codex_checklist/web_platform/phase2_p1_worker_image_bootstrap.md`
- `codex/reports/web_platform/phase2_p1_worker_image_bootstrap.md`
- `worker/Dockerfile`
- `worker/README.md`
- `.github/workflows/worker-image.yml`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] P2.1/a-f technikai kovetelmenyek repo-szinten teljesulnek (`worker/Dockerfile` + workflow evidencia).
- [ ] P2.1/g-hez publish workflow kesz, manualis triggerrel registry push tamogatott.
- [ ] Master checklist P2.1 pontok frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p1_worker_image_bootstrap.md` PASS.

### Kockazat + rollback
- Kockazat: Docker build idoben Sparrow forras feloldas flakey lehet halozati korlatozasnal.
- Mitigacio: `scripts/ensure_sparrow.sh` reuse + pin commit fallback cache logikaval.
- Rollback: worker Dockerfile/workflow es checklist/report valtozasok visszavonasa egy commitban.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase2_p1_worker_image_bootstrap.md`

## Kapcsolodasok
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx` (Phase 2.1)
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md` (3.7 worker + docker)
