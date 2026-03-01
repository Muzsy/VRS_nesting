# VRS Nesting – Tesztelési irányelvek (testing_guidelines.md)

## 🎯 Funkció

Ez a dokumentum rögzíti a VRS Nesting projektben a **kötelező minőségkaput** (pytest + mypy + Sparrow build + IO smoketest + validator), a determinisztikus futtatási elveket, és azt, mit kell a Codexnek mindig lefuttatnia és dokumentálnia.

---

## 🧠 Fejlesztési részletek

## 1) Minőségkapu (kötelező)

### 1.1 Standard (lokál)

* `./scripts/check.sh`
  * futtatja a `python3 -m pytest -q` unit teszteket (fail-fast)
  * futtatja a `python3 -m mypy --config-file mypy.ini vrs_nesting` type-checket (fail-fast)
  * Sparrow feloldás/build a `scripts/ensure_sparrow.sh`-n keresztül
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

### 1.3 CI kötelező check (PR merge gate)

* Kötelező PR check: **`repo-gate-required / repo_gate`**
  * workflow: `.github/workflows/repo-gate.yml`
  * a workflow futtatja a teljes `./scripts/check.sh` minőségkaput
* A többi workflow (`sparrow-io-smoketest`, `nesttool-smoketest`) kiegészítő smoke jellegű; nem kötelező merge gate.
* Nightly perf baseline workflow: `nightly-perf-baseline`
  * workflow: `.github/workflows/nightly-perf-baseline.yml`
  * futtatja: `python3 scripts/smoke_time_budget_guard.py --require-real-solver --perf-threshold-s 5.0 --baseline-json artifacts/nightly_perf_baseline.json`
  * publikálja: `nightly_perf_baseline.json` artifactot trend/baseline követéshez
  * threshold jelzés: GitHub Actions warning/notice summary + script fail, ha a küszöb sérül

---

## 2) Mi számít tesztnek ebben a repóban?

A repó jelenlegi tesztkészlete:

* Pytest unit tesztek (`tests/`, `pytest.ini`)
* Mypy type-check (`mypy.ini`, scope: `vrs_nesting/`)

* Sparrow futtatás egy rögzített POC bemeneten (alapértelmezés: `poc/sparrow_io/swim.json`)
* Output contract ellenőrzés: `scripts/validate_sparrow_io.py`
* DXF import/export smoke suite + valós DXF fixture smoke
* Multisheet wrapper edge-case smoke
* `vrs_solver` validator + determinisztika + time-budget guard smoke
* (ha elérhető) overlap-check shapely-vel

A belépési pont: `scripts/run_sparrow_smoketest.sh`.

### 2.1 Pytest + mypy tooling

Lokál és CI környezetben a `check.sh` miatt szükséges:

* `python3`
* `git` (Sparrow fallback klónozás/pin lépésekhez; `vendor/sparrow` használatakor ez a rész elhagyható)
* `cargo` / Rust toolchain (Sparrow build, illetve `vrs_solver` build)
* Python deps-ek a pinelt `requirements-dev.txt`-ből (`pytest`, `mypy`, `shapely`, `ezdxf`, stb.)

Telepítés (Ubuntu/Debian):

* `sudo apt-get update && sudo apt-get install -y python3 python3-pip git`
* `python3 -m pip install --break-system-packages -r requirements-dev.txt`

Dependency frissítés (reprodukálható mód):

* `requirements.in` / `requirements-dev.in` módosítása
* `python3 -m piptools compile requirements.in -o requirements.txt`
* `python3 -m piptools compile requirements-dev.in -o requirements-dev.txt`

---

## 3) Determinizmus és stabilitás

### 3.1 Fix bemenet + seed + time limit

A smoketest célja nem a „legjobb nesting”, hanem a **stabil contract és a reprodukálhatóság**.

* `SEED` környezeti változóval fixáljuk (alap: `0`)
* `TIME_LIMIT` környezeti változóval korlátozzuk (alap: `60`)

### 3.1.1 Timeout-bound determinism policy

Definicio: timeout-bound futasnak tekintjuk, ha a futasban `TIME_LIMIT_EXCEEDED` reason jelenik meg,
vagy a futasi ido a `time_limit` hatart eleri.

Szabaly:

* Determinizmus gate-et csak olyan fixture-re szabad kotelezo merge-gate checkkent hasznalni,
  ami kenyelmesen a `time_limit` alatt vegez (nem timeout-hatarkozeli).
* Timeout-hatarkozeli benchmarknal a hash driftet kulon timeout-bound kategoriakent kell jelenteni,
  es nem szabad automatikusan algoritmikus nondeterminizmus regressziokent kezelni.
* Benchmark/report futasban a timeout-bound allapotot explicit flaggel jelolni kell.

### 3.2 Sparrow feloldás + verzió pin

A Sparrow bináris feloldását a `scripts/ensure_sparrow.sh` végzi:

1. `SPARROW_BIN` env (ha futtatható)
2. `SPARROW_SRC_DIR` env (ha van benne `Cargo.toml`, build onnan)
3. `vendor/sparrow` (ha van `vendor/sparrow/Cargo.toml`, preferált vendor/submodule út)
4. fallback `.cache/sparrow` clone + pin + build

CI policy:

* CI-ben a hálózati fallback clone alapértelmezetten tiltott (`SPARROW_ALLOW_NETWORK_FALLBACK=0`).
* Ez vendor/submodule vagy explicit forrás/bináris használatot kényszerít (`vendor/sparrow`, `SPARROW_SRC_DIR`, `SPARROW_BIN`).
* Lokál futásnál a fallback clone továbbra is elérhető (ha nincs explicit tiltás).

Pin commit forrás:

* `SPARROW_COMMIT` env (elsődleges), különben
* `poc/sparrow_io/sparrow_commit.txt` (ha létezik és nem üres)

Ha a vendor/submodule repo nem tartalmazza a pinelt commitot, az `ensure_sparrow.sh` hibával áll meg és teendőt jelez (`git submodule update --init --recursive`).

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
* Új quality gate lépés (pl. pytest/mypy vagy más kötelező check) bevezetése → a standard gate (`scripts/check.sh`) és ez a dokumentáció együtt frissítendő.
* Python dependency változás esetén a `.in` + pinelt `.txt` fájlok és CI telepítési lépések együtt frissítendők.

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
