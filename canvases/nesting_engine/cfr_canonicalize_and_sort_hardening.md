# canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md

## 🎯 Funkció

A `rust/nesting_engine/src/nfp/cfr.rs` CFR (IFP \ union(NFP)) kimenetének determinisztikus stabilizálása:

1) **Ringing (outer + holes) kanonizálása** minden CFR komponensen:
   - duplikált/collinear pontok determinisztikus tisztítása
   - orientáció: outer CCW, holes CW
   - startpoint: lexikografikusan legkisebb ponttól induljon a gyűrű (rotálás)
   - 0-területű ring/komponens eldobása

2) **Komponensek totális rendezése** (ne csak “kb.”), hogy i_overlay boolean után se legyen drift:
   - stabil sort key: `min_point`, `abs(area)`, `vertex_count`, `ring_hash`
   - `ring_hash`: kanonizált ringek byte-reprezentációjából seed-mentes u64 (sha256 első 8 byte) — ugyanaz a módszer, mint a `shape_id`

3) **Unit tesztek** a CFR kanonizáció és a determinisztikus sorrend garantálására.

4) **Gate smoke bővítés**: új F4 noholes fixture + 3× NFP determinism check ezen is (plusz coverage).

Cél: a CFR output ne változzon input-sorrendtől, ring-startpoint drift-től vagy boolean belső implementációs apróságoktól.

## 🧠 Fejlesztési részletek

### Felderítés (aktuális állapot)
- `rust/nesting_engine/src/nfp/cfr.rs` jelenleg már kanonizál ringet (`dedup_ring`, `simplify_collinear`, orientáció-fix, lex-min startpoint), és kiszűri a 0-területű komponenseket.
- A komponens rendezés ma csak `min_point`, `abs(area)`, `vertex_count` kulccsal történik.
- `rust/nesting_engine/src/nfp/cache.rs` már használ seed-mentes `sha2::Sha256` alapú hash-elést (`shape_id`), ez új dependency nélkül átvehető CFR sort tie-breakhez.
- Drift-kockázat: azonos `min_point/area/vertex_count` esetén a boolean engine kimeneti sorrendje komponensszinten még eltérhet, ami candidate-sorrend és `determinism_hash` driftet okozhat.

### Kontextus / miért P0
A `nfp_based_placement_engine` candidate generálása CFR-vertexekből dolgozik. Ha a CFR komponensek/ringek sorrendje vagy startpointja driftel:
- candidate sorrend driftel,
- nudge-first-feasible más ágat talál,
- placement driftel,
- determinism_hash driftel.

### Elvárt invariánsok (CFR outputra)
Minden CFR komponens esetén:

- `outer`:
  - legalább 3 distinct pont
  - nincs egymás melletti duplikált pont
  - collinear láncok redukálva determinisztikusan
  - CCW orientáció
  - startpoint lexikografikusan legkisebb pont (x, majd y)
- `holes`:
  - mindegyik hole ring CW
  - ugyanazok a tisztítási invariánsok
- komponens-szint:
  - `abs(area) > 0`
  - komponensek totális sort-tal rendezve, azonos inputra byte-stabil output

### Implementációs terv (javasolt)
`rust/nesting_engine/src/nfp/cfr.rs`-ben:

- Adj hozzá privát helper-eket:
  - `fn canonicalize_ring(points: &mut Vec<Point64>, want_ccw: bool) -> bool`
    - visszatérési érték: “ring valid maradt-e”
  - `fn ring_hash_u64(outer: &[Point64], holes: &[Vec<Point64>]) -> u64`
  - `fn canonicalize_polygon64(poly: &mut Polygon64) -> bool`
- `compute_cfr(...)` végén:
  - alakítsd `Vec<Polygon64>`-re
  - mindegyiken `canonicalize_polygon64`
  - dobd az invalid/0-area komponenseket
  - sort key: `(min_point, abs_area, vertex_count, ring_hash_u64)`

Megjegyzés: sha256-hoz használd ugyanazt a crate-et/utilt, amit a `nfp/cache.rs` már használ (ne vezess be új dependency-t).

### F4 fixture
Adj hozzá új fixture-t:
- `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`

Célja: legyen “reális” NFP futás + plusz determinism coverage. A multi-component CFR-t elsősorban a unit tesztek garantálják (ott determinisztikusan előállítható).

### Érintett fájlok
- `rust/nesting_engine/src/nfp/cfr.rs`
- `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`
- `scripts/check.sh`
- Codex artefaktok:
  - `codex/codex_checklist/nesting_engine/cfr_canonicalize_and_sort_hardening.md`
  - `codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md`
  - `codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.verify.log`

## 🧪 Tesztállapot

### DoD
- [ ] CFR output komponensek minden ringje kanonizált (orientáció + lex-min start + tisztítás)
- [ ] 0-area / degenerált komponensek determinisztikusan eldobva
- [ ] Komponens sort totális (ring_hash tie-breakkel)
- [ ] Új unit tesztek:
  - [ ] ring startpoint drift ellen (rotált ring ugyanarra kanonizálódik)
  - [ ] orientáció drift ellen (reversed ring ugyanarra kanonizálódik)
  - [ ] komponens-sorrend stabil (input nfp_polys permutálása esetén CFR output stabil)
- [ ] Új F4 fixture létrehozva (noholes, spacing_mm explicit)
- [ ] `scripts/check.sh` bővítve: F4 3× determinism NFP módban
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- Normatív spec: `docs/nesting_engine/f2_3_nfp_placer_spec.md` (CFR canonicalize + sort elvárások)
- F2-3 core: `canvases/nesting_engine/nfp_based_placement_engine.md`
- Kód:
  - `rust/nesting_engine/src/nfp/cfr.rs`
  - `rust/nesting_engine/src/nfp/cache.rs` (sha256 minta / hash)
- Gate: `scripts/check.sh`
- Fixture-ek: `poc/nesting_engine/f2_3_f*.json`
