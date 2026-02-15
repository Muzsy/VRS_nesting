# VRS Nesting Codex – Áttekintés (overview.md)

## 🎯 Funkció

Ez a dokumentum rögzíti a VRS Nesting repóban használt **Codex-munkafolyamatot**: hogyan készülnek a **canvas + goal YAML** fájlok, hogyan dolgozik a Codex a kódbázisban, és mik a **kötelező minőségkapuk** (smoketest/validator + report).

**Cél:** a Codex feladatok végrehajtása legyen determinisztikus, auditálható és repo‑kompatibilis.

**Kimenet-alapú fejlesztés:** minden érdemi változtatás előtt előbb elkészül a canvas+yaml, és csak ezután történik implementáció.

---

## 🧠 Fejlesztési részletek

### 1) Alapelvek

* **Valós repó elv:** a Codex nem találhat ki fájlokat, parancsokat, JSON mezőket, konvenciókat. Mindent kereséssel kell azonosítani.
* **Minimal-invazív módosítás:** meglévő működést nem törünk; csak a szükséges részeket érintjük.
* **Egy feladat = egy slug:** minden Codex feladat kap egy egyedi `TASK_SLUG` azonosítót (pl. `sparrow_io_contract_update`, `dxf_import_arc_polygonize_fix`).
* **Kimenetek kötelezőek:** a feladat akkor „kész”, ha a dokumentáció + kód + ellenőrzés + report együtt megvan.

### 2) Kötelező artefaktok (minden feladathoz)

A `TASK_SLUG` alapján mindig készüljön:

> **Megjegyzés:** az `<AREA>/` opcionális domain mappa (pl. `sparrow_io/`, `dxf_import/`). Ha nincs ilyen mappa, maradhatnak a fájlok a gyökérben.

1. **Canvas (feladatleírás):**
   * `canvases/[<AREA>/]<TASK_SLUG>.md`

2. **Goal YAML (végrehajtási lépések):**
   * `codex/goals/canvases/[<AREA>/]fill_canvas_<TASK_SLUG>.yaml`

3. **Codex checklist (pipálható minőségkapu):**
   * `codex/codex_checklist/[<AREA>/]<TASK_SLUG>.md`

4. **Codex report (futtatások + eredmények):**
   * `codex/reports/[<AREA>/]<TASK_SLUG>.md`
   * `codex/reports/[<AREA>/]<TASK_SLUG>.verify.log`

> **Report szabvány:** a reportot kötelezően a `docs/codex/report_standard.md` (Report Standard v2) szerint kell kitölteni (DoD→Evidence + Advisory).

### 3) Canvas kötelező tartalma

A canvas feladata, hogy a Codex számára **végrehajtható specifikációt** adjon. Minimum:

* Konkrét cél és nem-cél (mi NEM része a feladatnak)
* Érintett fájlok listája (csak létező, megtalált útvonalak)
* Pipálható feladatlista
* Kockázatok + rollback terv
* Teszt terv: milyen ellenőrzést futtatsz / frissítesz (legalább `./scripts/verify.sh`)

### 4) Goal YAML séma (VRS szabvány)

A goal YAML **csak** a `steps` sémát használja (részletek: `docs/codex/yaml_schema.md`).

Szabályok:

* **Kötelező:** a YAML **legutolsó** stepje legyen a **"Repo gate (automatikus verify)"** (parancs: `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`).
* Minden lépés legyen kicsi és ellenőrizhető (1–4 fájl ideális).
* **Csak** olyan fájlt szabad módosítani, ami szerepel az adott lépés `outputs` listájában.
* A Repo gate step `outputs` listája tartalmazza a reportot **és** a hozzá tartozó logot: `codex/reports/[<AREA>/]<TASK_SLUG>.verify.log`.

### 5) Minőségkapu (repo gate)

A standard minőségkapu ebben a repóban:

* `./scripts/check.sh` – pytest unit tests (fail-fast) + mypy type-check (fail-fast) + Sparrow build/pin (ha kell) + IO smoketest/validator + DXF smoke suite (import/geometry/export/BLOCK-INSERT/multisheet/valós DXF pipeline) + `vrs_solver` validator + determinisztika + timeout/perf guard

Codex futásnál kötelező a wrapper, ami logot ment és frissíti a reportot:

* `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`

### 6) Ajánlott Codex futási sorrend

1. **Felderítés:** releváns fájlok, szabályok, meglévő minták megkeresése.
2. **Canvas elkészítése:** specifikáció + DoD + rollback.
3. **Goal YAML elkészítése:** lépések + outputs.
4. **Implementáció:** lépésről lépésre, a YAML szerint.
5. **Repo gate futtatása:** `./scripts/verify.sh --report ...`.
6. **Checklist + report lezárása:** checklist kipipálása + report kitöltése.

---

## 🧪 Tesztállapot

### Kötelező minimum ellenőrzések

* `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md` (ez futtatja a `./scripts/check.sh`-t, logot ment és frissíti a reportot)

### Mikor kell plusz ellenőrzés?

* IO contract / validator módosítás → új vagy frissített POC JSON + validator bővítés.
* Sparrow futtatás paraméterezés → dokumentált defaultok + CI kompatibilitás.
* Geometria algoritmus módosítás → legalább egy új/extra bemeneti minta a `poc/` alatt.

---

## 🌍 Lokalizáció

Nem releváns ebben a repóban (nincs UI lokalizáció).

---

## 📎 Kapcsolódások

* `AGENTS.md` – a Codex futás közbeni repo-szabályok elsődleges forrása
* `docs/codex/prompt_template.md` – egységes Codex prompt sablon
* `docs/codex/yaml_schema.md` – goal YAML steps-séma
* `docs/codex/report_standard.md` – report struktúra + AUTO_VERIFY blokk
* `docs/qa/testing_guidelines.md` – minőségkapu részletek
