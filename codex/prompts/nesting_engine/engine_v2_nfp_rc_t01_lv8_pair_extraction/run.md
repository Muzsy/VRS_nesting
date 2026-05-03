# Engine v2 NFP RC T01 — LV8 problémás part-pair extraction
TASK_SLUG: engine_v2_nfp_rc_t01_lv8_pair_extraction

## Szerep
Senior agent vagy. Adatextrakciós feladatot végzel: a valós LV8 solver input fixture-ből
kinyered a problémás part-párokat JSON fixture formátumba. Kizárólag új fájlokat hozol
létre. Nincs production kód módosítás.

## Cél
Hozd létre legalább 3 NFP pair fixture JSON-t `tests/fixtures/nesting_engine/nfp_pairs/`-ben
és az extraction scriptet `scripts/experiments/extract_nfp_pair_fixtures_lv8.py`-ban.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t01_lv8_pair_extraction.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t01_lv8_pair_extraction.yaml`
- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` (struktúra megértéséhez — csak olvasd)
- `scripts/export_real_dxf_nfp_pairs.py` (Python script minta)
- `scripts/benchmark_cavity_v2_lv8.py` (első 80 sor: LV8 benchmark minta)
- `rust/nesting_engine/src/nfp/concave.rs` (első 60 sor: ConcaveNfpOptions kontextus)

## Engedélyezett módosítás
Csak a YAML `allowed_files` listájában szereplő fájlok.

## Szigorú tiltások
- **Tilos bármely meglévő production fájlt módosítani** (.py, .rs, .ts, .tsx).
- Tilos NFP-t számítani.
- Tilos silent fallback — ha a part ID nem található, WARN legyen a logban.
- Tilos üres `points_mm` tömböt valid fixture-nek elfogadni.
- Tilos a fixture-t valódi geometria helyett placeholder koordinátákkal feltölteni
  (kivéve ha az LV8 fixture valóban nem tartalmazza a part-okat — akkor explicit megjegyzés).

## Végrehajtandó lépések

### Step 1: LV8 fixture struktúra megértése
```bash
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('tests/fixtures/nesting_engine/ne2_input_lv8jav.json').read_text())
print('top-level keys:', list(data.keys()))
parts = data.get('parts', [])
print('parts count:', len(parts))
if parts:
    print('first part keys:', list(parts[0].keys()))
    for p in parts:
        pid = p.get('part_id', '')
        pts = p.get('points_mm', [])
        holes = p.get('holes_points_mm', [])
        if 'Lv8_11612' in pid or 'Lv8_07921' in pid or 'Lv8_07920' in pid:
            print(f'  FOUND: {pid} outer_vertices={len(pts)} holes={len(holes)}')
"
```
Ha a fenti parancs nem találja a megnevezett part ID-kat, listázd a top 10 legtöbb
vertexű part-ot, és azokat válaszd fixturenek.

### Step 2: Top komplexitású partok listázása (ha named IDs nem találhatók)
```bash
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('tests/fixtures/nesting_engine/ne2_input_lv8jav.json').read_text())
parts = data.get('parts', [])
ranked = sorted(parts, key=lambda p: len(p.get('points_mm', [])), reverse=True)
print('Top 10 by vertex count:')
for p in ranked[:10]:
    print(f'  {p.get(\"part_id\")}: outer_vc={len(p.get(\"points_mm\",[]))} holes={len(p.get(\"holes_points_mm\",[]))}')
"
```

### Step 3: `scripts/experiments/` könyvtár és extraction script
Hozd létre a `scripts/experiments/extract_nfp_pair_fixtures_lv8.py` scriptet:
- `--input` parancssori arg (default: `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`)
- `--output-dir` parancssori arg (default: `tests/fixtures/nesting_engine/nfp_pairs`)
- Keresi: Lv8_11612, Lv8_07921, Lv8_07920 part ID-kat
- Ha nem talál exact match-et, a 6 legnagyobb vertex count-ú partból választja a top 3 párt
- WARN log ha bármely ID nem található
- Kimenti a fixture JSON-okat a canvas-ban megadott sémával
- Stdout riport: part ID, vertex count, pair product

