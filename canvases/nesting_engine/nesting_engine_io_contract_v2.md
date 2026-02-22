# canvases/nesting_engine/nesting_engine_io_contract_v2.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_io_contract_v2.md`
> **TASK_SLUG:** `nesting_engine_io_contract_v2`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — IO Contract v2 dokumentáció + példa JSON-ok

## 🎯 Funkció

Az NFP nesting motor JSON IO contract-jának teljes dokumentálása és példa
input/output fájlok létrehozása. Ez az a szerződés, amit a Python runner
(`nesting_engine_runner.py`, F1-4 task) és a Rust motor között használunk.

A task deliverable-jei:
- `docs/nesting_engine/io_contract_v2.md` — minden mező, egység, invariáns dokumentálva
- `docs/nesting_engine/json_canonicalization.md` — determinism_hash normatív kanonikalizáció (meglévő, csak hivatkozunk rá)
- `poc/nesting_engine/sample_input_v2.json` — működőképes példa input (kézzel összerakott, valószerű geometriával)
- `poc/nesting_engine/sample_output_v2.json` — elvárt output struktúra ugyanehhez az inputhoz
- A meglévő v1 contract (`docs/solver_io_contract.md`) **nem módosul**

**Nem cél:**
- A Rust motor tényleges implementálása (az F1-4 task)
- Python runner megírása (az F1-4 task)
- A meglévő `docs/solver_io_contract.md` (v1) módosítása vagy törlése
- Backward kompatibilitás a v1-gyel (a v2 új crate-hez, új runner-hez szól)
- Valós DXF fájlok importálása (a poc JSON-ok kézzel összerakottak)

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Létrehozandó (új):**
- `docs/nesting_engine/io_contract_v2.md`
  - (A determinism_hash rész csak hivatkozik a `docs/nesting_engine/json_canonicalization.md`-re)
- `poc/nesting_engine/sample_input_v2.json`
- `poc/nesting_engine/sample_output_v2.json`
- `codex/codex_checklist/nesting_engine/nesting_engine_io_contract_v2.md`
- `codex/reports/nesting_engine/nesting_engine_io_contract_v2.md`

**Nem módosul:**
- `docs/solver_io_contract.md` (v1 — marad)
- `rust/nesting_engine/` (egyetlen fájl sem)
- `rust/vrs_solver/` (egyetlen fájl sem)
- `vrs_nesting/` (egyetlen fájl sem)
- `scripts/check.sh`, `scripts/verify.sh`

---

### Kontextus: mi változott az F1-1 task óta

Az F1-1 task során a `clipper2` crate helyett az `i_overlay` crate került bevezetésre
(pure Rust, nem C++ FFI). Ez az IO contract szempontjából **transzparens** — a JSON
határfelület nem függ a belső geometriai könyvtártól. A koordináták és a polygon
reprezentáció a contract-ban mm-alapú f64, a Rust belső SCALE konverzió (→ i64) a
motor belsejében történik, kívülről láthatatlan.

---

### Input contract v2 — teljes séma

```json
{
  "version": "nesting_engine_v2",
  "seed": 42,
  "time_limit_sec": 60,
  "sheet": {
    "width_mm": 1000.0,
    "height_mm": 2000.0,
    "kerf_mm": 0.2,
    "margin_mm": 5.0
  },
  "parts": [
    {
      "id": "part_001",
      "quantity": 10,
      "allowed_rotations_deg": [0, 90, 180, 270],
      "outer_points_mm": [[x, y], ...],
      "holes_points_mm": [
        [[x, y], ...]
      ]
    }
  ]
}
```

**Mezők részletezése:**

