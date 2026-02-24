# VRS Nesting Codex Task — NFP Fixture könyvtár bővítése + white-box unit tesztek
TASK_SLUG: nfp_fixture_expansion

## 1) Kötelező olvasnivaló

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/report_standard.md`
4. `rust/nesting_engine/src/nfp/convex.rs` — az edge-merge + hull implementáció
5. `rust/nesting_engine/tests/nfp_regression.rs` — az integrációs tesztek (automatikusan futnak)
6. `poc/nfp_regression/convex_rect_rect.json` — fixture formátum referencia
7. `poc/nfp_regression/README.md` — fixture konvenció
8. `canvases/nesting_engine/nfp_fixture_expansion.md` — task specifikáció
9. `codex/goals/canvases/nesting_engine/fill_canvas_nfp_fixture_expansion.yaml` — lépések

---

## 2) Kontextus

A publikus `compute_convex_nfp()` edge-merge fastpath. Az eddigi tesztelés
2 db axis-aligned téglalap fixture-re korlátozódott — ez nem elegendő audit-szintű
bizonyítéknak. Ez a task:

1. Bevezeti a hiányzó **white-box unit teszteket** a `convex.rs`-be
   (hibakezelés, collinear merge, determinizmus közvetlen ellenőrzése)
2. Bővíti a **fixture könyvtárat** 5 új esettel:
   elforgatott, hatszög, skinny, collinear, háromszög

---

## 3) Nem cél

- Az edge-merge algoritmus módosítása
- Cache bekötés
- Konkáv NFP (F2-2)
- Teljesítmény benchmark

---

## 4) Kritikus megszorítások

### 4.1 — Fixture expected_nfp kiszámítása

Az `expected_nfp` értékét **hull-módszerrel (`compute_convex_nfp_reference()`)
kell előre kiszámítani**, majd kézzel ellenőrizni (legalább vertex count és
körülbelüli méret szintjén). Nem elfogadható, hogy az edge-merge kimenetét
copy-paste-led be expected_nfp-nek — az körkörös logika.

### 4.2 — Cross-check FAIL nem elrejtendő

Ha az `edge_merge_equals_hull_on_all_fixtures` teszt FAIL egy valódi konvex
fixture-n: **NE módosítsd az edge-merge kódot ebben a taskban**. Dokumentáld
a reportban Advisory szekcióban, és döntés a következő taskban születik.
Ez a task célja a helyesség **feltárása**, nem elfedése.

### 4.3 — Unit tesztek: függvénynév, nem sorszám

A report Evidence Matrix-ban unit tesztekre **függvénynévvel** hivatkozz
(pl. `test_not_convex_returns_err`), nem `convex.rs:142` típusú sor-hivatkozással.
A sor-számok az edge-merge task óta megváltoztak és tovább változnak.

---

## 5) Végrehajtás sorrendje

1. Kontextus betöltése
2. `convex.rs` unit tesztek (5 db)
3. `convex_collinear_edge.json` — legegyszerűbb, kézzel számolható
4. `convex_skinny.json`
5. `convex_triangle.json`
6. `convex_hexagon.json`
7. `convex_rotated_rect.json` — legkomplexebb, hull-lal kiszámítva
8. Integrációs teszt ellenőrzés (mind 7 fixture)
9. Checklist + report
10. Gate

---

## 6) DoD ellenőrzőlista

- [ ] `convex.rs`-ben `#[cfg(test)]` blokk létezik ≥ 5 unit teszttel
- [ ] `test_not_convex_returns_err` PASS
- [ ] `test_empty_polygon_returns_err` PASS
- [ ] `test_collinear_merge_no_extra_vertices` PASS (4 csúcs, nem több)
- [ ] `test_determinism` PASS
- [ ] `test_rect_rect_known_nfp` PASS
- [ ] 5 új fixture JSON létezik a `poc/nfp_regression/`-ben
- [ ] Minden fixture: `is_convex` + `is_ccw` teljesül a bemeneti poligonokon
- [ ] Minden fixture: `expected_nfp` hull-lal kiszámítva és kézzel ellenőrizve
- [ ] `fixture_library_passes` PASS (7 fixture)
- [ ] `edge_merge_equals_hull_on_all_fixtures` PASS (7 fixture) — vagy FAIL dokumentálva
- [ ] `cargo test` (lib + integration) PASS
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md` PASS

---

## 7) Gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md
```

Ha a cross-check FAIL egy fixture-n: ne rejtsd el. A report Advisory
szekciójában dokumentáld melyik fixture-n, mi volt a különbség, és
mit jelent ez az edge-merge stabilitásáról.