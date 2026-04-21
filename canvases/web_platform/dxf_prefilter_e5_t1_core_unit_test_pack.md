# DXF Prefilter E5-T1 — Unit test pack az inspect / repair / acceptance magra

## Cel
A DXF prefilter lane-ben az E2-T1→T6 ota a kovetkezo **core pipeline truth** mar megvan:
- T1 inspect (`inspect_dxf_source`)
- T2 role resolver (`resolve_dxf_roles`)
- T3 gap repair (`repair_dxf_gaps`)
- T4 duplicate dedupe (`dedupe_dxf_duplicate_contours`)
- T5 normalized DXF writer (`write_normalized_dxf`)
- T6 acceptance gate (`evaluate_dxf_prefilter_acceptance_gate`)

Minden egyes reteghez mar leteznek kulon task-specifikus unit tesztek, de jelenleg nincs egyetlen,
**fixture-driven core regression pack**, amely a teljes T1→T6 lancot ugyanazon bemeneti DXF-eken,
ugyanazon helperrel vegigviszi, es cross-step invariansokat ellenoriz.

Az E5-T1 celja ezert nem uj product logika, hanem egy **koncentralt, magas jelerteku unit test pack**
bevezetese az inspect / repair / acceptance magra, amely:
- a legfontosabb V1 fixture-csaladokat egy helyen regresszioba emeli,
- a core pipeline jelenlegi strict/lenient truthjat dokumentalja es teszttel rogzi,
- es nem nyit uj runtime / persistence / route / UI scope-ot.

## Miért most?
A jelenlegi repo-grounded helyzet:
- az E2 taskok sorban mind kaptak sajat unit tesztet, de ezek jellemzoen **reteg-specifikusak**;
- az E3/E4 taskok mar a persisted/UI vilagot epitik ezekre a core truthokra;
- ha nincs egy osszefogo, T1→T6 fixture matrix, akkor a jovobeli refaktoroknal konnyen lehet,
  hogy minden reteg kulon zold marad, de a teljes core pipeline valamelyik tipikus V1 esetben elcsuszik;
- a taskbontas V1 minimum fixture-ei (simple outer, outer+inner, gap repair, duplicate dedupe,
  ambiguous repair, rossz szin/layer kombinacio) mar most teljesen a repo current-code truthra ulnek.

A helyes E5-T1 scope tehat:
**uj, parameterezett / helperes unit test pack a teljes core chainre, a meglevo retegtesztek mellett,
termelesi kod refaktor es E3/E4 scope-nyitas nelkul.**

## Scope boundary

### In-scope
- Uj, dedikalt pytest file a T1→T6 core fixture matrixhoz.
- Valos DXF fixture-helper(ek) a tesztfile-on belul, a meglevo service-ek valos hivasaival.
- A minimum V1 scenario-k regresszios rogzitese:
  - egyszeru zart outer,
  - outer + inner,
  - kis, egyertelmu gap javitas,
  - kuszob feletti gap,
  - duplikalt kontur dedupe,
  - ambiguous gap partner,
  - rossz / konfliktusos layer-szin role eset.
- Cross-step assertions, nem csak vegso acceptance outcome:
  - inspect inventory / candidate signal,
  - role resolver output,
  - gap repair summary,
  - duplicate dedupe summary,
  - writer artifact truth,
  - acceptance outcome / reasons.
- Task-specifikus smoke, amely a test pack jelenletet, scenario matrixat es T1→T6 helper truthjat
  determinisztikusan bizonyitja.
- Checklist + report evidence frissitese.

