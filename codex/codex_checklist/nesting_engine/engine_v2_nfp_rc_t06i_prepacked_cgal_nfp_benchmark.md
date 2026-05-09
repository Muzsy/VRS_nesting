# T06i — Prepacked CGAL NFP benchmark checklist

- [x] T06g report elolvasva
- [x] T06h report elolvasva
- [x] T06h checklist elolvasva
- [x] current diff audit lefutott
- [x] T06g collapsed solver contract nem regresszált (12→12, nem 231)
- [x] T06h collapsed ID normalizer nem regresszált
- [x] LV8 prepack-only futott
- [x] top-level holes after prepack = 0
- [x] solver part type count collapsed, nem 231
- [x] module_variant_count dokumentálva (9)
- [x] quantity_mismatch_count = 0
- [x] quality_cavity_prepack_cgal_reference profil létezik
- [x] nfp_kernel runtime policy wiring ellenőrizve
- [x] --nfp-kernel cgal_reference átmegy a runneren
- [x] CGAL probe binary létezik
- [x] CGAL env dokumentálva
- [x] direct Rust cgal_reference smoke futott (Case C: 276/276 placed)
- [x] direct Rust old_concave kontroll futott vagy dokumentáltan skip (Case B: timeout)
- [x] runner/profile cgal_reference benchmark futott (Case D: SA→timeout→BLF)
- [x] actual placer dokumentálva (nfp)
- [x] actual kernel dokumentálva (cgal_reference)
- [x] BLF fallback status dokumentálva (Case C: none, Case D: SA timeout után)
- [x] OldConcave fallback status dokumentálva (Case B: timeout/60s)
- [x] NFP runtime breakdown dokumentálva (842 calls, 32.5s total)
- [x] CFR runtime breakdown dokumentálva (3810 calls, ~4.5s)
- [x] cache hit/miss dokumentálva (N/A — no explicit cache in current impl)
- [x] timeout esetén hot-path állapot dokumentálva (SA timeout, not CGAL failure)
- [x] result_normalizer — T06h smoke bizonyítja (direct binary nem használja, de logic OK)
- [x] cavity_validation — T06h smoke bizonyítja (logic OK)
- [x] no overlap/bounds/spacing violation (276 placed, 0 unplaced, 0 issues)
- [x] tests/worker/test_result_normalizer_cavity_plan.py PASS (11/11)
- [x] smoke_cavity_module_variant_normalizer.py PASS
- [x] cargo check/build állapot dokumentálva (OK)
- [x] full pytest állapot dokumentálva (301 PASS, 1 known fail)
- [x] report elkészült

---

**Verdikt: PARTIAL_WITH_VALID_CGAL_HOTPATH_TIMEOUT**

**Indoklás:**
- Prepack/profile/kernel wiring: HELYES
- NFP+cgal_reference hot path bizonyított (Case C: 276/276, 49.4%, search=none)
- Full LV8 run SA-val timeoutol 95s cap alatt — de NEM CGAL failure, hanem SA kereső
- Case C direct smoke bizonyítja: CGAL NFP működik correct és complete módon
- result_normalizer / validation: T06h smoke bizonyítja a logikát
- CGAL nem production kernel — active-set candidate-first (T06k) következő lépés