| Mező | Típus | Kötelező | Leírás |
|---|---|---|---|
| `version` | string | ✓ | Mindig `"nesting_engine_v2"` |
| `seed` | integer ≥ 0 | ✓ | Determinisztikus futáshoz |
| `time_limit_sec` | integer > 0 | ✓ | Solver time budget másodpercben |
| `sheet.width_mm` | f64 > 0 | ✓ | Tábla szélessége mm-ben |
| `sheet.height_mm` | f64 > 0 | ✓ | Tábla magassága mm-ben |
| `sheet.kerf_mm` | f64 ≥ 0 | ✓ | Vágási rés mm-ben (laser kerf) |
| `sheet.margin_mm` | f64 ≥ 0 | ✓ | Tábla szélétől tartandó minimum távolság |
| `parts[].id` | string | ✓ | Egyedi azonosító, snake_case ajánlott |
| `parts[].quantity` | integer > 0 | ✓ | Hány példány szükséges |
| `parts[].allowed_rotations_deg` | int[] | ✓ | Megengedett forgatások, pl. `[0, 90, 180, 270]` |
| `parts[].outer_points_mm` | [[f64,f64]] | ✓ | Külső kontúr pontjai mm-ben, CCW irány |
| `parts[].holes_points_mm` | [[[f64,f64]]] | — | Lyukak pontjai (belső kontúrok), CW irány; üres lista ha nincs |

**Invariánsok:**
- `outer_points_mm`: minimum 3 pont, zárt (utolsó pont nem egyezik az elsővel — a motor zárja)
- `holes_points_mm`: minden lyuk minimum 3 pont, zárt ugyanígy
- Koordináták: mm, f64, a tábla bal-alsó sarka (0, 0)
- Az inflált (kerf+margin) geometria a motor belsejében számítódik — az input mindig nominális

---

### Output contract v2 — teljes séma

```json
{
  "version": "nesting_engine_v2",
  "seed": 42,
  "solver_version": "0.1.0",
  "status": "ok",
  "sheets_used": 2,
  "placements": [
    {
      "part_id": "part_001",
      "instance": 0,
      "sheet": 0,
      "x_mm": 10.5,
      "y_mm": 20.3,
      "rotation_deg": 90
    }
  ],
  "unplaced": [
    {
      "part_id": "part_002",
      "instance": 3,
      "reason": "PART_NEVER_FITS_SHEET"
    }
  ],
  "objective": {
    "sheets_used": 2,
    "utilization_pct": 78.4
  },
  "meta": {
    "elapsed_sec": 12.3,
    "determinism_hash": "sha256:abc123..."
  }
}
```

**Mezők részletezése:**

| Mező | Típus | Leírás |
|---|---|---|
| `version` | string | Mindig `"nesting_engine_v2"` |
| `seed` | integer | Echo az inputból |
| `solver_version` | string | Rust crate verziója (Cargo.toml-ból) |
| `status` | string | `"ok"` (minden elhelyezve) vagy `"partial"` (van unplaced) |
| `sheets_used` | integer | Felhasznált táblák száma |
| `placements[].part_id` | string | Azonosító az inputból |
| `placements[].instance` | integer ≥ 0 | 0-alapú index (az adott part_id hanyadik példánya) |
| `placements[].sheet` | integer ≥ 0 | 0-alapú tábla index |
| `placements[].x_mm` | f64 | Elhelyezési X koordináta mm-ben (bounding box bal-alsó sarok) |
| `placements[].y_mm` | f64 | Elhelyezési Y koordináta mm-ben |
| `placements[].rotation_deg` | integer | Alkalmazott rotáció fokban (az `allowed_rotations_deg` egyike) |
| `unplaced[].part_id` | string | Az el nem helyezett part azonosítója |
| `unplaced[].instance` | integer | Példány index |
| `unplaced[].reason` | string | `PART_NEVER_FITS_SHEET` vagy `TIME_LIMIT_EXCEEDED` |
| `objective.sheets_used` | integer | Elsődleges optimalizálási cél értéke |
| `objective.utilization_pct` | f64 | Átlagos tábla-kihasználtság % (0–100) |
| `meta.elapsed_sec` | f64 | Tényleges futásidő másodpercben |
| `meta.determinism_hash` | string | SHA-256 hash a placements tömb kanonikus JSON reprezentációjából |

