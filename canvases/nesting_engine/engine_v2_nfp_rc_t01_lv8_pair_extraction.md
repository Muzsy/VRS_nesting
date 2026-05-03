# Engine v2 NFP RC — T01 LV8 problémás part-pair extraction

## Cél
Kinyerni a valós LV8 solver inputból azokat az alkatrészpárokat, amelyek a jelenlegi
concave NFP algoritmust timeoutba vagy fragment explosion állapotba viszik.
Az extractált párok képezik T02–T10 fejlesztési lánc bemeneti fixture-jeit.

## Miért szükséges
A jelenlegi concave NFP implementáció valós ipari DXF méreteken, különösen az LV8
csomagban, fragment explosion problémába fut (példa: 342 × 518 = 177 156 rész-NFP).
Ahhoz, hogy az új reduced convolution kernel fejlesztése bizonyítékalapú legyen,
reprodukálható, explicit fixture-ök kellenek a problémás partpárokból.

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` — meglévő LV8 solver input
- `scripts/benchmark_cavity_v2_lv8.py` — LV8 benchmark minta (cavity_prepack_v2 flow)
- `scripts/export_real_dxf_nfp_pairs.py` — meglévő DXF NFP pár export script
- `worker/cavity_prepack.py` — build_cavity_prepacked_engine_input_v2 (hole-free output)
- `rust/nesting_engine/src/nfp/concave.rs` — ConcaveNfpOptions, concave NFP flow
- `rust/nesting_engine/src/nfp/cache.rs` — shape_id() hashing

### Létrehozandó:
- `scripts/experiments/extract_nfp_pair_fixtures_lv8.py` — extraction script
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` — 1. fixture (Lv8_11612 × Lv8_07921)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` — 2. fixture (Lv8_11612 × Lv8_07920)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` — 3. fixture (Lv8_07921 × Lv8_07920)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json` — fixture index metaadatokkal

## Nem célok / scope határok
- Nem kell NFP-t számítani — csak a geometriát kinyerni és menteni.
- Nem kell az existing NFP kódot módosítani.
- Nem kell a benchmark scripteket módosítani (csak olvasni).
- Nem kell új Rust kódot írni.
- Nem kell cavity_prepack_v2-t módosítani.
- A fixture-ok nem tartalmaznak holes-t a solver input szintjén (cavity_prepack_v2 utáni hole-free geometria).

## Részletes implementációs lépések

### 1. LV8 fixture olvasása
Olvasd el a `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` fájlt.
Értsd meg a part-record struktúrát: `part_id`, `points_mm`, `holes_points_mm`, `quantity`.
Azonosítsd az LV8 jellegű alkatrészeket (Lv8_xxxxx azonosítókkal vagy a fixture
méretéből következtethető darabok).

### 2. Cavity prepack v2 futtatása (ha van runner)
Ha a `benchmark_cavity_v2_lv8.py` script futtatható és a LV8 fixture elérhető:
```bash
python3 scripts/benchmark_cavity_v2_lv8.py --help
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('tests/fixtures/nesting_engine/ne2_input_lv8jav.json').read_text())
print('parts count:', len(data.get('parts', [])))
print('first part keys:', list(data.get('parts', [{}])[0].keys()))
"
```
Azonosítsd a top-level hole-free geometriákat.

### 3. Problémás párok kiválasztási kritériuma
Problémás pár jelölt, ha:
- A part-rekord `points_mm` outer ring vertex count > 150
- VAGY a cavity_prepack_v2 output tanúsítja, hogy ez a part komplex konkáv geometriájú
- VAGY az `export_real_dxf_nfp_pairs.py` script komplexnek jelöli

Prioritás: Lv8_11612 × Lv8_07921, Lv8_11612 × Lv8_07920, Lv8_07921 × Lv8_07920
(a tervfájl ezeket nevezi meg).

### 4. Fixture JSON formátum
Minden `lv8_pair_NN.json` tartalmazza:

```json
{
  "fixture_version": "nfp_pair_fixture_v1",
  "pair_id": "lv8_pair_01",
  "description": "LV8 problémás partpár: nagy konkáv alkatrészek",
  "source": "ne2_input_lv8jav.json",
  "part_a": {
    "part_id": "Lv8_11612",
    "geometry_level": "solver",
    "outer_ring_vertex_count": 342,
    "points_mm": [[x1, y1], [x2, y2], "..."],
    "holes_mm": []
  },
  "part_b": {
    "part_id": "Lv8_07921",
    "geometry_level": "solver",
    "outer_ring_vertex_count": 518,
    "points_mm": [[x1, y1], "..."],
    "holes_mm": []
  },
  "baseline_metrics": {
    "fragment_count_a": null,
    "fragment_count_b": null,
    "expected_pair_count": null,
    "current_nfp_timeout_reproduced": false,
    "notes": "baseline metrics T04-ben töltendő ki"
  }
}
```

### 5. Fixture index
`lv8_pair_index.json`:
```json
{
  "index_version": "v1",
  "fixtures": [
    {"pair_id": "lv8_pair_01", "file": "lv8_pair_01.json", "part_a": "Lv8_11612", "part_b": "Lv8_07921"},
    {"pair_id": "lv8_pair_02", "file": "lv8_pair_02.json", "part_a": "Lv8_11612", "part_b": "Lv8_07920"},
    {"pair_id": "lv8_pair_03", "file": "lv8_pair_03.json", "part_a": "Lv8_07921", "part_b": "Lv8_07920"}
  ],
  "created_from": "ne2_input_lv8jav.json",
  "geometry_level": "solver",
  "hole_status": "hole_free_after_cavity_prepack_v2"
}
```

### 6. Extraction script
`scripts/experiments/extract_nfp_pair_fixtures_lv8.py`:
- Olvassa a ne2_input_lv8jav.json-t
- Ha a fixture nem parse-olható vagy üres: **STOP — írj hibajelentést, ne hozz létre fixture-t**
- Keresi a tervfájlban megnevezett part ID-kat (Lv8_11612, Lv8_07921, Lv8_07920)
- Ha nem találja exact match alapján: a **legtöbb vertexű** partokból választja a top 3 párt (ez belső fallback — de csak valós geometrián alapulhat)
- Kimenti a fixture-öket
- Riportot ír stdout-ra: part ID, vertex count, hole count, FOUND/WARN jelzéssel

## Adatmodell / contract változások
Nincs production kód változás. Csak `scripts/experiments/` és `tests/fixtures/nesting_engine/nfp_pairs/` direktóriák jönnek létre.

## Backward compatibility
Nincs breaking change. Új könyvtárak és JSON fixture fájlok.

## Hibakódok / diagnosztikák
Az extraction script alábbi warning-okat adhat stdout-on:
- `WARN: part_id not found in fixture` — ha a névszerinti part nem azonosítható
- `WARN: no hole-free solver geometry — using exact geometry` — ha cavity_prepack_v2 nem fut
- `WARN: vertex_count below 100 — pair may not be problematic` — ha a kiválasztott pár nem bizonyítottan problémás

## Tesztelési terv
```bash
# 1. Extraction script szintaxis check
python3 -c "import ast; ast.parse(open('scripts/experiments/extract_nfp_pair_fixtures_lv8.py').read()); print('syntax OK')"

