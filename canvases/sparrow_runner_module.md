# Sparrow runner modul (Python) + smoketest integráció

## 🎯 Funkció

**Cél:** a Sparrow futtatását kiszervezni egy determinisztikus, artefakt-orientált Python „runner” modulba, ami minden futást egy egyedi `runs/<run_id>/` könyvtárba ment (input snapshot + stdout/stderr + outputok + meta). A meglévő repo gate (check.sh → smoketest + validator) ettől még ugyanúgy zöld kell maradjon.

**Miért kell:** a jelenlegi „root/output/” output konvenció könnyen ütközik (régi fájl validálása, párhuzamos futás, CI artefakt mentés). A runnerrel minden futás izolált és auditálható.

## 🧠 Fejlesztési részletek

### Scope

**Benne van**

* `vrs_nesting/runner/sparrow_runner.py` modul:
  * `SPARROW_BIN` feloldás (env / explicit / PATH)
  * input `instance.json` snapshot mentés `runs/<run_id>/instance.json`
  * Sparrow futtatás `cwd=run_dir`-rel, stdout/stderr fájlba
  * output felderítés `run_dir/output/final_*.json` alapján
  * meta mentés: `runs/<run_id>/runner_meta.json` (cmd, seed, time_limit, sha256, strip_width, density, placed_count, log pathok)
  * CLI: `python3 -m vrs_nesting.runner.sparrow_runner --input <path> ...` → **stdout-on csak a run_dir** (shell integrációhoz)

* `scripts/run_sparrow_smoketest.sh` frissítése:
  * Sparrow futtatást a runneren keresztül végezze
  * a validator bemenetének a snapshotot használja
  * overlap-check logika változatlan (CI-ben shapely kötelező)

* `.github/workflows/sparrow-smoketest.yml` frissítése:
  * failure artefaktok: `runs/**`

* `.gitignore` frissítése:
  * `runs/` ignore

**Nincs benne (explicit nem-cél)**

* IO contract/validator szabályok módosítása
* multi-sheet wrapper vagy DXF export
* Sparrow build/pin logika átalakítása (ez marad `scripts/check.sh` + CI workflow)
* új POC bemenet hozzáadása

### Érintett fájlok

* Új:
  * `vrs_nesting/__init__.py`
  * `vrs_nesting/runner/__init__.py`
  * `vrs_nesting/runner/sparrow_runner.py`
* Módosul:
  * `scripts/run_sparrow_smoketest.sh`
  * `.github/workflows/sparrow-smoketest.yml`
  * `.gitignore`

### DoD (Definition of Done)

* [ ] A runner modul létrejött a fenti scope szerint, és `python3 -m vrs_nesting.runner.sparrow_runner --help` működik.
* [ ] Minden Sparrow futás artefaktja a `runs/<run_id>/` alatt keletkezik (snapshot + log + output + `runner_meta.json`).
* [ ] A `scripts/run_sparrow_smoketest.sh` már a runneren keresztül futtat, és a validátort a snapshot+final_json párossal hívja.
* [ ] CI failure esetén a `runs/**` felkerül az artefaktba.
* [ ] `./scripts/verify.sh --report codex/reports/sparrow_runner_module.md` lefut és **PASS**.

### Kockázatok + rollback

* **Kockázat:** a runner CLI extra stdout-ot ír → a shell script nem tudja elkapni a run_dir-t.
  * **Mitigáció:** a runner CLI stdout-ja kizárólag a run_dir legyen; minden más stderr.
* **Kockázat:** Sparrow output név eltér (nem `final_<name>.json`).
  * **Mitigáció:** fallback a legfrissebb `output/final_*.json`.
* **Rollback:**
  * állítsd vissza `scripts/run_sparrow_smoketest.sh`-t a korábbi közvetlen Sparrow futtatásra,
  * CI artefakt path vissza `output/final_*`-ra,
  * a runner fájlok maradhatnak (nem zavarnak), vagy törölhetők.

## 🧪 Tesztállapot

**Kötelező:**

* `./scripts/verify.sh --report codex/reports/sparrow_runner_module.md`

**Opcionális (gyors sanity):**

* `python3 -c 'from vrs_nesting.runner.sparrow_runner import resolve_sparrow_bin; print(resolve_sparrow_bin())'` (ha van Sparrow a PATH-on)

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

* `AGENTS.md`
* `scripts/check.sh`
* `scripts/run_sparrow_smoketest.sh`
* `scripts/validate_sparrow_io.py`
* `docs/sparrow_modul/sparrow_runner_modul_komplett_dokumentacio.md`
* `docs/qa/testing_guidelines.md`
