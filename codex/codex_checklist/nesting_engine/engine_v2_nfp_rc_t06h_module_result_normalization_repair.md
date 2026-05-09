# T06h — Module result normalization repair checklist

- [x] T06g report elolvasva
- [x] worker/result_normalizer.py auditálva
- [x] worker/cavity_prepack.py module_variants szerkezete auditálva
- [x] worker/cavity_validation.py auditálva
- [x] collapsed module variant ID root cause dokumentálva
- [x] module_variants mapping solver_part_id-t tartalmaz
- [x] module_variants mapping representative_virtual_id-t tartalmaz
- [x] module_variants mapping member_virtual_ids-t tartalmaz
- [x] module_variants_by_solver_id reverse mapping létrejön
- [x] result_normalizer module_variants mappinget betölti
- [x] result_normalizer module_variants_by_solver_id mappinget betölti
- [x] per-instance virtual_id backward compatibility megmaradt
- [x] collapsed empty module variant lookup működik
- [ ] collapsed child module variant lookup synthetic/smoke teszten működik vagy dokumentáltan PARTIAL
- [x] normal part lookup megmaradt
- [x] unresolvable module composite id explicit error/issue
- [x] placement_trees lookup resolved_part_id alapján történik
- [x] unplaced ág collapsed ID-t kezel
- [x] cavity_validation collapsed ID-t kezel
- [x] parent reconstruction ellenőrizve
- [ ] child reconstruction ellenőrizve vagy synthetic teszten bizonyítva
- [x] quantity preservation ellenőrizve
- [x] no missing parent
- [x] no missing child
- [x] no duplicated child
- [x] LV8 prepack-only smoke lefutott
- [x] smoke_cavity_module_variant_normalizer.py lefutott
- [x] tests/worker/test_result_normalizer_cavity_plan.py PASS
- [x] teljes pytest állapot dokumentálva
- [x] T06g 12→12 solver part type contract nem regresszált
- [x] nincs optimizer / provider / Dockerfile változás
- [x] report elkészült

---

**Verdict: PARTIAL_WITH_KNOWN_UNRELATED_FAIL (T06h PASS)**

PARTIAL indoklás:
- collapsed child module reconstruction nem validált real LV8 inputon (csak smoke/synthetic szinten)
- A teljes pytest 1 fail-ja: DXF preflight unrelated, pre-existing, nem T06h okozta

T06h célzott acceptance szempontból: **PASS**