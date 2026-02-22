# Nesting Engine — Tolerance & Scale Policy

**Scope:** `rust/nesting_engine/` crate
**Source of truth:** `src/geometry/scale.rs` + `src/geometry/offset.rs`

---

## 1. Scale Policy

### 1.1 SCALE konstans

```
SCALE = 1_000_000i64   (1 mm = 1_000_000 units)
```

Minden koordináta `i64` típusú egész számként tárolódik:

| Dimenzió | Érték |
|---|---|
| 1 unit | 1 µm (mikrométter) |
| 1 mm | 1 000 000 unit |
| Maximálisan kezelhető méret | ±9 223 372 mm ≈ ±9 223 km (i64 max / SCALE) |
| Tipikus táblaméret | ≤ 4 000 mm → ~bőven belül esik |

**Miért `i64`?**
Az egész aritmetika determinisztikus és hordozható: ugyanazon bemenetre mindig ugyanazt az eredményt adja, platform- és fordítóverziótól függetlenül. A floating-point kerekítés okozta nemdeterminizmus kizárt.

**Miért 1 000 000?**
1 µm pontosság elegendő CNC-alapú lemezmegmunkáláshoz (ahol a gyártási tolerancia jellemzően 50–200 µm). A 6 tizedesjegy elegendő tér a Clipper/offset számításokhoz, és az `i64` tartományát nem meríti ki.

### 1.2 Konverzió

```rust
pub const SCALE: i64 = 1_000_000;

/// mm (f64) → skálázott i64
pub fn mm_to_i64(mm: f64) -> i64 {
    (mm * SCALE as f64).round() as i64
}

/// skálázott i64 → mm (f64)
pub fn i64_to_mm(scaled: i64) -> f64 {
    scaled as f64 / SCALE as f64
}
```

A konverzió **veszteséges** (kerekítés), de **determinisztikus** és **reprodukálható**:

```
round_trip_error = |i64_to_mm(mm_to_i64(x)) - x| < 1e-6  (garantált)
```

---

## 2. Touching Policy

### 2.1 TOUCH_TOL konstans

```
TOUCH_TOL = 1i64   (= 1 µm)
```

Két polygon **érintkezőnek** (touching) minősül, ha bármely pontjaik közötti távolság ≤ TOUCH_TOL unit = 1 µm.

### 2.2 Touching = infeasible (konzervatív)

Az érintkezés **nem engedélyezett elhelyezés**: az alkatrészek közt legalább 1 µm résnek kell maradnia. Ez a **konzervatív oldal** — gyártási biztonság:

- Lezervárásnál az érintkező kontúrok összeolvadhatnak
- Vágásnál a kerf-szélesség miatt az érintkezés anyaghiányt okoz
- A tolerancia az offset (inflate) lépéssel érvényesítendő: minden alkatrész kontúrját `inflate_part()` hívással kell felnagyítani a nesting előtt

---

## 3. Kontúr-irány Policy

Az `i_overlay` offset API az alábbi kontúr-irányokat várja el:

| Kontúr | Irány | Indok |
|---|---|---|
| Outer boundary | Counter-clockwise (CCW) | i_overlay `OutlineOffset` követelmény |
| Holes | Clockwise (CW) | i_overlay `OutlineOffset` követelmény |

Az `offset.rs` modul `ensure_ccw()` és `ensure_cw()` segédfüggvényei minden hívás előtt érvényesítik az előírt irányt a shoelace (signed area) képlettel.

**Miért kötelező?**
Az `i_overlay` csendesen rossz eredményt adhat helytelen kontúr-irány esetén hibakód visszaadása helyett. Az irány-ellenőrzés az OffsetError-t megelőzi.

---

## 4. Simplify Policy (inflate_part előfeltétele)

Minden `inflate_part()` hívás előtt kötelező a `simplify_shape(FillRule::NonZero)` előfeldolgozás:

```rust
let simplified = shape.simplify_shape(FillRule::NonZero);
let shape_to_offset = simplified.into_iter().next().unwrap_or(shape);
```

**Miért kötelező?**
A DXF importerből érkező polygonok érvényessége nem garantált:
- Önmetsző kontúrok előfordulhatnak arc-polygonizáció után
- Degenerált csúcsok (nulla-terület háromszögek) jelen lehetnek
- Az `i_overlay` offset ezekre csendesen hibás eredményt adhat

A `simplify_shape` eltávolítja az önmetsző éleket és degenerált csúcsokat. Ha az input már érvényes, a kimenet ekvivalens.

---

## 5. OffsetError típusok és kezelési elvek

| Variáns | Mikor? | Kezelés |
|---|---|---|
| `HoleCollapsed { hole_index }` | Egy lyuk eltűnik az offset után (üres eredmény) | Fatal: elhelyezés visszautasítása |
| `SelfIntersection` | Az eredmény önmetsző (a jövőbeni detektáláshoz fenntartva) | Fatal: elhelyezés visszautasítása |
| `ClipperError(String)` | Az `i_overlay` üres eredményt ad vagy belső hiba | Fatal: elhelyezés visszautasítása |

Minden `OffsetError` fatális: a hibás alkatrész geometry nem használható nesting inputként.

---

## 6. Kapcsolódások

- `src/geometry/scale.rs` — SCALE, TOUCH_TOL, mm_to_i64(), i64_to_mm()
- `src/geometry/offset.rs` — inflate_outer(), deflate_hole(), inflate_part(), OffsetError
- `src/geometry/types.rs` — Point64, Polygon64, PartGeometry
- `canvases/nesting_engine/nesting_engine_crate_scaffold.md` — feladat specifikáció