**`unplaced` reason kódok:**

| Kód | Jelentés |
|---|---|
| `PART_NEVER_FITS_SHEET` | A part inflated bounding box-a meghaladja a tábla hasznos területét — fizikailag nem fér el |
| `TIME_LIMIT_EXCEEDED` | A time_limit_sec lejárt mielőtt minden part elhelyezhető lett volna |

**`determinism_hash` számítása:**
**Normatív definíció:** a `meta.determinism_hash` értékét **kötelezően** a
`docs/nesting_engine/json_canonicalization.md` szerint kell előállítani
(RFC 8785 / JCS + hash-view + placements stabil rendezés + SHA-256).

Tilos a nyers output JSON (pretty-print / tetszőleges serializáció) közvetlen hash-elése.

---

### Geometria egyezmények (kőbe vésett szabályok)

```
1. Koordináta-rendszer: origó (0,0) = tábla bal-alsó sarka, X jobbra, Y felfelé
2. Kontúr irány: outer = CCW (Counter-Clockwise), hole = CW (Clockwise)
3. Egység: kizárólag mm (f64) a JSON határfelületen
4. Nominális vs. inflated: az INPUT mindig nominális geometriát tartalmaz.
   A motor BELSŐ kerf+margin inflate-et végez, a JSON output koordinátái
   szintén nominálisak (a placement transzformáció a nominális origóra vonatkozik).
5. Elhelyezési transzformáció: a part (x_mm, y_mm)-el eltolódik, majd
   rotation_deg szöggel fordul a saját origója körül (bounding box bal-alsó sarok).
```

---

### Poc JSON fájlok tartalma

#### `poc/nesting_engine/sample_input_v2.json`

Tartalmaz:
- 1 db tábla: 500×1000mm, kerf=0.2mm, margin=5mm
- 3 féle part:
  - `rect_100x50`: egyszerű téglalap lyuk nélkül, 5 példány, [0, 90, 180, 270]
  - `l_shape`: L-alakú konkáv polygon lyuk nélkül, 3 példány, [0, 90, 180, 270]
  - `ring`: téglalap 1 lyukkal (furat), 2 példány, [0, 180]
- seed: 42, time_limit_sec: 30

A koordináták kézzel összerakottak, valószerű gyártási méretekkel (mm).

#### `poc/nesting_engine/sample_output_v2.json`

Tartalmaz:
- status: "partial" (nem minden fér el 1 táblán — szándékos, hogy a multi-sheet logika is tesztelhető legyen)
- 8 placement (a 10-ből ami elfér)
- 2 unplaced (TIME_LIMIT_EXCEEDED reason)
- objective, meta mezők kitöltve
- determinism_hash: placeholder string (a tényleges implementáció tölti majd ki)

**Fontos:** a poc output JSON értékei illusztrációk — nem a tényleges solver output.
A motor implementálása előtt ez a fájl nem validálható gépileg. Célja a struktúra
rögzítése és a fejlesztői referencia.

---

### Kapcsolat a v1 contract-tal

| Aspektus | v1 (`solver_io_contract.md`) | v2 (`io_contract_v2.md`) |
|---|---|---|
| Crate | `vrs_solver` | `nesting_engine` |
| Runner | `vrs_solver_runner.py` | `nesting_engine_runner.py` (F1-4) |
| Part geometria | `outer_points` + `holes_points` (opcionális) | `outer_points_mm` + `holes_points_mm` (kötelező) |
| Egység jelölés | implicit (mm feltételezett) | explicit `_mm` suffix |
| Objective | nincs | `objective.sheets_used`, `objective.utilization_pct` |
| Determinism hash | nincs | `meta.determinism_hash` |
| Kompatibilitás | marad, nem változik | új, független contract |

---

### Kockázat + mitigáció + rollback

