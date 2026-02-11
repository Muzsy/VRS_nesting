# VRS Nesting Codex – YAML séma (yaml_schema.md)

## 🎯 Funkció

Ez a dokumentum rögzíti a VRS Nesting repóban használt **egyetlen elfogadott Codex goal YAML sémát**.

**Cél:** a Codex végrehajtás legyen determinisztikus és auditálható: minden lépés explicit, minden fájl érintettsége előre deklarált.

---

## 🧠 Fejlesztési részletek

## 1) Elfogadott séma (kötelező)

A VRS goal YAML-ek **kizárólag** ezt a sémát használhatják:

```yaml
steps:
  - name: "<lépés neve>"
    description: >
      <részletes, végrehajtható utasítások>
    outputs:
      - "<fájl útvonal>"
      - "<fájl útvonal>"
```

### Kötelező mezők

* `steps` (lista)
* Minden stepben:
  * `name` (string)
  * `description` (multiline string, `>` ajánlott)
  * `outputs` (string lista)

### Opcionális mezők

* `inputs` (string lista) – csak akkor, ha a lépés konkrét bemeneti fájlokra támaszkodik, és ezt auditálni akarjuk.

Példa:

```yaml
steps:
  - name: "Felderítés és érintett fájlok rögzítése"
    description: >
      Keresd meg a releváns modulokat és meglévő mintákat a repóban. Írd össze a
      talált fájlokat és helyezd el őket a canvas kapcsolódó szekciójába.
    outputs:
      - "canvases/example_task.md"

  - name: "Validator bővítése"
    description: >
      Frissítsd a Sparrow IO validátort a kívánt új szabály(ok)kal. Ha szükséges,
      adj hozzá új POC inputot a poc/ alá.
    outputs:
      - "scripts/validate_sparrow_io.py"
      - "poc/sparrow_io/swim.json"

  - name: "Repo gate (automatikus verify)"
    description: >
      Futtasd a standard ellenőrzést és frissítsd automatikusan a reportot.
      Parancs: ./scripts/verify.sh --report codex/reports/example_task.md
    outputs:
      - "codex/reports/example_task.md"
      - "codex/reports/example_task.verify.log"
```

---

## 2) Globális szabályok (nem alkuképes)

### 2.1 Outputs szabály – fájl érintettség

* A Codex **csak** olyan fájlt hozhat létre vagy módosíthat, ami szerepel a step `outputs` listájában.
* Ha egy fájl módosítása szükséges, de nem szerepel outputsban: a YAML-t előbb frissíteni kell.

### 2.2 Egy step = ellenőrizhető egység

* Egy step legyen **kicsi** és ellenőrizhető.
* Ideális: 1–4 fájl az outputsban.
* Nagy refaktor: több stepre bontva.

### 2.3 Kizárt "meta" parancsok

A YAML nem tartalmazhat:

* `analyze`, `summarize`, `plan` jellegű parancsokat
* „csak gondold át” jellegű lépéseket

A leírásnak végrehajthatónak kell lennie.

---

## 3) Kötelező ellenőrző lépések (minőségi gate)

Minden feladat YAML-jának **legutolsó** stepje legyen egy minőségi kapu, ami:

* lefuttatja a standard ellenőrzést a `./scripts/verify.sh` wrapperen keresztül
* a **reportot automatikusan frissíti** (PASS/FAIL + log hivatkozás)
* a logot elmenti a report mellé

**Standard parancs:**

* `./scripts/verify.sh --report codex/reports/<feature>/<name>.md`

**Standard outputs (kötelező):**

* `codex/reports/<feature>/<name>.md`
* `codex/reports/<feature>/<name>.verify.log`

Ajánlott step name: **"Repo gate (automatikus verify)"**

---

## 4) Naming konvenciók

### 4.1 YAML fájlnév

* `codex/goals/canvases/fill_canvas_<TASK_SLUG>.yaml`

### 4.2 Step name

* rövid, cselekvő ige + tárgy
* magyar nyelv

### 4.3 Outputs útvonal

* teljes repo relatív útvonal
* mindig idézőjelben

---

## 🧪 Tesztállapot

### Kötelező minimum

* Minden YAML **legutolsó** stepje legyen a minőségi kapu (`./scripts/verify.sh`).
* Ha bemeneti/kimeneti contract változik: legyen `poc/` minta is (outputs-ban).

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

* `docs/codex/overview.md` – workflow és DoD
* `docs/codex/prompt_template.md` – egységes prompt
* `docs/codex/report_standard.md` – report struktúra + AUTO_VERIFY blokk
* `docs/qa/testing_guidelines.md` – minőségkapu részletek
