# canvases/web_platform/phase4_p5_load_profile_and_snapshot.md

# Phase 4 P5 load profile + snapshot

## Funkcio
A P4.5 celja terhelesi baseline keszitese: 10 parhuzamos run-inditas es 50 parhuzamos viewer session
profillal, majd performance snapshot riport rogzitese.

## Scope
- Benne van:
  - in-process ASGI load smoke script mockolt backenddel;
  - 10 concurrent run + 50 concurrent viewer meres;
  - latency/error-rate snapshot;
  - duplikalt run-id ellenorzes (no double-processing jelzes).
- Nincs benne:
  - valos cloud infrastrukturan futtatott k6/locust benchmark;
  - p95 strict release gate.

## Erintett fajlok
- `canvases/web_platform/phase4_p5_load_profile_and_snapshot.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p5_load_profile_and_snapshot.yaml`
- `codex/codex_checklist/web_platform/phase4_p5_load_profile_and_snapshot.md`
- `codex/reports/web_platform/phase4_p5_load_profile_and_snapshot.md`
- `codex/reports/web_platform/phase4_p5_load_profile_and_snapshot.verify.log`
- `scripts/smoke_phase4_load_profile.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] 10 concurrent run create load teszt PASS.
- [ ] 50 concurrent viewer-data load teszt PASS.
- [ ] Snapshot riport tartalmazza latency/error-rate metrikakat.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p5_load_profile_and_snapshot.md` PASS.
