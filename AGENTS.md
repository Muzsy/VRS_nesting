# AGENTS.md — VRS Nesting (Codex / AI agent guide)

## Projekt cél

A repó célja egy DXF alapú nesting pipeline kialakítása, ahol a Sparrow (JeroenGar/sparrow) futtatása, az IO contract ellenőrzés, és a reprodukálható smoketest a központi minőségkapu.

Ez a fájl az AI agent futás közbeni **elsődleges szabálygyűjteménye**. Minden Codex feladat előtt ezt kell elolvasni.

---

## Repo-szabályok (nem alkuképes)

* **Valós repó elv:** nem találhatsz ki nem létező fájlokat, parancsokat, JSON mezőket, konvenciókat. Mindent kereséssel igazolj.
* **Codex outputs szabály:** csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel a feladat YAML step `outputs` listájában.
* **Minimal-invazív változtatás:** meglévő működést nem rontunk el; ha változtatás kockázatos (pl. IO contract), külön canvasban legyen rollback terv.
* **Titok / kulcs / token nem kerülhet repo-ba.** Ha később lesz (pl. privát registry, license), akkor `.env` + `.gitignore` és dokumentált setup.
* **Minőségkapu parancsot wrapperrel futtasd:**
  * Lokál: `./scripts/check.sh`
  * Codex/report: `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`

---

## Dokumentációs „szabványcsomag” (source of truth)

### Codex workflow

* `docs/codex/overview.md` – workflow + DoD
* `docs/codex/prompt_template.md` – egységes Codex prompt sablon
* `docs/codex/yaml_schema.md` – az egyetlen elfogadott goal YAML séma
* `docs/codex/report_standard.md` – Report Standard v2 (DoD→Evidence + Advisory)
* `codex/prompts/task_runner_prompt_template.md` – rövid futtató prompt (canvas+yaml alapján)

### QA / teszt

* `docs/qa/testing_guidelines.md` – tesztelési minimum + parancsok

---

## Repo gyors térkép

* `.github/workflows/` – CI pipeline-ok
* `scripts/` – futtatási/ellenőrzési belépési pontok (check/verify/smoketest/validator)
* `poc/` – bemeneti/kimeneti minták (pl. `poc/sparrow_io/swim.json`)
* `docs/` – specifikációk és fejlesztési dokumentáció
* `canvases/` – feladat specifikációk (canvasok)
* `codex/` – goal YAML-ek + checklistek + riportok

---

## Codex munkafolyamat (kötelező keret)

Minden feladat egy `TASK_SLUG` köré szerveződik, és a következő artefaktokat hozza létre/frissíti:

* `canvases/[<AREA>/]<TASK_SLUG>.md`
* `codex/goals/canvases/[<AREA>/]fill_canvas_<TASK_SLUG>.yaml`
* `codex/codex_checklist/[<AREA>/]<TASK_SLUG>.md`
* `codex/reports/[<AREA>/]<TASK_SLUG>.md`
* `codex/reports/[<AREA>/]<TASK_SLUG>.verify.log` *(automatikus, a `verify.sh` írja)*

Kötelező sorrend:

1. Felderítés (valós fájlok + minták)
2. Canvas megírása
3. Goal YAML (steps + outputs)
4. Implementáció a YAML szerint
5. Repo gate futtatása (automatikus verify + log + report frissítés)

   * Kötelező parancs: `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`
6. Checklist + report kitöltése

Részletek: `docs/codex/overview.md`

---

## Tooling elvárások

* **Python 3** szükséges (`scripts/validate_sparrow_io.py`, `scripts/verify.sh` report frissítéshez).
* **Git** szükséges (Sparrow forrás klónozás, diff/stat a verify reporthoz).
* **Rust toolchain + cargo** szükséges (Sparrow buildhez, ha nincs előre telepített bináris).
* **Shapely** ajánlott az overlap-check-hez; CI-ben telepítve van (`python3-shapely`).

---

## Forrás-igazság (prioritás, ha ellentmondás van)

1. `AGENTS.md`
2. `docs/` (Codex/QA szabályok)
3. `.github/workflows/` (CI valós működés)
4. `scripts/` (belépési pontok, quality gate)
5. `poc/` minták (IO contract és demo input/output)
6. `canvases/` és `codex/` futási artefaktok (feladat-specifikusak)
