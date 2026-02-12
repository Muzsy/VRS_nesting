PASS_WITH_NOTES

## 1) Meta

- Task slug: `rotation_policy_and_instance_regression`
- Kapcsolodo canvas: `canvases/egyedi_solver/rotation_policy_and_instance_regression.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_rotation_policy_and_instance_regression.yaml`
- Futas datuma: `2026-02-12`
- Fokusz terulet: `Docs | Planning`

## 2) Scope

### 2.1 Cel
- P1 scaffold a rotacios policy + instance regresszio taskhoz.
- Ellenorzesi terv + P0 regresszio-orseg rogzites.

### 2.2 Nem-cel
- Funkcionalis implementacio.
- Repo gate futtatas ebben a task-specifikus reportban.

## 3) Scaffold statusz

- Canvas + goal YAML + runner prompt letrehozva.
- Checklist letrehozva.
- Kotelezo kapu kesobbi futtatashoz rogzitve.

## 4) Kotelezo verify a kesobbi runhoz

- `./scripts/verify.sh --report codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
- Vart log: `codex/reports/egyedi_solver/rotation_policy_and_instance_regression.verify.log`

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-12T21:47:09+01:00 → 2026-02-12T21:48:16+01:00 (67s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/rotation_policy_and_instance_regression.verify.log`
- git: `main@7aabc83`
- módosított fájlok (git status): 1

**git status --porcelain (preview)**

```text
?? codex/reports/egyedi_solver/rotation_policy_and_instance_regression.verify.log
```

<!-- AUTO_VERIFY_END -->
