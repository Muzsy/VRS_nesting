# Samples + schema rendbetetel: project_rect_1000x2000.json CLI-futtathato

## 🎯 Funkcio
A `samples/project_rect_1000x2000.json` legyen **strict schema-kompatibilis** es tenylegesen futtathato a CLI-vel:
- legalabb addig, hogy a CLI be tudja olvasni/validalni a projectet (es a run flow elejen ne haljon el ismeretlen mezok miatt).

Cel:
- `python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json` ne bukjon el a **project schema** validacion.

## 🧠 Fejlesztesi reszletek

### Mi a problema (konkretan)
A project schema strict (ismeretlen top-level mezok tiltasaval), ezert a sample-ben levo “extra” mezok (pl. pelda output / debug mezok) a CLI project-parse lepest el tudjak rontani.

A feladat NEM a schema fellazitasa. A feladat:
- a sample tegye azt, amit a schema elvar,
- az extra peldaadat menjen kulon fajlba vagy docs-ba.

### Felderitesi eredmeny (valos repo allapot)
- Schema oldal: `vrs_nesting/project/model.py` strict top-level kulcslistat var:
  - kotelezo: `version`, `name`, `seed`, `time_limit_s`, `stocks`, `parts`
  - ismeretlen kulcsokra: `E_SCHEMA_UNKNOWN` (`_validate_keys(...)`).
- Korabbi mintaelteres oka: a `samples/project_rect_1000x2000.json` korabban tartalmazott
  extra top-level kulcsot (`solver_output_example`), ami strict parse hibahoz vezetett.
- Jelenlegi allapot: a futtathato sample mar strict-kompatibilis; a feladatban az extra peldaadat
  kulon fajlba mentese es dokumentalt ellenorzese marad.

### Elvart iranyelvek
- A `vrs_nesting/project/model.py` altal elvart project formatum legyen a minta, ne “best-effort” parse.
- A `samples/project_rect_1000x2000.json` maradjon a *futtathato* demo minta.
- Ha van “pelda output” / “expected output” / “solver output example”, azt:
  - vagy kulon mintafajlba kell mozgatni (pl. `samples/project_rect_1000x2000_with_examples.json`),
  - vagy a `docs/` ala kell tenni (pl. `docs/examples/`), de a futtathato sample-t nem szabad szetszennyezni.

### Konkrét teendok
1) Nezd meg, pontosan miert nem strict-kompatibilis a sample:
   - mely top-level kulcsok ismeretlenek,
   - van-e hianyzo kotelezo kulcs,
   - van-e tipus/szerkezet elteres.
2) Javitsd a `samples/project_rect_1000x2000.json`-t:
   - csak a schema altal elfogadott mezok legyenek benne,
   - minimal, de realis demo (1 tabla/stock + 1-2 alkatrész).
3) Ha voltak extra debug/pelda adatok:
   - hozd letre a megfelelo uj fajlt, es tedd at oda az extra reszt (ne vesszen el).
4) Validald, hogy a CLI mar elfogadja a projectet (task-specifikus smoke).

### Erintett fajlok
- `samples/project_rect_1000x2000.json`
- (ha kell) uj fajl: `samples/project_rect_1000x2000_with_examples.json` (csak ha van mit atmenteni)
- (opcionalis, ha a schema/README kifejezetten hivatkozik a sample-re) `docs/mvp_project_schema.md`
- `codex/codex_checklist/egyedi_solver/samples_project_rect_1000x2000_schema_fix.md`
- `codex/reports/egyedi_solver/samples_project_rect_1000x2000_schema_fix.md`

### DoD
- [ ] A `samples/project_rect_1000x2000.json` strict schema-valid (ismeretlen top-level mez nelkul).
- [ ] `python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json` nem bukik el a project-parse/validalas lepesen.
- [ ] Ha volt extra peldaadat, az nem veszett el: kulon fajlba atkerult.
- [ ] Verify gate PASS.

## 🧪 Tesztallapot
- Kotelezo:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/samples_project_rect_1000x2000_schema_fix.md`
- Manualis smoke (min):
  - `python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json`
  - ellenorizd, hogy nincs project schema error.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `vrs_nesting/project/model.py`
- `docs/mvp_project_schema.md`
- `samples/project_rect_1000x2000.json`
- `scripts/check.sh`
- `scripts/verify.sh`
