# NFP Regression Fixtures

Ez a könyvtár konvex (F2-1) es konkav (F2-2) NFP regresszios fixture-okat tartalmaz.

## Fixture formátum

Minden `.json` fájl alap mezo-i:

- `description`: rövid leírás
- `fixture_type`: `convex` vagy `concave`
- `polygon_a`: `[[x, y], ...]` egész koordináták
- `polygon_b`: `[[x, y], ...]` egész koordináták
- `rotation_deg_b`: B alakzat rotációja fokban (jelen regresszioban 0)
- `expected_nfp`: elvárt NFP kontúr
- `expected_vertex_count`: elvárt csúcsszám

Opcionális mezo:

- `expect_exact_fallback`: `true` eseten az orbitalis exact mod fallbackje is validalt.
- `prefer_exact`: `true` eseten a no-fallback exact modot is kotelezoen ellenorizzuk.
- `allow_exact_equals_stable`: ha `true`, exact vs stable canonical ring azonossag elfogadott.
- `expect_exact_error`: ha `true`, no-fallback exact hiba explicit elvart.

## Konkav fixture-ek (F2-2)

Konkav fixture-eknel az elvart eredmeny a stabil alaputvonalra vonatkozik:

1. konkav -> konvex dekompozicio
2. resz-NFP-k (konvex Minkowski)
3. union
4. boundary clean (CCW + lexikografikus start, onmetszesmentes)

Az osszehasonlitas tesztoldalon canonical ring alapjan tortenik.

## Megjegyzés

A fixture koordináták integer rácson vannak megadva. Az NFP összehasonlítás
tesztoldalon kanonizált kontúrral történik (CCW + determinisztikus kezdőpont).

## Quarantine workflow (`quarantine_generated_*.json`)

### Mit jelent a quarantine fixture?

- `quarantine_generated_*.json` fajlok fuzz altal generalt "gyanus" vagy uj geometriak.
- Ezeket a regresszios teszt futtatja, de alapertelmezetten nem tekintjuk veglegesen elfogadott fixture library elemnek.

### Hogyan generaljuk?

- Hasznalt script: `scripts/fuzz_nfp_regressions.py`
- Pelda:
  - `python3 scripts/fuzz_nfp_regressions.py --seed 20260225 --count 3`

### Hogyan acceptaljuk?

1. Valaszd ki a stabilan reprodukalhato quarantine fixture-t.
2. Nevezd at beszelo nevre (ne maradjon `quarantine_generated_...` prefix).
3. Frissitsd a `description` mezot ertelmezheto geometrai esetre.
4. Ellenorizd az `expected_nfp` es `expected_vertex_count` stabilitasat tobbszori futassal.
5. Futtasd:
   - `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression`
6. Ha PASS es a viselkedes vedeni kivant regresszio, mehet commitba accepted fixture-kent.

Megjegyzes: a repoban nincs kulon "build_expected" script; acceptalas manual review + regresszios teszt PASS alapjan tortenik.

### Mi tortenjen, ha kesobb torik?

1. Reprodukald fix paranccsal (seed, fixture fajl, tesztnev).
2. Dontsd el, hogy:
   - algoritmus regresszio tortent -> javitas szukseges, vagy
   - a fixture elvaras hibas -> expected mezo korrekcio + dokumentalt indok.
3. A dontest reportban rogzitsd (task report + verify log hivatkozas).
