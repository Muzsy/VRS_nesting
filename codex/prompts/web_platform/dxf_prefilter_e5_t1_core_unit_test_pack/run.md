Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj product/runtime/UI scope-ot; ez teszt-task.
- Ne torold vagy irjad at a meglevo T1..T6 reteg-specifikus tesztfile-okat.
- A helyes current-code truth most: az E5-T1 nem replacement, hanem plusz,
  cross-module fixture matrix a T1→T6 core pipeline-ra.
- A pack valos `inspect -> role -> gap -> dedupe -> writer -> acceptance` helperre
  epuljon; ne fake-eld ki a writer/gate reteget csak azert, hogy purebb legyen.
- A T5/T6 `ezdxf` dependency truthjat vallald explicit modon (pl. `pytest.importorskip("ezdxf")`).
- A strict vs lenient kimeneti kulonbseget current-code truth szerint rogzitsd;
  ne leegyszerusitett "minden gap reject" jellegu szabalyokat tesztelj.

Modellezesi elvek:
- A pack legyen onallo uj tesztfile, sajat helperrel.
- Minimum scenario-k:
  - simple closed outer -> accepted clean
  - outer + inner -> accepted clean
  - kis egyertelmu gap -> repaired then accepted
  - threshold feletti gap -> unresolved truth rogzitese
  - duplicate contour -> deduped then accepted
  - ambiguous gap partner -> lenient review / strict reject
  - rossz vagy konfliktusos layer-szin role eset -> ne lehessen csendben accepted
- Ne csak a vegso acceptance outcome-ot nezd; minden scenario allitson koztes
  reteg-invariansrol is (inspect/role/gap/dedupe/writer/gate).
- A smoke legyen structural, ne route/UI/persistence smoke.

Kulon figyelj:
- a pack ne nyisson T7 / persistence / runtime / file-list route scope-ot;
- a tesztfile ne legyen csak copy-paste a meglevo E2 tesztekbol, hanem egyetlen,
  attekintheto core regression pack legyen;
- ha a current-code truth szerint valamely scenario lenientben review_required,
  strictben rejected, ezt kulon es egyertelmuen nevezd meg a tesztben;
- a reportban kulon emeld ki, hogy a pack miert ertekes a meglevo retegtesztek mellett.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile tests/test_dxf_preflight_core_unit_pack.py scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`
- `python3 -m pytest -q tests/test_dxf_preflight_core_unit_pack.py`
- `python3 scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`

A reportban kulon terj ki erre:
- miert uj cross-module fixture matrix a helyes E5-T1 current-code truth, es miert nem a meglevo E2 tesztek ujrairasa;
- pontosan mely minimum scenario-kat fedi le a pack;
- hogyan jelenik meg benne a strict vs lenient truth;
- miert vallalja explicit modon az `ezdxf` dependency truthot a T5/T6 miatt.