### Step 4: `tests/fixtures/nesting_engine/nfp_pairs/` és fixture-ök
Futtasd az extraction scriptet:
```bash
python3 scripts/experiments/extract_nfp_pair_fixtures_lv8.py
```
Ha nem futtatható, írd meg a fixture-öket a ne2_input_lv8jav.json tényleges adataiból.

### Step 5: Validálás
```bash
# Szintaxis
python3 -c "import ast; ast.parse(open('scripts/experiments/extract_nfp_pair_fixtures_lv8.py').read()); print('syntax OK')"

# JSON validálás
python3 -c "
import json
from pathlib import Path
for f in sorted(Path('tests/fixtures/nesting_engine/nfp_pairs').glob('*.json')):
    d = json.loads(f.read_text())
    pa = d.get('part_a', {})
    pb = d.get('part_b', {})
    a_vc = len(pa.get('points_mm', []))
    b_vc = len(pb.get('points_mm', []))
    print(f'{f.name}: A_id={pa.get(\"part_id\")} A_vc={a_vc} B_id={pb.get(\"part_id\")} B_vc={b_vc} product={a_vc*b_vc}')
"

# Schema check
python3 -c "
import json,pathlib
p=json.loads(pathlib.Path('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json').read_text())
assert p['fixture_version']=='nfp_pair_fixture_v1', 'fixture_version hiba'
assert len(p['part_a']['points_mm']) > 0, 'part_a points_mm üres!'
assert len(p['part_b']['points_mm']) > 0, 'part_b points_mm üres!'
print('schema OK')
"
```

### Step 6: Checklist és report
Töltsd ki a checklistet és a reportot.
Magyar nyelvű report. Tartalmazza:
- Task meta (task_id, dátum)
- Olvasott fájlok listája
- ne2_input_lv8jav.json: part count, megtalált/nem megtalált part ID-k
- Fixture-ök listája: pair_id, part_a vertex count, part_b vertex count, product
- Létrehozott fájlok listája
- DoD→Evidence mátrix
- PASS/FAIL összegzés

## Stop conditions

**Ha a `ne2_input_lv8jav.json` nem létezik, üres, vagy nem parse-olható:**
→ **STOP. FAIL státusz.** Írj hibajelentést. Ne hozz létre fixture-t semilyen formában.
A fixture hiányában T02–T10 NEM INDÍTHATÓ. A problémát manuálisan kell megoldani.

**Elfogadott belső fallback (csak ha a fixture parse-olható és tartalmaz valódi geometriát):**
Ha a megnevezett part ID-k (Lv8_11612, Lv8_07921, Lv8_07920) nem találhatók:
1. Listázd a top 6 legkomplexebb partot (legtöbb vertex)
2. Hozz létre fixture-öket a top 3 párból
3. Jelöld explicit: `"WARN: named part IDs not found, using top-complexity fallback"`
4. Ez elfogadható, mert valódi LV8 geometrián alapul

**Tilos:**
- Placeholder/synthetic koordinátákat kreálni
- `"data_unavailable": true` fixture-öket létrehozni és azokra építeni
- Üres `points_mm` tömböt tartalmazó fixture-t valid-nak tekinteni

## Tesztparancsok
```bash
python3 -c "import ast; ast.parse(open('scripts/experiments/extract_nfp_pair_fixtures_lv8.py').read()); print('syntax OK')"
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json
python3 -c "import json,pathlib; p=json.loads(pathlib.Path('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json').read_text()); assert p['fixture_version']=='nfp_pair_fixture_v1'; print('schema OK')"
```

## Ellenőrzési pontok
- [ ] scripts/experiments/extract_nfp_pair_fixtures_lv8.py létezik és szintaxis OK
- [ ] tests/fixtures/nesting_engine/nfp_pairs/ könyvtár létezik
- [ ] lv8_pair_01.json, lv8_pair_02.json, lv8_pair_03.json mind léteznek
- [ ] lv8_pair_index.json létezik
- [ ] Minden fixture fixture_version=nfp_pair_fixture_v1
- [ ] Minden fixture part_a.points_mm és part_b.points_mm nem üres
- [ ] Nincs production kód módosítás
