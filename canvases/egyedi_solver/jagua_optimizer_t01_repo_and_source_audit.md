# JG-01 — jagua_optimizer_t01_repo_and_source_audit

## Funkció

A JG-01 feladat célja a `jagua-rs` + saját optimizer átállási lánc első valóságellenőrzése: a repo jelenlegi állapotát, a már meglévő `jagua-rs` integrációt, a Python runner/adapter boundaryt, a meglévő cavity pipeline-t, a Sparrow minták szerepét, valamint a rectangular / irregular-remnant / hole-cavity kockázatokat kell kódszintű anchorokkal auditálni.

Ez **audit és döntés-előkészítő task**, nem solver-implementáció. A kimenete egy olyan forrásaudit, amely alapján a JG-02 solver module scaffold biztonságosan indítható vagy blokkolható.

## Source of truth

A feladat kizárólag repo-beli, ellenőrizhető forrásokra épülhet:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- a task szempontjából releváns valós kód és meglévő jelentések.

Ha bármely kötelező tervdokumentum hiányzik, a task `BLOCKED`.

## Stratégiai háttér

A master plan szerint a projekt nem kész Sparrow/SparrowGH solverre áll át, hanem egy `jagua-rs` collision / geometry backend + saját, ipari célú optimizer architektúrára. A Sparrowból csak keresési és repair-search minták vehetők át szelektíven. Az eredeti Sparrow strip-packing outer-loopja nem vehető át vakon fixed-sheet / multi-sheet / remnant célra.

A JG-01 feladata annak bizonyítása, hogy a repo jelenlegi állapota alapján milyen anchorokra lehet építeni, hol vannak mismatch-ek, és milyen kockázatokkal indítható a JG-02.

## Feladat scope

### Benne van

- Repo-szabályok és JG tervdokumentáció újraolvasása.
- A JG-01 task pontos kinyerése a task bontásból és checklistből.
- A `rust/vrs_solver` aktuális állapotának auditja.
- A `jagua-rs` dependency és valós használat auditja a Cargo/workspace és Rust kód alapján.
- A `docs/solver_io_contract.md` input/output szerződés auditja.
- A Python runner/adapter boundary auditja: `vrs_nesting/runner/vrs_solver_runner.py`, `vrs_nesting/runner/solver_adapter.py`.
- A meglévő cavity pipeline auditja: `worker/cavity_prepack.py`, `worker/cavity_validation.py`, `worker/result_normalizer.py`.
- A final validation / exact validation meglévő anchorjainak auditja: `scripts/validate_nesting_solution.py`, `vrs_nesting/nesting/instances.py`.
- A Sparrow minták és vendor/fallback útvonalak auditja: `scripts/ensure_sparrow.sh`, `scripts/run_sparrow_smoketest.sh`, `vrs_nesting/runner/sparrow_runner.py`, `poc/sparrow_io/*`.
- Audit report létrehozása: `docs/egyedi_solver/jagua_optimizer_source_audit.md`.
- Task-specifikus checklist, report és verify log frissítése.
- A globális JG progress checklist JG-01 szakaszának frissítése kizárólag a tényleges audit eredménye alapján.

### Nincs benne

- Nem szabad solver runtime viselkedést módosítani.
- Nem szabad új optimizer modult implementálni.
- Nem szabad `rust/vrs_solver/src/main.rs` refaktort végezni; ez JG-02 scope.
- Nem szabad `jagua-rs` verziót, Cargo feature-t vagy dependency graphot módosítani.
- Nem szabad Sparrow/SparrowGH külső kódot letölteni vagy vendorizálni.
- Nem szabad cavity-prepack viselkedést módosítani.
- Nem szabad quality profile-t, DXF importot, normalizálót vagy API runtime-ot módosítani.

## Kötelező globális invariánsok

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any task that produces or modifies nesting layout behavior must require exact final validation.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Aktuális repo snapshotból előzetesen azonosított anchorok

Ezeket a JG-01 végrehajtáskor újra ellenőrizni kell, és a reportban véglegesíteni kell path + line anchorral.

| Terület | Előzetes anchor | Miért fontos |
| --- | --- | --- |
| `jagua-rs` dependency | `rust/vrs_solver/Cargo.toml`, `rust/vrs_solver/Cargo.lock` | A solver crate jelenleg `jagua-rs = "0.6.4"` dependencyt tartalmaz. |
| Rust solver bemenet | `rust/vrs_solver/src/main.rs` | `SolverInput`, `Stock`, `Part`, `outer_points`, `holes_points`, `allowed_rotations_deg` struktúrák itt vannak. |
| Rust solver heurisztika | `rust/vrs_solver/src/main.rs` | A jelenlegi elhelyező egyszerű row/cursor jellegű; JG-01-ben bizonyítani kell, hogy nem ipari optimizer. |
| Jagua használat | `rust/vrs_solver/src/main.rs` | A kód `SPolygon`, `Edge`, `Point`, `CollidesWith` primitiveket használ feasibility jellegű ellenőrzésre. |
| Solver IO contract | `docs/solver_io_contract.md` | A `v1` JSON boundary rögzíti a stock/part/input/output mezőket és sheet-index semantics-et. |
| VRS runner | `vrs_nesting/runner/vrs_solver_runner.py` | Bináris feloldás, run-dir artefaktok, timeout, contract validation és meta írás itt történik. |
| Adapter boundary | `vrs_nesting/runner/solver_adapter.py` | Itt látszik a `vrs_solver` és Sparrow adapter egységesítése. |
| Exact/multi-sheet validáció | `vrs_nesting/nesting/instances.py`, `scripts/validate_nesting_solution.py` | Ezeket kell auditálni, hogy mire támaszkodhat JG-02+ exact validation policy. |
| Cavity-prepack | `worker/cavity_prepack.py`, `worker/cavity_validation.py`, `worker/result_normalizer.py` | A Phase 3 cavity és expansion/restore audit alapja. |
| Sparrow runner/gate | `scripts/ensure_sparrow.sh`, `scripts/run_sparrow_smoketest.sh`, `vrs_nesting/runner/sparrow_runner.py` | Sparrowból átvehető minták és meglévő regressziós útvonalak. |

