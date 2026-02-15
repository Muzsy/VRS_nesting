PASS

## 1) Meta

- **Task slug:** `ci_gate_check_sh`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/ci_gate_check_sh.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_ci_gate_check_sh.yaml`
- **Futas datuma:** `2026-02-15`
- **Branch / commit:** `main@d2064ec`
- **Fokusz terulet:** `CI | Docs | Quality Gate`

## 2) Scope

### 2.1 Cel

- A `./scripts/check.sh` valjon a lokalis, Codex verify es CI oldali kozos gate-te.
- A bovitett smoke suite jelenjen meg explicit modon a QA/Codex dokumentacioban.
- Keszitsen uj CI workflow-t, ami egyetlen paranccsal futtatja a repo gate-et.

### 2.2 Nem-cel (explicit)

- A mar meglevo `nesttool-smoketest` es `sparrow-smoketest` workflow-k kivaltasa.
- Dependency management rendszer (requirements/pyproject) bevezetese.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok

- `canvases/egyedi_solver/ci_gate_check_sh.md`
- `docs/qa/testing_guidelines.md`
- `docs/codex/overview.md`
- `.github/workflows/repo-gate.yml`
- `codex/codex_checklist/egyedi_solver/ci_gate_check_sh.md`
- `codex/reports/egyedi_solver/ci_gate_check_sh.md`

### 3.2 Miert valtoztak?

- A bovitett smoke suite mar a `check.sh` resze, de ezt a docs nem reszletezte, es CI-ben nem volt egysoros ossz-gate workflow.
- A valtozas celja, hogy lokalis/verify/CI ugyanazt a gate-et hasznalja.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/ci_gate_check_sh.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `./scripts/check.sh` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-15T13:36:30+01:00 → 2026-02-15T13:38:08+01:00 (98s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/ci_gate_check_sh.verify.log`
- git: `main@d2064ec`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 docs/codex/overview.md        |  2 +-
 docs/qa/testing_guidelines.md | 23 +++++++++++++++++++++--
 2 files changed, 22 insertions(+), 3 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/codex/overview.md
 M docs/qa/testing_guidelines.md
?? .github/workflows/repo-gate.yml
?? canvases/egyedi_solver/ci_gate_check_sh.md
?? codex/codex_checklist/egyedi_solver/ci_gate_check_sh.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_ci_gate_check_sh.yaml
?? codex/reports/egyedi_solver/ci_gate_check_sh.md
?? codex/reports/egyedi_solver/ci_gate_check_sh.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| Testing guidelines tartalmazza a `check.sh` szokasos vegfuttatast + fo lepeseket | PASS | `docs/qa/testing_guidelines.md:15` | A gate komponensek felsorolasa explicitre bovult. | Doksireview |
| Testing guidelines kiemeli az `ezdxf` fuggoseget es ad telepitesi tippet | PASS | `docs/qa/testing_guidelines.md:65` | A dependency lista es install tipp kulon tartalmazza az `ezdxf`-et. | Doksireview |
| Codex overview gate leiras szinkronban a check.sh valos lepeseivel | PASS | `docs/codex/overview.md:68` | A gate sor frissult a bovitett smoke suite leirasara. | Doksireview |
| Uj CI workflow futtatja a `./scripts/check.sh` gate-et | PASS | `.github/workflows/repo-gate.yml:29` | Uj workflow egyetlen gate parancsot futtat, rust + deps telepitessel. | Workflow review |
| Workflow trigger + deps + artifact upload teljesul | PASS | `.github/workflows/repo-gate.yml:3` | Triggerek, apt/pip deps (`ezdxf`) es failure artifact upload beallitva. | Workflow review |
| Verify PASS es auto log generalas megtortent | PASS | `codex/reports/egyedi_solver/ci_gate_check_sh.verify.log:1` | Verify wrapper frissitette a report auto blokkjat es logot irt. | `./scripts/verify.sh --report ...` |

## 8) Advisory notes (nem blokkolo)

- A repo-gate workflow jelenleg a meglevo ket smoke workflow mellett fut, nem helyettesiti azokat.
