# Canvas: MVP Demo Készlet és Dokumentáció Véglegesítése

**Task Slug:** `mvp_finalize_demo_and_docs`
**Státusz:** Draft
**Prioritás:** P0 (MVP Blokkoló)

## 1. Context & Goal
A rendszer architekturálisan készen áll (CLI, Sparrow runner, DXF import/export), de hiányzik egy **reprodukálható demo csomag** és egy **"Hogyan futtasd" leírás**, ami bizonyítja, hogy a rendszer képes feldolgozni a valós (íves, egyszerű, hibás) DXF fájlokat.
Jelenleg a `samples/dxf_demo` mappa tartalma létezik, de nincs validálva, hogy ez a hivatalos demo set, és nincs hozzá publikus futtatási útmutató.

**Cél:**
1. A `samples/dxf_demo/` tartalmának véglegesítése (legyen benne: egyszerű, íves, és egy szándékoltan hibás fájl).
2. A `docs/how_to_run.md` létrehozása, amely lépésről lépésre végigvezet a telepítésen és a demo futtatásán.
3. Annak biztosítása, hogy a CI/Smoke tesztek (`scripts/check.sh`) ezt a demo készletet használják referenciaként.

## 2. Definition of Done (DoD)
- [ ] **Demo Set:** A `samples/dxf_demo/` mappában dokumentáltan jelen vannak a kulcs fájlok:
    - `stock_rect_1000x2000.dxf` (Alapanyag)
    - `part_arc_spline_chaining_ok.dxf` (Íves, helyes alkatrész)
    - `part_chain_open_fail.dxf` (Hibás/nyitott alkatrész - error handling teszthez)
- [ ] **Documentation:** Elkészült a `docs/how_to_run.md`:
    - Előfeltételek (Python, Rust/Sparrow)
    - Telepítés (`pip-sync`)
    - Demo parancs (`python -m vrs_nesting ...`)
    - Várt kimenet leírása.
- [ ] **Verification:** A `scripts/verify.sh` sikeresen lefut, és a report megerősíti a demo fájlok helyességét.

## 3. Plan
1. **Felderítés:** Ellenőrizni a jelenlegi `samples/dxf_demo` tartalmát.
2. **Dokumentálás (README):** Frissíteni a `samples/dxf_demo/README.md`-t, rögzítve az elvárt fájlokat.
3. **User Guide:** Megírni a `docs/how_to_run.md`-t a `docs/codex/overview.md` és a meglévő CLI help alapján.
4. **Gate:** Futtatni a verify szkriptet.

## 4. Risks & Mitigation
- **Rust/Sparrow hiány:** A felhasználónak nincs Rust toolchain-je.
  - *Mitigation:* A doksi emelje ki a `scripts/ensure_sparrow.sh` használatát vagy a bináris letöltést.
- **DXF verzió inkompatibilitás:** Régi R12 vs 2013 DXF.
  - *Mitigation:* A demo fájlok legyenek szabványos ASCII DXF-ek (ezdxf kezeli).