# VRS Nesting – Codex Dry Run Checklist (dry_run_checklist.md)

## 🎯 Funkció

Ez a checklist egy **„száraz futás”** (dry run) ellenőrzőlista Codex feladatokhoz.

Célja:

* még a kódmódosítás előtt kiszűrni a tipikus hibákat (rossz fájlútvonal, hiányzó szabály, rossz scope, hiányzó gate),
* biztosítani, hogy a canvas+yaml **végrehajtható**, a repó szabályoknak megfelelő és auditálható.

**Szabály:** a dry run checklistet a Codex **mindig** kitölti a tényleges implementáció előtt, és a feladat `codex/codex_checklist/<TASK_SLUG>.md` fájljába beemeli (vagy hivatkozza).

---

## 🧠 Fejlesztési részletek

### Kötelező fájl

* `codex/codex_checklist/[<AREA>/]<TASK_SLUG>.md`

Ebben a fájlban a DoD checklist mellett legyen benne ez a dry run rész is (vagy hivatkozás rá).

---

## 🧪 Tesztállapot

## Dry Run Checklist – pipálható

### 0) Alapok

* [ ] `TASK_SLUG` egyedi, beszédes, stabil (kisbetű, `_` elválasztás)
* [ ] A feladat célja 1–3 mondatban egyértelmű
* [ ] A „nem cél” lista konkrét (mi NEM része)
* [ ] A scope (érintett scripts/algoritmus/docs/CI) rögzítve van

### 1) Repó-szabályok és források

* [ ] `AGENTS.md` elolvasva és a szabályok beépítve a megoldásba
* [ ] A releváns docs szabályfájlok azonosítva (`docs/codex/*`, `docs/qa/*`)
* [ ] Ha valamelyik docs hiányzik: dokumentáltam, és nem találtam ki helyette szabályt

### 2) Valós fájlok ellenőrzése (no-hallucination)

* [ ] Minden hivatkozott fájl valóban létezik a repóban
* [ ] Minden új fájlnak megvan a pontos célkönyvtára (repo-konvenció szerint)
* [ ] Nincs kitalált JSON mező / IO contract elem / parancs

### 3) Canvas minőség (canvases/<TASK_SLUG>.md)

* [ ] A canvas tartalmazza a kötelező szekciókat:

  * [ ] 🎯 Funkció
  * [ ] 🧠 Fejlesztési részletek
  * [ ] 🧪 Tesztállapot
  * [ ] 🌍 Lokalizáció
  * [ ] 📎 Kapcsolódások

* [ ] Van pipálható feladatlista, és lépésenként végrehajtható
* [ ] Van kockázat és rollback terv (ha érint contractot / gate-et)
* [ ] Van konkrét tesztterv (legalább `./scripts/verify.sh`)

### 4) YAML minőség (fill_canvas_<TASK_SLUG>.yaml)

* [ ] Csak a `steps/name/description/outputs` séma van használva
* [ ] A lépések kicsik és ellenőrizhetők (ideális 1–4 fájl / step)
* [ ] Minden step `description` végrehajtható, nem „gondolkodós”
* [ ] A YAML nem tartalmaz `analyze/summarize/plan` jellegű meta utasítást
* [ ] Minden módosított/létrehozott fájl szerepel valamely step `outputs` listájában
* [ ] A YAML legvégén van külön gate step (`./scripts/verify.sh ...`)

### 5) Scope és módosítási határok

* [ ] A változtatás célpontja egyértelmű (pl. `scripts/`, `poc/`, `.github/workflows/`, `docs/`)
* [ ] Nem nyúlok indokolatlanul több területhez (nincs “szétszórt quick fix”)
* [ ] Contract/validator változás esetén van `poc/` frissítés terve

### 6) Teszt és minőségkapu

* [ ] Az elvárt gate parancs rögzítve:

  * [ ] `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`
  * [ ] (opcionális) `./scripts/check.sh`
  * [ ] `./scripts/check.sh` részeként a `python3 -m pytest -q` is lefut (fail-fast)
  * [ ] `./scripts/check.sh` részeként a `python3 -m mypy --config-file mypy.ini vrs_nesting` is lefut (fail-fast)

* [ ] A report útvonala rögzítve: `codex/reports/[<AREA>/]<TASK_SLUG>.md`
* [ ] A log útvonala rögzítve: `codex/reports/[<AREA>/]<TASK_SLUG>.verify.log`
* [ ] Python dependency változás esetén frissítve vannak a `.in` és pinelt `requirements*.txt` fájlok, és a CI telepítés ezekre mutat

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

* `docs/codex/overview.md`
* `docs/codex/prompt_template.md`
* `docs/codex/yaml_schema.md`
* `docs/codex/report_standard.md`
* `docs/qa/testing_guidelines.md`
* `codex/codex_checklist/` (feladatspecifikus checklistek)
* `codex/reports/` (futtatási riportok)