### Out-of-scope
- Barmilyen termelesi kod vagy API contract refaktor csak azert, hogy a teszt kenyelmesebb legyen.
- E3 runtime / persistence / artifact storage / route / trigger logika modosítása.
- E4 UI / intake / drawer / review flow modosítása.
- `scripts/check.sh` globalis gate bovitese.
- Uj DXF preflight product feature vagy policy domain.
- T7 diagnostics renderer / persistence / file-list projection vilag ujratesztelese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- Core service-ek:
  - `api/services/dxf_preflight_inspect.py`
  - `api/services/dxf_preflight_role_resolver.py`
  - `api/services/dxf_preflight_gap_repair.py`
  - `api/services/dxf_preflight_duplicate_dedupe.py`
  - `api/services/dxf_preflight_normalized_dxf_writer.py`
  - `api/services/dxf_preflight_acceptance_gate.py`
- Meglevo reteg-specifikus tesztek:
  - `tests/test_dxf_preflight_inspect.py`
  - `tests/test_dxf_preflight_role_resolver.py`
  - `tests/test_dxf_preflight_gap_repair.py`
  - `tests/test_dxf_preflight_duplicate_dedupe.py`
  - `tests/test_dxf_preflight_normalized_dxf_writer.py`
  - `tests/test_dxf_preflight_acceptance_gate.py`
- Smoke mintak:
  - `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
  - `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
  - `scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`
- Dokumentacios truth:
  - `docs/qa/testing_guidelines.md`
  - `canvases/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`

## Jelenlegi repo-grounded helyzetkep

### 1. Mar vannak eros retegtesztek, de nincs core fixture matrix
A mai repo-ban a T1..T6 mind sajat, reszletes unit tesztekkel jon. Az E5-T1 celja nem ezek ujrairasa,
hanem egy **osszegzo regresszios pack** hozzaadasa, amely ugyanazon kis fixture-csaladon a teljes core
chainen megy vegig.

### 2. A T5/T6 valos utja `ezdxf`-fuggo
A writer es acceptance gate current-code truth szerint valos normalized DXF artifactot ir / olvas.
Ezert az E5-T1 pack nem tehet ugy, mintha a T5/T6 teljesen pure lenne. A helyes modell:
- a test pack explicit vallalja a valos T5/T6 utat;
- es hasznalhat `pytest.importorskip("ezdxf")` guardot, hogy a dependency truth ne legyen eltagadva.

### 3. A kuszob feletti/ambiguous gap kimenet strict vs lenient modtol fugg
A taskbontas rovid leirasaihoz kepest a mai kod pontosabb truthot tud:
- lenient modban bizonyos unresolved gap / role konfliktus `review_required` lehet,
- strict modban ugyanaz `rejected`.
Az E5-T1-nek ezt a current-code truthot kell teszttel rogitenie, nem egy leegyszerusitett,
altalanos "gap -> reject" allitast.

### 4. A task ne nyuljon a production module-okhoz, ha nem muszaj
A jelenlegi kodban mar adott minden T1→T6 hivhato entrypoint. Az E5-T1 helyes formaban
**csak uj teszt + smoke + artefakt** task.

## Konkret elvarasok

### 1. Szülessen uj, dedikalt core-pack pytest file
Javasolt uj fajl:
- `tests/test_dxf_preflight_core_unit_pack.py`

A file legyen onallo, sajat helper(ek)kel. Ne refaktoralja most kozosen a meglevo E2 teszteket,
hogy a scope kicsi es biztonsagos maradjon.

### 2. A pack valodi T1→T6 chain helperre epuljon
Legyen benne egy egyertelmu helper, amely a kovetkezo sorrendben fut:
1. `inspect_dxf_source(...)`
2. `resolve_dxf_roles(...)`
3. `repair_dxf_gaps(...)`
4. `dedupe_dxf_duplicate_contours(...)`
5. `write_normalized_dxf(...)`
6. `evaluate_dxf_prefilter_acceptance_gate(...)`

A helper adja vissza a koztes retegek truthjat is, hogy a tesztek ne csak a vegso outcome-ra lassanak ra.

### 3. Minimum fixture matrix (repo-truth szerint)
Az uj test pack minimum fedje le ezeket:

