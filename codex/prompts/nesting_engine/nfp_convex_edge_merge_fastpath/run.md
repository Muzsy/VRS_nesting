# VRS Nesting Codex Task — NFP Nesting Engine: Konvex NFP edge-merge fastpath
TASK_SLUG: nfp_convex_edge_merge_fastpath

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md` — SCALE=1_000_000, TOUCH_TOL=1i64
6. `rust/nesting_engine/src/geometry/types.rs` — cross_product_i128, is_ccw, is_convex
7. `rust/nesting_engine/src/nfp/convex.rs` — **a jelenlegi hull implementáció** (ezt módosítod)
8. `rust/nesting_engine/src/nfp/mod.rs` — NfpError (nem változik)
9. `rust/nesting_engine/tests/nfp_regression.rs` — bővítendő cross-check teszttel
10. `poc/nfp_regression/*.json` — fixture-ök (nem változnak)
11. `canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md` — task specifikáció
12. `codex/goals/canvases/nesting_engine/fill_canvas_nfp_convex_edge_merge_fastpath.yaml` — lépések

Ha bármelyik fájl nem létezik: állj meg és jelezd pontosan mit kerestél és hol.

---

## 2) Kontextus — miért ez a task

A `nfp_computation_convex` taskban lezárt hull implementáció
(pairwise sums + monotone chain, O(n×m×log)) matematikailag korrekt,
de a nesting engine-ben a konvex NFP tömegesen hívódik:
placement loop, rotációs variánsok, és az F2-2 konkáv fallback konvex
dekompozíciós ágán. Inflate után 200-400 csúcsos poligonoknál
n×m = 40k–160k pont hívásonként — ez szűk keresztmetszet lesz.

Az edge-merge (O(n+m)) azonos eredményt ad konvex esetben, de
nagyságrendekkel gyorsabb. A hull **megmarad** referencia- és fallback-funkcióban.

---

## 3) Nem cél

- A hull (`compute_convex_nfp_reference`) eltávolítása vagy logikai módosítása
- Konkáv NFP (F2-2 task)
- NFP cache módosítása
- `rust/vrs_solver/` bármilyen módosítása
- Python runner módosítása

---

## 4) Kritikus implementációs megszorítások (nem alkuképes)

### 4.1 — i128 a szög-merge komparátorban (overflow védelem)

Az edge-merge szív: `cross = cross_product_i128(eA[i], eB[j])`.
Ez dönti el, hogy melyik élt adjuk hozzá következőnek.
**Közvetlen i64 szorzat TILOS** — ugyanaz az overflow-veszély, mint a hull-ban.

### 4.2 — Lexikografikus kezdőpont (determinizmus)

A kezdőpont meghatározza az output kontúr bejárási sorrendjét.
**Kötelező:** `argmin_lex(x, y)` — lexikografikusan legkisebb csúcs
mindkét poligonon. Ez garantálja, hogy `canonicalize(edge_merge) == canonicalize(hull)`
a cross-check tesztben.

### 4.3 — Collinear merge (`cross == 0`)

Ha két él párhuzamos, az output él a kettő összege.
Ez ekvivalens a hull `turn <= 0` kollineáris-szűrésével.
**Ha ezt kihagyod:** az NFP extra csúcsokat tartalmaz párhuzamos éleknél
és a cross-check teszt FAIL-el.

### 4.4 — Hull átnevezés, nem törlés

A jelenlegi `compute_convex_nfp()` → `compute_convex_nfp_reference()`.
Semmi sem törlődik, a hull logika byte-azonos marad.
Az F2-2/F2-3 esetleges fallback-je a `compute_convex_nfp_reference()`-t hívja.

---

## 5) Végrehajtás sorrendje (YAML lépések szerint)

1. **Szabályok + kontextus betöltése** — convex.rs, nfp_regression.rs áttekintése
2. **Hull átnevezés** — `compute_convex_nfp` → `compute_convex_nfp_reference` (csak rename)
3. **Edge-merge implementáció** — új `compute_convex_nfp()` O(n+m)
4. **Cross-check teszt** — `nfp_regression.rs` bővítése
5. **Checklist + report vázlat** — codex artefaktok
6. **Repo gate** — `./scripts/verify.sh` (kötelező, utoljára)

---

## 6) DoD ellenőrzőlista (a gate előtt saját ellenőrzés)

- [ ] `compute_convex_nfp()` az edge-merge implementációt hívja
- [ ] `compute_convex_nfp_reference()` a hull (logikailag változatlan, csak átnevezve)
- [ ] `fixture_library_passes` integrációs teszt PASS (automatikusan edge-merge-re fut)
- [ ] `edge_merge_equals_hull_on_all_fixtures` PASS minden fixture-re
- [ ] Párhuzamos élek (`cross == 0`): collinear merge unit teszttel igazolva
- [ ] `cross_product_i128()` az egyetlen szorzási útvonal a merge komparátorban
- [ ] Lexikografikus kezdőpont (`argmin_lex`) mindkét poligonon
- [ ] Determinizmus: azonos input kétszer → azonos csúcslista
- [ ] `cargo build vrs_solver --release` PASS (F1 regresszió nem sérül)
- [ ] `cargo test` (nesting_engine) PASS (unit + integrációs tesztek)

---

## 7) Gate futtatása (kötelező, kizárólag wrapperrel)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md
```

**Ha FAIL:** ne merge-elj. Ha a cross-check teszt FAIL: a `compute_convex_nfp()`
visszakapja a hull implementációt (`_wip` suffix az edge-merge-re), és az F2-2
task megkezdható a hull alapon is.

---

## 8) Output elvárás

A végén add meg a módosított/létrehozott fájlok teljes tartalmát:

- `rust/nesting_engine/src/nfp/convex.rs` (teljes)
- `rust/nesting_engine/tests/nfp_regression.rs` (teljes)
- `codex/codex_checklist/nesting_engine/nfp_convex_edge_merge_fastpath.md`
- `codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md`