# 2. Fixture fájlok léteznek
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json

# 3. JSON validálás
python3 -c "
import json
from pathlib import Path
for f in Path('tests/fixtures/nesting_engine/nfp_pairs').glob('*.json'):
    data = json.loads(f.read_text())
    print(f.name, 'OK, keys:', list(data.keys()))
"

# 4. Fixture struktúra ellenőrzés
python3 -c "
import json
from pathlib import Path
pair = json.loads(Path('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json').read_text())
assert pair['fixture_version'] == 'nfp_pair_fixture_v1'
assert 'part_a' in pair
assert 'part_b' in pair
assert 'points_mm' in pair['part_a']
a_vc = len(pair['part_a']['points_mm'])
b_vc = len(pair['part_b']['points_mm'])
print(f'pair_01 vertex count: A={a_vc} B={b_vc} product={a_vc*b_vc}')
"
```

## Elfogadási feltételek
- [ ] `scripts/experiments/extract_nfp_pair_fixtures_lv8.py` létezik és szintaktikailag helyes
- [ ] `tests/fixtures/nesting_engine/nfp_pairs/` könyvtár létezik legalább 3 fixture fájllal
- [ ] Minden fixture JSON-ban van `fixture_version`, `part_a.points_mm`, `part_b.points_mm`
- [ ] Minden fixture `part_a.points_mm` és `part_b.points_mm` **nem üres** (legalább 3 pont)
- [ ] Az index fájl tartalmazza mind a 3 fixture referenciát
- [ ] Legalább egy fixture outer_ring_vertex_count > 50
- [ ] Nincs production kód változás
- [ ] **Tilos placeholder/synthetic geometria** — minden koordináta a `ne2_input_lv8jav.json` valódi adatából származik
- [ ] Ha a `ne2_input_lv8jav.json` nem elérhető vagy nem parse-olható: a task FAIL státusszal zárul, fixture nem jön létre

## Rollback / safety notes
Ez a task kizárólag új fájlokat hoz létre `scripts/experiments/` és
`tests/fixtures/nesting_engine/nfp_pairs/` útvonalakon. Nincs production kód változás,
nincs rollback kockázat. A fixture fájlok törölhetők következmény nélkül.

## Dependency
- Nincs — ez az első task. Önálló.
- T04 fogja kitölteni a `baseline_metrics` mezőket a fixture JSON-okban.
