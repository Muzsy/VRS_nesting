# VRS Nesting – Tesztelési irányelvek (testing_guidelines.md)

## 🎯 Funkció

Ez a dokumentum rögzíti a VRS Nesting projektben a **kötelező minőségkaput** (pytest unit tests + Sparrow build + IO smoketest + validator), a determinisztikus futtatási elveket, és azt, mit kell a Codexnek mindig lefuttatnia és dokumentálnia.

---

## 🧠 Fejlesztési részletek

## 1) Minőségkapu (kötelező)

### 1.1 Standard (lokál)

* `./scripts/check.sh`
  * futtatja a `python3 -m pytest -q` unit teszteket (fail-fast)
  * Sparrow pin + build (ha nincs előre megadott bináris)
  * Sparrow IO smoketest + IO validator
  * DXF import convention smoke
  * geometry/polygonize/offset robustness smoke
  * DXF export smoke (`--run-dir`)
  * BLOCK/INSERT eredeti geometria export smoke
  * multisheet wrapper edge-case smoke
  * valós DXF fixture import smoke
  * valós DXF + Sparrow pipeline smoke
  * `vrs_solver` build + nesting solution validator smoke
  * determinisztika hash-stabilitás smoke
  * timeout/perf guard smoke

### 1.2 Codex/report (kötelező)

* `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`
  * futtatja: `./scripts/check.sh`
  * menti: `codex/reports/.../<TASK_SLUG>.verify.log`
  * frissíti a report AUTO_VERIFY blokkot

**Szabály:** Codex futás végén mindig a `verify.sh` az elvárt.

---

## 2) Mi számít tesztnek ebben a repóban?

A repó jelenlegi tesztkészlete:

* Pytest unit tesztek (`tests/`, `pytest.ini`)

* Sparrow futtatás egy rögzített POC bemeneten (alapértelmezés: `poc/sparrow_io/swim.json`)
* Output contract ellenőrzés: `scripts/validate_sparrow_io.py`
* DXF import/export smoke suite + valós DXF fixture smoke
* Multisheet wrapper edge-case smoke
* `vrs_solver` validator + determinisztika + time-budget guard smoke
* (ha elérhető) overlap-check shapely-vel

A belépési pont: `scripts/run_sparrow_smoketest.sh`.

### 2.1 Pytest tooling

Lokál és CI környezetben a `check.sh` miatt szükséges:

* `python3`
* `python3-pytest` (apt csomag)
* `python3-shapely` (overlap-check smoke-hoz)
* `git` (Sparrow clone/pin lépésekhez)
* `cargo` / Rust toolchain (Sparrow build, illetve `vrs_solver` build)
* `ezdxf` (különösen a valós DXF smoke-okhoz)

Telepítés (Ubuntu/Debian):

* `sudo apt-get update && sudo apt-get install -y python3 python3-pytest python3-pip python3-shapely git`
* `python3 -m pip install --break-system-packages ezdxf`

---

## 3) Determinizmus és stabilitás

### 3.1 Fix bemenet + seed + time limit

A smoketest célja nem a „legjobb nesting”, hanem a **stabil contract és a reprodukálhatóság**.

* `SEED` környezeti változóval fixáljuk (alap: `0`)
* `TIME_LIMIT` környezeti változóval korlátozzuk (alap: `60`)

### 3.2 Sparrow verzió pin

Ha létezik: `poc/sparrow_io/sparrow_commit.txt`, akkor a buildnek ezt kell használni.

**Szabály:** ha a CI-ben flakiness jelenik meg, az első lépés a commit pin és a seed/time limit felülvizsgálata.

### 3.3 IO contract változás

Ha módosul a `scripts/validate_sparrow_io.py` vagy bármely POC minta:

* legyen új/extra invariáns dokumentálva a canvasban,
* legyen a reportban DoD→Evidence bizonyíték,
* és fusson a gate.

---

## 4) Mikor kell plusz teszt / minta?

* Geometria algoritmus módosítás → legalább 1 új POC input a `poc/` alatt.
* Parser / export változás → input + expected output struktúra frissítése, validator bővítés.
* Több sheet / multi-run wrapper → legalább 1 „multi” POC minta.
* Új teszt típus (pl. benchmark/integration) bevezetése → a standard gate (`scripts/check.sh`) és ez a dokumentáció együtt frissítendő.

---

## 5) Codex kötelező dokumentálás (checklist + report)

### 5.1 Checklist minimum

* [ ] Releváns fájlok azonosítva (felderítés)
* [ ] Canvas elkészült (kockázat + rollback + DoD)
* [ ] YAML steps + outputs pontos (outputs szabály betartva)
* [ ] `./scripts/verify.sh --report ...` lefutott
* [ ] Report DoD→Evidence Matrix kitöltve

### 5.2 Report minimum

A reportot **kötelezően** a `docs/codex/report_standard.md` szerint kell kitölteni:

* státusz: PASS / FAIL / PASS_WITH_NOTES
* futtatott parancsok + eredmény
* változások összefoglalója
* DoD → Evidence Matrix (bizonyítékokkal)

---

## 🧪 Tesztállapot

A feladat akkor kész, ha a gate zöld, és a reportban minden DoD ponthoz van bizonyíték.

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

* `AGENTS.md`
* `scripts/check.sh`
* `scripts/run_sparrow_smoketest.sh`
* `scripts/validate_sparrow_io.py`
* `docs/codex/report_standard.md`