| Kockázat | Mitigáció | Rollback |
|---|---|---|
| A poc JSON-ok eltérnek a tényleges motor kimenetétől (F1-4) | A poc output explicitly "illusztráció" státuszú — F1-4 task feladata a valódi output validálása | poc fájlok frissítése F1-4-ben |
| Mező-eltérés a Python runner és a Rust motor között | Az io_contract_v2.md az egyetlen source of truth — mindkét oldal ebből implementál | Contract frissítés + mindkét oldal update |
| v1 contract véletlenül módosul | A v1 fájl nem szerepel egyetlen step outputs listájában sem | git revert |

---

## ✅ Pipálható DoD lista

### Felderítés
- [ ] `AGENTS.md` elolvasva
- [ ] `docs/codex/overview.md` elolvasva
- [ ] `docs/codex/yaml_schema.md` elolvasva
- [ ] `docs/codex/report_standard.md` elolvasva
- [ ] `docs/solver_io_contract.md` (v1) megvizsgálva — struktúra megértve, nem módosítjuk
- [ ] `rust/nesting_engine/src/geometry/types.rs` megvizsgálva — `PartGeometry`, `Polygon64` ismert
- [ ] `docs/nesting_engine/tolerance_policy.md` megvizsgálva — koordináta konvenciók ismertek
- [ ] `docs/nesting_engine/json_canonicalization.md` megvizsgálva — determinism_hash normatív szabályai ismertek

### Implementáció
- [ ] `docs/nesting_engine/io_contract_v2.md` létrehozva, minden mező dokumentálva
- [ ] `poc/nesting_engine/sample_input_v2.json` létrehozva, valid JSON, 3 part type
- [ ] `poc/nesting_engine/sample_output_v2.json` létrehozva, valid JSON, illusztrációs értékekkel
- [ ] Geometria egyezmények (CCW/CW, mm, nominális, transzformáció) dokumentálva
- [ ] `unplaced` reason kódok definiálva és dokumentálva
- [ ] `determinism_hash` számítási módja dokumentálva **és hivatkozás** a `docs/nesting_engine/json_canonicalization.md` normatív doksira szerepel
- [ ] v1 ↔ v2 összehasonlító táblázat az io_contract_v2.md-ben

### Ellenőrzés
- [ ] `poc/nesting_engine/sample_input_v2.json` valid JSON (`python3 -m json.tool` PASS)
- [ ] `poc/nesting_engine/sample_output_v2.json` valid JSON (`python3 -m json.tool` PASS)
- [ ] `docs/solver_io_contract.md` (v1) változatlan (`git diff` üres erre a fájlra)

### Gate
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md` PASS

---

## 🧪 Tesztállapot

**Kötelező gate:**
```
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md
```

**Task-specifikus ellenőrzések:**
```bash
python3 -m json.tool poc/nesting_engine/sample_input_v2.json   > /dev/null
python3 -m json.tool poc/nesting_engine/sample_output_v2.json  > /dev/null
git diff docs/solver_io_contract.md   # üres kell legyen
```

**Elfogadási kritérium:**
- Minden mező az `io_contract_v2.md`-ben dokumentált (típus, kötelező/opcionális, egység)
- A poc JSON-ok valid JSON-ok, a contract sémájával összhangban vannak
- A v1 contract fájl byte-azonos marad

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

**Szülő dokumentum:**
- `canvases/nesting_engine/nesting_engine_backlog.md` — F1-2 task

**Előző task (F1-1) outputjai — elolvasandó implementáció előtt:**
- `rust/nesting_engine/src/geometry/types.rs` — `Point64`, `Polygon64`, `PartGeometry`
- `rust/nesting_engine/src/geometry/scale.rs` — SCALE, koordináta konvenciók
- `docs/nesting_engine/tolerance_policy.md` — CCW/CW, mm, touching policy

**Meglévő v1 contract (referencia, nem módosítandó):**
- `docs/solver_io_contract.md`

**Következő task (F1-3):**
- `canvases/nesting_engine/nesting_engine_polygon_pipeline.md`

**Codex workflow:**
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
