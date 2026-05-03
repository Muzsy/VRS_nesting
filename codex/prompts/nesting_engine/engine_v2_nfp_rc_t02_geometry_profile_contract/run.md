# Engine v2 NFP RC T02 — Geometry Profile Contract
TASK_SLUG: engine_v2_nfp_rc_t02_geometry_profile_contract

## Szerep
Senior dokumentációs agent vagy. Read-only vizsgálatot végzel a meglévő geometry
infrastruktúrán, majd definiálod és dokumentálod az exact / canonical / solver geometry
háromszintű contractot. Nincs kód módosítás.

## Cél
Hozd létre `docs/nesting_engine/geometry_preparation_contract_v1.md`-t, amely
T03–T10 minden geometriai döntés referenciaalapja.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t02_geometry_profile_contract.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t02_geometry_profile_contract.yaml`
- `rust/nesting_engine/src/geometry/types.rs` (teljes fájl)
- `rust/nesting_engine/src/geometry/scale.rs` (SCALE konstans értéke)
- `rust/nesting_engine/src/geometry/float_policy.rs` (GEOM_EPS_MM értéke)
- `rust/nesting_engine/src/geometry/pipeline.rs` (run_inflate_pipeline flow)
- `rust/nesting_engine/src/nfp/mod.rs` (NfpError enum)
- `rust/nesting_engine/src/nfp/boundary_clean.rs` (clean_polygon_boundary, ring_has_self_intersection)

## Engedélyezett módosítás
Csak a YAML `allowed_files` listájában szereplő fájlok.

## Szigorú tiltások
- **Tilos bármely .rs, .py, .ts, .tsx fájlt módosítani.**
- Tilos nem létező API-t dokumentálni.
- Tilos kommentből következtetni — csak valós kódot dokumentálni.
- Tilos v2 feature-t bevezető kódot írni.

## Végrehajtandó lépések

### Step 1: Geometry kód olvasása
```bash
# SCALE konstans értéke
grep -n "SCALE\|pub const" rust/nesting_engine/src/geometry/scale.rs

# GEOM_EPS_MM értéke
grep -n "GEOM_EPS_MM\|pub const" rust/nesting_engine/src/geometry/float_policy.rs

# Point64, Polygon64 definíció
grep -n "pub struct Point64\|pub struct Polygon64\|pub struct PartGeometry" rust/nesting_engine/src/geometry/types.rs

# NfpError enum tagok
grep -n "pub enum NfpError\|EmptyPolygon\|NotConvex\|Orbit\|Decomposition" rust/nesting_engine/src/nfp/mod.rs

# boundary_clean publikus API
grep -n "^pub fn" rust/nesting_engine/src/nfp/boundary_clean.rs
```

### Step 2: docs/nesting_engine/ könyvtár ellenőrzése
```bash
ls docs/nesting_engine/ 2>/dev/null || mkdir -p docs/nesting_engine && echo "könyvtár létrehozva"
```

### Step 3: Contract dokumentum megírása

Hozd létre `docs/nesting_engine/geometry_preparation_contract_v1.md`-t.
Kötelező 7 szekció (a canvas spec alapján részletesen):

1. **Exact geometry** — eredeti gyártási kontúr, nem módosítható destruktívan
2. **Canonical clean geometry** — topológiailag ekvivalens, degenerate-ektől tisztítva
3. **Solver/NFP geometry** — topology-preserving simplification (NEM gyártási igazság)
4. **Integer robust layer** — Point64 típus, SCALE konstans, snap tolerance, overflow check
5. **GEOM_EPS_MM toleranciák** — pontos értéke, mikor érvényes/nem érvényes
6. **Simplification safety szabályok** — reflex vertex, narrow neck, hole, key-lock megőrzés
7. **Final validation elve** — minden placement exact geometry alapján validálandó

Rögzítsd a tényleges értékeket (SCALE, GEOM_EPS_MM) a kódból.
Ha nem olvasható: explicit `(TBD: konstans nem található a kódban)` jelölés.

### Step 4: Validálás
```bash
# Dokumentum létezik
ls docs/nesting_engine/geometry_preparation_contract_v1.md

# Kötelező szekciók és kulcsszavak
python3 -c "
content = open('docs/nesting_engine/geometry_preparation_contract_v1.md').read()
required = ['Exact geometry', 'Canonical clean', 'Solver', 'Integer robust',
            'GEOM_EPS_MM', 'Simplification safety', 'Final validation',
            'Point64', 'solver geometry', 'gyártási']
missing = [r for r in required if r not in content]
if missing:
    print('HIÁNYZÓ SZEKCIÓK:', missing)
else:
    print('Minden kulcsszó megtalálható')
"

# Nincs production kód módosítás
git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'
```

### Step 5: Report és checklist
Töltsd ki a checklistet és a reportot.
Tartalmazza: olvasott fájlok, SCALE és GEOM_EPS_MM tényleges értékei, DoD→Evidence mátrix.

## Tesztparancsok
```bash
ls docs/nesting_engine/geometry_preparation_contract_v1.md
python3 -c "content=open('docs/nesting_engine/geometry_preparation_contract_v1.md').read(); assert 'solver geometry' in content; assert 'Point64' in content; print('keywords OK')"
git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'
```

## Ellenőrzési pontok
- [ ] docs/nesting_engine/geometry_preparation_contract_v1.md létezik
- [ ] Mind a 7 szekció megvan
- [ ] Explicit: solver geometry ≠ gyártási geometria
- [ ] Explicit: Point64 az integer robust layer implementációja
- [ ] GEOM_EPS_MM értéke szerepel (vagy explicit TBD)
- [ ] SCALE értéke szerepel (vagy explicit TBD)
- [ ] Nincs production kód módosítás