## Kötelező audit output

A `docs/egyedi_solver/jagua_optimizer_source_audit.md` legalább ezeket a szakaszokat tartalmazza:

1. `# JG-01 Source Audit — jagua-rs + saját optimizer`
2. `## Scope and sources`
3. `## Repo rules and task source extraction`
4. `## Current vrs_solver state`
5. `## jagua-rs dependency and API usage`
6. `## Solver IO contract and runner boundary`
7. `## Existing validation anchors`
8. `## Cavity-prepack / expansion anchors`
9. `## Sparrow / search-pattern reuse anchors`
10. `## Rectangular Phase 1 readiness`
11. `## Irregular/remnant Phase 2 risks`
12. `## Hole/cavity Phase 3 risks`
13. `## License / dependency / build risks`
14. `## Reusable anchors table`
15. `## Blockers and REQUIRES_DECISION`
16. `## Recommendation for JG-02`

A reportban külön táblában kell rögzíteni: használható repo anchorok, `jagua-rs` képességek és hiányok, Sparrowból átvehető minták, rectangular / irregular / hole-cavity kockázatok, licenc/dependency/build megjegyzések, showstopper / no-showstopper döntés JG-02 indíthatóságáról.

## JG-01 DoD

- [ ] A JG-01 task pontosan azonosítva lett a task bontásban és checklistben.
- [ ] Repo szabályfájlok be lettek olvasva és reportban szerepelnek.
- [ ] `rust/vrs_solver` jelenlegi állapota auditálva lett kódszintű anchorokkal.
- [ ] `jagua-rs` dependency és használat auditálva lett Cargo/workspace és Rust kód alapján.
- [ ] `docs/solver_io_contract.md` releváns szerződései auditálva lettek.
- [ ] Python runner/adapter boundary auditálva lett.
- [ ] Meglévő cavity pipeline auditálva lett.
- [ ] Exact validation / solution validation anchorok auditálva lettek.
- [ ] Sparrowból átvehető minták külön táblában szerepelnek.
- [ ] Rectangular, irregular/remnant és hole/cavity kockázatok külön bontva szerepelnek.
- [ ] Licenc/dependency/build kockázatok dokumentálva lettek.
- [ ] Blokkolók és döntési javaslatok külön szakaszban szerepelnek.
- [ ] `docs/egyedi_solver/jagua_optimizer_source_audit.md` elkészült.
- [ ] Task-specifikus checklist frissült.
- [ ] Globális JG progress checklist JG-01 státusza frissült vagy explicit `BLOCKED/DEVIATION` megjegyzést kapott.
- [ ] Standard repo gate lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`.
- [ ] A reportban szerepel, hogy JG-02 indítható-e.

## Tesztelési és ellenőrzési terv

Minimum:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
p = Path('codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t01_repo_and_source_audit.yaml')
data = yaml.safe_load(p.read_text(encoding='utf-8'))
assert isinstance(data, dict) and isinstance(data.get('steps'), list) and data['steps']
print('YAML_OK')
PY
```

Task-specifikus audit sanity:

```bash
cargo metadata --manifest-path rust/vrs_solver/Cargo.toml --no-deps >/dev/null
python3 -m pytest -q tests/test_solver_adapter_contract.py tests/worker/test_cavity_prepack.py tests/worker/test_cavity_validation.py tests/worker/test_result_normalizer_cavity_plan.py
```

Kötelező végső gate:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
```

Ha bármelyik parancs környezeti dependency miatt nem fut, a reportban környezeti blocker/deviation státuszt kell adni, log taillel.

## Failure / rollback policy

- Ha kötelező forrásdokumentum hiányzik: `STATUS: BLOCKED`.
- Ha JG-00 nincs kész vagy a task index/master runner hiányzik: `STATUS: BLOCKED`.
- Ha a task végrehajtása közben production runtime kód módosul, rollback kötelező; ha nem rollbackelhető, `STATUS: REVISE`.
- Ha a `jagua-rs` / runner / validation anchorok között showstopper derül ki, azt `REQUIRES_DECISION` és `BLOCKED` vagy `STOP` státusszal kell rögzíteni.
- Ha a verify gate piros, a task nem lehet `PASS`, kivéve ha a hiba bizonyítottan külső/környezeti és a report `REVISE` státusszal lezárja.

## Phase gate érintettség

JG-01 a Gate 0 része. A JG-02 csak akkor indítható, ha JG-00 PASS, JG-01 source audit elkészült, nincs showstopper a `jagua-rs` dependency/build/API/contract irányban, és a report explicit módon kimondja: `JG-02 indítható` vagy `JG-02 blokkolt`, indokkal.
