# canvases/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md
# P1-3: Sparrow dependency kockázat csökkentése (vendor/submodule + fallback)

## 🎯 Funkció

A cél, hogy a Sparrow beszerzése/futtatása ne csak a CI/lokál “git clone GitHub-ról” úton múljon.

Legyen egy stabil, preferált út:
- **vendor/submodule** (`vendor/sparrow/`) használata, ha elérhető (offline-barát),
és legyen **fallback**:
- jelenlegi cache-es klónozás (`.cache/sparrow`) pinelt commit-ra (ha nincs vendor).

Követelmény: a meglévő gate viselkedés nem sérülhet; ha nincs vendor, továbbra is működjön a repo a mostani módon.

## 🧠 Fejlesztési részletek

### Jelenlegi állapot (probléma)

- `scripts/check.sh` Sparrow-t alapból `.cache/sparrow` alá klónozza és buildeli (`git clone https://github.com/JeroenGar/sparrow.git ...`), opcionálisan pin: `poc/sparrow_io/sparrow_commit.txt`.
- `.github/workflows/sparrow-smoketest.yml` szintén klónoz + checkout pin + build.
- Külső függés kockázat: ha a remote elérhetetlen / rate limit / átmeneti outage, a gate elhasal.

### Megoldás – központosított Sparrow “resolver” script

Hozzunk létre egy új, egyetlen belépési pontot:

- Új: `scripts/ensure_sparrow.sh`
  - **stdout**: kizárólag a feloldott, futtatható `SPARROW_BIN` abszolút útvonala (hogy könnyen `$(...)`-be fogható legyen)
  - **stderr**: logok/debug (stdout tisztán marad)
  - Prioritás:
    1) ha `SPARROW_BIN` env meg van adva és futtatható → azt adja vissza
    2) ha `SPARROW_SRC_DIR` env meg van adva és ott van `Cargo.toml` → build ott → bin vissza
    3) ha `vendor/sparrow/Cargo.toml` létezik → build ott → bin vissza
    4) fallback: `.cache/sparrow` (ha nincs, clone) → pin (commit file alapján) → build → bin vissza
  - Pin forrása:
    - `SPARROW_COMMIT` env (ha meg van adva) különben
    - `poc/sparrow_io/sparrow_commit.txt` (ha létezik és nem üres)
  - Ha vendor/submodule git repo és a pin commit nem érhető el benne: legyen **érthető hiba** + teendő (submodule update / checkout).

### Integráció

- `scripts/check.sh`:
  - a jelenlegi Sparrow clone/pin/build blokk helyett használja az `ensure_sparrow.sh`-t, és abból állítsa be a `SPARROW_BIN`-t (ha nincs explicit `SPARROW_BIN`).
  - A gate lépések sorrendje maradjon, a végén ugyanúgy fusson a smoketest suite.

- `.github/workflows/sparrow-smoketest.yml`:
  - a “Prepare Sparrow source” + “Build Sparrow” lépéseket váltsa ki az `./scripts/ensure_sparrow.sh` használata
  - a `SPARROW_BIN` beállítása menjen `$GITHUB_ENV`-be: `echo "SPARROW_BIN=$(./scripts/ensure_sparrow.sh)" >> $GITHUB_ENV`
  - `actions/checkout@v4` kapjon `submodules: recursive` opciót (akkor is oké, ha jelenleg nincs submodule)

- `.github/workflows/repo-gate.yml`:
  - `actions/checkout@v4` kapjon `submodules: recursive` opciót (jövőbiztos vendor/submodule támogatás).

### Dokumentáció

- `docs/qa/testing_guidelines.md`:
  - frissítsd a “Sparrow pin + build” részt: említsd az új `ensure_sparrow.sh` logikát, és a vendor/submodule preferált utat.
  - írd le az env opciókat: `SPARROW_BIN`, `SPARROW_SRC_DIR`, `SPARROW_COMMIT`.

- `AGENTS.md`:
  - a “Git szükséges (Sparrow klónozás…)” részt pontosítsd: git a fallback klónozáshoz kell; vendor/submodule mellett a gate offline-barátabb.

- (Opcionális, de hasznos) `vendor/README.md`:
  - röviden: hogyan adják hozzá submodule-ként a Sparrow-t `vendor/sparrow` alá, és hogyan illeszkedik a pinhez.

### DoD

- [ ] Létrejön `scripts/ensure_sparrow.sh` a fenti prioritási szabályokkal (stdout csak bin path).
- [ ] `scripts/check.sh` Sparrow feloldása az `ensure_sparrow.sh`-n keresztül történik (explicit `SPARROW_BIN` továbbra is felülír).
- [ ] `sparrow-smoketest.yml` az `ensure_sparrow.sh`-t használja, és `submodules: recursive` be van állítva.
- [ ] `repo-gate.yml` checkout `submodules: recursive`.
- [ ] `docs/qa/testing_guidelines.md` és `AGENTS.md` frissítve az új Sparrow-dependency logikára.
- [ ] Repo gate PASS:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`

### Kockázat + mitigáció + rollback

- Kockázat: az `ensure_sparrow.sh` véletlenül stdout-ra logol → eltöri a `$(...)` feloldást.
  - Mitigáció: minden log stderr-re; stdout kizárólag a bin path.
- Kockázat: vendor/submodule állapot “félkész” → félrevezető fallback.
  - Mitigáció: vendor csak akkor aktív, ha van `Cargo.toml`; különben fallback cache/clone.
- Rollback: `scripts/check.sh` visszaállítása a jelenlegi clone/pin/build blokkra; workflow lépések vissza.

## 🧪 Tesztállapot

- Kötelező:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`
- Opcionális (lokál sanity):
  - `./scripts/ensure_sparrow.sh` (csak egy abszolút bin path-ot adjon vissza)

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `scripts/check.sh`
- `scripts/ensure_sparrow.sh` (új)
- `.github/workflows/repo-gate.yml`
- `.github/workflows/sparrow-smoketest.yml`
- `poc/sparrow_io/sparrow_commit.txt`
- `docs/qa/testing_guidelines.md`
- `AGENTS.md`
