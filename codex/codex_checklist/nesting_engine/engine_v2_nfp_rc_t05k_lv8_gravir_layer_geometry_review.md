# T05k — Checklist

## T05k: LV8 Gravír Layer Geometry Review

### Előkészítés
- [x] T05j riport és policy megértése
- [x] T05j audit fájlok elolvasása
- [x] Referencia riport elolvasása

### Reprodukció
- [x] Lv8_11612 preflight_review_required reprodukálva
  - Futtatva: `python3 scripts/experiments/audit_production_dxf_holes.py .../lv8jav`
  - Eredmény: `Lv8_11612_6db REV3.dxf: import=IMPORT_OK_WITH_HOLES preflight=PREFLIGHT_REVIEW_REQUIRED outer=520 holes=11`
  - Review ok: `DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW`
  - Nincs `preflight_rejected` ✅

### Entity-Level Audit
- [x] Gravír layer entity-level audit script létrehozva
  - Fájl: `scripts/experiments/audit_lv8_11612_gravir_entities.py`
- [x] Gravír layer entity breakdown elvégezve
  - CIRCLE: 2db (radius=9.125mm, crosshair markerek)
  - LINE: 32db (részleges crosshair minta)
  - TEXT: 8db (üres, import placeholder)
- [x] JSON output létrehozva
  - `tmp/reports/nfp_cgal_probe/t05k_lv8_11612_gravir_entity_audit.json`
- [x] Markdown output létrehozva
  - `tmp/reports/nfp_cgal_probe/t05k_lv8_11612_gravir_entity_audit.md`

### Layer Summary
- [x] Layer-by-layer összesítés elkészült
- [x] Külön táblázat: layer name, entity types, entity count, closed ring count, text/mtext count, cut/marking candidates, total area, notes
- [x] Layer 0: 108 entities, 8 cut candidates, 0 marking
- [x] Gravír: 42 entities, 0 cut candidates, 0 marking (8 text mind üres)

### Nested Contour Classification
- [x] Minden kontúrra classification elkészült
- [x] Gravír:0 → ARTIFACT (HIGH) — CIRCLE crosshair marker
- [x] Gravír:1 → ARTIFACT (HIGH) — CIRCLE crosshair marker
- [x] Layer 0:3 → MATERIAL_ISLAND (LOW) — depth=2 nested island
- [x] Layer 0:4 → MATERIAL_ISLAND (LOW) — depth=2 nested island
- [x] Layer 0 depth=1 kontúrok → CUT_INNER (HIGH)

### Debug Export
- [x] ASCII debug export létrehozva
  - `tmp/reports/nfp_cgal_probe/t05k_lv8_11612_nested_contours_ascii.md`

### Döntési javaslat
- [x] Döntési javaslat dokumentálva
- [x] REVIEW marad (NEM accepted_for_import)
- [x] Gravír CIRCLE markerek = ARTIFACT, NEM cut/marking
- [x] Depth=2 kontúrok = MATERIAL_ISLAND, NEM auto-accept
- [x] Shapely is_valid korlátozás változatlan

### Regresszió ellenőrzés
- [x] `pytest tests/test_dxf_preflight_real_world_regressions.py -q`
  - Eredmény: **7/7 PASSED** ✅
- [x] `pytest tests/test_dxf_preflight_role_resolver.py -q`
  - Eredmény: **25/25 PASSED** ✅
- [x] LV8 többi fájl nem romlott
  - accepted_for_import: 10 (változatlan)
  - preflight_review_required: 1 (Lv8_11612, változatlan)
  - preflight_rejected: 0 (változatlan)

### Nincs tiltott módosítás
- [x] Nincs T08 indítás ✅
- [x] Nincs CGAL production integráció ✅
- [x] Nincs production Dockerfile módosítás ✅
- [x] Nincs worker runtime módosítás ✅
- [x] Nincs DXF automatikus accepted_for_import minősítés ✅
- [x] Gravír layer kontúrok nem törölve csendben ✅
- [x] CUT kontúr nem átminősítve MARKING-ra ✅
- [x] TEXT/MTEXT nem konvertálva cut geometriává ✅
- [x] Nincs silent fallback ✅
- [x] Eredeti DXF nem módosítva destruktívan ✅

### Riportok és dokumentáció
- [x] Fő riport létrehozva
  - `codex/reports/nesting_engine/engine_v2_nfp_rc_t05k_lv8_gravir_layer_geometry_review.md`
- [x] Checklist létrehozva
  - `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t05k_lv8_gravir_layer_geometry_review.md`

### Státusz összefoglaló
- Státusz: **PASS**
- Módosított fájlok: 1 új script (`audit_lv8_11612_gravir_entities.py`)
- Nincs breaking change
- Minden teszt átmegy
- LV8 benchmark stabil
