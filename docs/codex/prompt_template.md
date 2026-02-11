# VRS Nesting Codex – Prompt sablon (prompt_template.md)

> Ez a sablon a VRS Nesting repóban futtatott Codex feladatok **egységes bemenete**. A cél a determinisztikus, auditálható végrehajtás: **felderítés → canvas → YAML → implementáció → gate → report**.

---

## 🎯 Funkció

Egy olyan „minden feladatra jó” prompt váz, ami:

* kényszeríti a Codexet a repo-szabályok betartására,
* minden feladatnál legeneráltatja a kötelező artefaktokat (canvas+yaml+checklist+report),
* biztosítja a Sparrow IO contract és a smoketest stabilitását.

---

## 🧠 Fejlesztési részletek

## 0) Használat

* Másold ki ezt a sablont.
* Töltsd ki a `<>` helyőrzőket.
* Add a Codexnek egyben.

**TASK_SLUG konvenció:**

* kisbetű
* szavak `_`-al elválasztva
* legyen beszédes, stabil

Példa: `sparrow_io_contract_update`, `check_sh_gate_unify`, `dxf_export_multi_sheet_wrapper`.

---

## 1) Kötelező bemenetek (a prompt kitöltéséhez)

* **TASK_TITLE:** `<rövid cím>`
* **TASK_SLUG:** `<egyedi azonosító>`
* **CÉL:** `<1-3 mondat>`
* **NEM CÉL:** `<mi NEM része>`
* **SCOPE:** `<érintett modulok / scriptek / doksik, ha ismert>`
* **KOCKÁZAT:** `<ha van, pl. IO contract törés>`
* **ELVÁRT GATE:** `<minimum elvárás, tipikusan ./scripts/verify.sh>`

---

## 2) VRS Nesting Codex Task Prompt (COPY-PASTE)

```text
# VRS Nesting Codex Task — <TASK_TITLE>
TASK_SLUG: <TASK_SLUG>

## 1) Kötelező olvasnivaló (prioritási sorrend)
Olvasd el és tartsd be, ebben a sorrendben:
1) AGENTS.md (repo-szabályok, gate parancsok)
2) docs/codex/overview.md (workflow és DoD)
3) docs/codex/yaml_schema.md (steps-séma kötelező)
4) docs/codex/report_standard.md (report struktúra + AUTO_VERIFY blokk)
5) docs/qa/testing_guidelines.md (minőségkapu részletek)

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél, és hol.

## 2) Cél
<CÉL>

## 3) Nem cél
<NEM CÉL>

## 4) Kötelező kimenetek (hozd létre / frissítsd)
> `<AREA>/` opcionális domain mappa (pl. `sparrow_io/`, `dxf_export/`). Ha nincs ilyen, maradhat a gyökérben.

1) canvases/[<AREA>/]<TASK_SLUG>.md
2) codex/goals/canvases/[<AREA>/]fill_canvas_<TASK_SLUG>.yaml
3) codex/codex_checklist/[<AREA>/]<TASK_SLUG>.md
4) codex/reports/[<AREA>/]<TASK_SLUG>.md
5) codex/reports/[<AREA>/]<TASK_SLUG>.verify.log  (auto)

## 5) Munkaszabályok (nem alkuképes)
- Valós repó elv: nem találhatsz ki fájlokat, JSON mezőket, parancsokat.
- Csak a ténylegesen létező fájlokra hivatkozz.
- Csak olyan fájlt módosíthatsz, ami szerepel az adott YAML step outputs listájában.
- Minimal-invazív változtatás: meglévő működés nem romolhat.

## 6) Kötelező workflow (nem ugorható át)
### 6.1 Felderítés
- Keresd meg a feladathoz releváns meglévő mintákat és fájlokat.
- Írj egy rövid listát: "Talált releváns fájlok" (útvonal + miért releváns).

### 6.2 Canvas létrehozása
Hozd létre a canvases/<TASK_SLUG>.md fájlt a kötelező szekciókkal:
- 🎯 Funkció
- 🧠 Fejlesztési részletek
- 🧪 Tesztállapot
- 🌍 Lokalizáció
- 📎 Kapcsolódások

A canvas tartalmazzon:
- pipálható feladatlistát
- érintett fájlok listáját (csak létező utak)
- kockázatok + rollback tervet
- teszt tervet (minőségkapu + feladat-specifikus ellenőrzések)

### 6.3 Goal YAML létrehozása
Hozd létre a codex/goals/canvases/fill_canvas_<TASK_SLUG>.yaml fájlt.
Kizárólag a steps-sémát használd:

steps:
  - name: "..."
    description: >
      ...
    outputs:
      - "..."

Szabály:
- minden módosított/létrehozott fájl szerepeljen valamely step outputs listájában
- legyen külön step a minőségkapu futtatására (a YAML legvégén)

### 6.4 Codex checklist + report
- Hozd létre/frissítsd: codex/codex_checklist/<TASK_SLUG>.md
  - legyen benne pipálható DoD lista és feladat-specifikus pontok
- Hozd létre/frissítsd: codex/reports/<TASK_SLUG>.md
  - kötelezően a docs/codex/report_standard.md szerkezete szerint
  - tartalmazza a DoD → Evidence Matrix részt (útvonal + sorsáv), evidence nélkül nincs PASS

### 6.5 Implementáció
- Hajtsd végre a YAML steps lépéseit sorrendben.
- Csak a step outputs fájlokat módosíthatod.

### 6.6 Gate / teszt / ellenőrzés
- Futtasd a standard ellenőrzést wrapperrel:
  - ./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md  (kötelező)

### 6.7 Zárás
- Töltsd ki a checklistet (pipáld ami kész).
- Töltsd ki a reportot a docs/codex/report_standard.md szerint.

## 7) Feladat-specifikus részletek
<SCOPE>

## 8) Output elvárás
A végén add meg a módosított/létrehozott fájlok teljes tartalmát (nem diffet), fájlonként külön blokkokban.
```

---

## 🧪 Tesztállapot

* A minimum gate mindig kötelező: `./scripts/verify.sh ...`.

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

* `AGENTS.md`
* `docs/codex/overview.md`
* `docs/codex/yaml_schema.md`
* `docs/codex/report_standard.md`
* `docs/qa/testing_guidelines.md`
