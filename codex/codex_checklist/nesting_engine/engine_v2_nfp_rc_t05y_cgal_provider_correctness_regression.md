# T05y — CGAL Provider Correctness Regression Checklist

**Dátum:** 2026-05-06
**Státusz:** PASS

---

## Build / Infrastructure

- [x] CGAL probe build PASS
- [x] cargo check PASS
- [x] cargo test --lib PASS (60/60 passed, dokumentált pre-existing warning-ekkel)
- [x] old_concave default továbbra is működik
- [x] cgal_reference explicit guard mögött működik (`NFP_ENABLE_CGAL_REFERENCE=1` + `NFP_CGAL_PROBE_BIN=...`)

---

## Toxic Pair Regression

- [x] toxic lv8_pair_01 CGAL providerrel SUCCESS (203ms)
- [x] toxic lv8_pair_02 CGAL providerrel SUCCESS (145ms)
- [x] toxic lv8_pair_03 CGAL providerrel SUCCESS (78ms) — smoke script által igazolva

---

## Kontroll Pair — OldConcave vs CGAL Összehasonlítás

- [x] legalább 1 old_concave success kontroll pair összehasonlítva CGAL-lal
  - lv8_pair_holes_smoke: old_concave SUCCESS, cgal_reference SUCCESS
  - Output különbség (holes count): old_concave outer-only (0 holes), cgal_reference 1 hole
  - Ez nem correctness hiba — T07 mindkettőn PASS

---

## T07 Correctness Benchmark

- [x] T07 correctness provider útvonalon lefutott (via external_json — CGAL probe output)
- [x] FP/FN riport készült (lv8_pair_01, lv8_pair_holes_smoke, real_work_dxf_holes_pair_02 — mind 0 FP, 0 FN)
- [x] lv8_pair_01 T07: PASS, boundary_penetration=0.0mm
- [x] lv8_pair_holes_smoke T07: PASS, HOLES_AWARE active (1 hole), hole_boundary_penetration=0.01mm
- [x] real_work_dxf_holes_pair_02 T07: PASS, HOLES_AWARE active (1 hole parsed), hole_boundary_collision=2

---

## Real Holes-Os Fixture — Provider Útvonal

- [x] real_work_dxf_holes_pair_02 CGAL providerrel tesztelve
- [x] fixture tényleg tartalmaz holes_mm mezőt nem üresen (part_a: 2 holes, 30 vertices)
- [x] provider input JSON továbbítja a holes-t
- [x] CGAL output holes_i64 parse-olódik (1 hole ring, 3 vertices)
- [x] T07 hole-aware containment aktív (`HOLES_AWARE: 1 hole(s) parsed from holes_i64`)
- [x] holes input NEM lett csendben outer-onlyként kezelve (output: 1 hole)

---

## Cache Key

- [x] cache key OldConcave vs CgalReference szeparáció igazolva (`NfpCacheKey.nfp_kernel` mező)
- [x] nincs silent fallback CGAL hibánál (provider explicit `Err`-t ad vissza)
- [x] CGAL hiba/timeout/invalid output NEM kerül sikeres cache entryként tárolásra

---

## Production Guardok

- [x] nincs production Dockerfile módosítás
- [x] nincs worker production runtime módosítás
- [x] CGAL NEM default kernel (default: OldConcave)
- [x] CGAL NEM production dependency

---

## T08 Tiltás

- [x] nincs T08 indítás

---

## Összesítés

| Kategória | Eredmény |
|-----------|----------|
| Build / Infra | 5/5 ✅ |
| Toxic Pair Regression | 3/3 ✅ |
| Kontroll Pair Összehasonlítás | 1/1 ✅ |
| T07 Correctness | 3/3 ✅ |
| Real Holes Fixture | 6/6 ✅ |
| Cache Key | 3/3 ✅ |
| Production Guardok | 4/4 ✅ |
| T08 Tiltás | 1/1 ✅ |
| **ÖSSZESEN** | **26/26 ✅** |

**VERDIKT: ALL CHECKS PASSED — CGAL provider correctness regression VALIDÁLHATÓ, mehet a következő lépésre.**
