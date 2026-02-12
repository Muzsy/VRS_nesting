# Determinizmusra hash-stabilitasi smoke teszt bevezetese

## 🎯 Funkcio
A task celja az azonos input+seed melletti output hash stabilitas explicit ellenorzese a quality gate-ben: ket egymas utani solver futas output hash-e legyen azonos.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `scripts/check.sh` bovitese determinism smoke lepesre (ket run + hash osszehasonlitas).
  - CI workflow (`nesttool-smoketest`) bovitese ugyanilyen hash stabilitasi ellenorzessel.
  - Checklist + report artefaktok letrehozasa.
- Nincs benne:
  - Solver algoritmus ujratervezese.
  - Floating-point vagy RNG policy globalis atalakitas.
  - Sparrow determinism extra audit.

### Erintett fajlok
- `canvases/egyedi_solver/determinism_hash_stability_smoke.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_determinism_hash_stability_smoke.yaml`
- `scripts/check.sh`
- `.github/workflows/nesttool-smoketest.yml`
- `codex/codex_checklist/egyedi_solver/determinism_hash_stability_smoke.md`
- `codex/reports/egyedi_solver/determinism_hash_stability_smoke.md`

### DoD
- [ ] `scripts/check.sh` futtat ket egymas utani azonos input+seed solver run-t.
- [ ] A ket run output hash-e explicit osszehasonlitasra kerul, es mismatch esetben FAIL.
- [ ] A CI workflow tartalmazza a determinism hash stability ellenorzest.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_hash_stability_smoke.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: hash mismatch idonkenti flakiness miatt (nem determinisztikus sorrend/fp drift).
- Mitigacio: azonos input snapshot, fix seed/time_limit, runner meta `output_sha256` alapjan ellenorzes.
- Rollback: az uj determinism lepes izolaltan kiveheto a check/workflow scriptbol.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_hash_stability_smoke.md`
- Task-specifikus ellenorzesek:
  - `./scripts/check.sh`
  - CI workflow lint/syntax check (ha relevans)

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_p0_audit.md`
- `docs/qa/testing_guidelines.md`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