#### a) Simple closed outer -> accepted clean
- egyetlen zart outer CUT_OUTER kontur;
- varhato: nincs blocking/review, nincs repair, `accepted_for_import`.

#### b) Outer + inner -> accepted clean
- egy zart outer es egy zart inner;
- varhato: inner nem torik el a writer/gate alatt, `accepted_for_import`.

#### c) Unambiguous small gap -> repaired then accepted
- kis, onmagaba zarhato vagy egyertelmu parositasu cut-like gap a threshold alatt;
- varhato: legalabb 1 applied gap repair, acceptance clean vagy tisztan accepted.

#### d) Gap over threshold -> unresolved truth rogzitese
- threshold feletti gap;
- current-code truth szerint ezt a pack strict es/vagy lenient modban is rogzitse ugy,
  hogy vilagos legyen: lenientben review_required lehet, strictben rejected.

#### e) Duplicate contour -> deduped then accepted
- ket azonos zart kontur ugyanazon szerepkorben;
- varhato: applied duplicate dedupe > 0, vegul accepted.

#### f) Ambiguous gap partner -> lenient review / strict reject
- olyan nyitott cut-like vegpontpar, ahol tobb lehetseges partner van;
- varhato: lenient modban `review_required`, strict modban `rejected`.

#### g) Rossz / konfliktusos layer-szin role eset
- non-canonical layeren vegyes cut + marking jel vagy layer-vs-color konfliktus;
- a test current-code truth szerint rogzitse, hogy ez review vagy reject iranyba megy,
  es ne lehessen csendben accepted.

### 4. A tesztek ne csak a vegso outcome-ot ellenorizzek
Minden scenario a pipeline megfelelo retegen is allitson legalabb egy fontos invariansrol:
- inspect: open path / duplicate / contour candidate counts,
- role resolver: layer role assignment vagy blocking/review count,
- gap repair: applied gap repairs / remaining open paths,
- dedupe: applied dedupes / unresolved duplicate groups,
- writer: `normalized_dxf.output_path`, canonical layer truth vagy skipped source entity summary,
- acceptance: `acceptance_outcome`, blocking reasons, review reasons.

### 5. A pack current-code truth szerint vallalja az `ezdxf` dependency-t
Mivel a T5/T6 valodi normalized DXF-et ir/olvas, a pack hasznaljon explicit dependency truth-ot,
peldaul:
- `pytest.importorskip("ezdxf")`

De ezt a reportban kulon nevezze meg: ez nem kiskapu, hanem a writer/gate jelenlegi valos fuggese.

### 6. Keszuljon task-specifikus smoke
Javasolt uj fajl:
- `scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`

A smoke minimum bizonyitsa:
- az uj test pack file letezik;
- a file T1→T6 core helperre epul;
- a fenti minimum scenario-k kulcsszavai/szerkezete bent vannak;
- a pack current-code truth szerint vallalja az `ezdxf` guardot;
- nem nyit route/UI/persistence scope-ot.

### 7. A task ne gyengitse a meglevo retegteszteket
Az E5-T1 nem torolheti vagy irhatja felul a meglevo T1..T6 test file-okat. Ezek maradjanak meg,
az uj pack ezek fole jon plusz regressziokent.

### 8. Verifikacio
Minimum futtasok:
- `python3 -m py_compile tests/test_dxf_preflight_core_unit_pack.py scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`
- `python3 -m pytest -q tests/test_dxf_preflight_core_unit_pack.py`
- `python3 scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md`

A report kulon terjen ki erre:
- miert uj cross-module fixture matrix a helyes E5-T1 current-code truth, es miert nem a meglevo E2 tesztek ujrairasa;
- mely minimum scenario-kat fedi le a pack;
- hogyan jelenik meg benne a strict vs lenient truth;
- miert vallalja explicit modon az `ezdxf` dependency truthot a T5/T6 miatt.
