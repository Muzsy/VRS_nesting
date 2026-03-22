# H2-E3-T3 rule matching logic

## Funkcio
A feladat a H2 cut rule reteg harmadik, logikai lepese.
A cel, hogy a mar letezo `geometry_contour_classes` contour-osztalyozasi truth es a
mar letezo `cut_contour_rules` szabalytruth alapjan egy determinisztikus matching
engine eldontse, hogy egy adott contourhoz melyik szabaly hasznalando.

Ez a task szandekosan nem cut rule CRUD, nem manufacturing profile resolver,
nem project manufacturing selection, nem snapshot manufacturing bovites, nem
manufacturing plan builder, es nem run-level persistencia.
A scope kifejezetten az, hogy a matching logika onallo, tesztelheto service-kent
megszulessen ugy, hogy a kesobbi H2-E4 manufacturing plan builder erre tudjon epulni.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - egy dedikalt matching service bevezetese, amely egy explicit `cut_rule_set_id`
    alatt kivalasztja a contouronkent hasznalando `cut_contour_rules` rekordot;
  - a `geometry_contour_classes` es a `cut_contour_rules` meglevo truth retegere epulo,
    determinisztikus szabaly-kivalasztasi logika;
  - a `contour_kind` + `feature_class` + `enabled` +
    `min_contour_length_mm`/`max_contour_length_mm` mezokon alapulo minimum matching;
  - feature-class fallback logika: specifikus `feature_class` elonyben, majd `default`;
  - stabil tie-break szabaly, hogy azonos inputra azonos rule valasztodjon;
  - task-specifikus smoke script a sikeres es hibas agakra.
- Nincs benne:
  - uj tabla vagy migracio;
  - `geometry_contour_classes` sorok visszairasa `rule_id`-val vagy barmilyen direkt
    szabalykotes a contour-class truth tablaba;
  - manufacturing profile resolver vagy project manufacturing selection bekotes;
  - run snapshot vagy manufacturing plan persistencia;
  - `run_manufacturing_plans` / `run_manufacturing_contours` irasa;
  - preview, postprocess vagy export.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E3-T3 task: contour class -> rule hozzarendeles, output matching engine.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 detailed roadmap; kimondja, hogy a rule matching a contour classificationra
    es a cut contour rules vilagara epul, es hogy a manufacturing plan builder majd
    ezt fogyasztja.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - manufacturing policy eredmeny kulon layer; nem szabad a geometry truth-tal vagy a
    kesobbi plan persisted vilaggal osszemosni.
- `api/services/geometry_contour_classification.py`
  - a jelenlegi contour-class truth service; ezt kell olvasni, nem modositani.
- `api/services/cut_contour_rules.py`
  - a szabalytruth CRUD service; a matching ennek rekordjait fogyasztja.
- `api/services/cut_rule_sets.py`
  - a rule set owner-scope mintaja; a matching inputjaban explicit `cut_rule_set_id`
    lesz, nem resolver.
- `scripts/smoke_h2_e2_t2_contour_classification_service.py`
  - minta a contour-class oldali smoke logikahoz.
- `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
  - minta a rule truth oldali smoke logikahoz.

### Konkret elvarasok

#### 1. A matching service explicit rule setre dolgozzon
A service ne probaljon manufacturing profile-t vagy project selectiont feloldani.
Az input legyen explicit `cut_rule_set_id`.
Ez a task nem resolver, hanem matching engine.

#### 2. A matching csak valos, mar letezo mezokre epuljon
A matching minimum a mar letezo mezo-kombinaciokra epulhet:
- `contour_kind`
- `feature_class`
- `enabled`
- `min_contour_length_mm`
- `max_contour_length_mm`
- `sort_order`
- stabil tie-break

Ne talalj ki uj klasszifikacios mezot, uj catalogot, vagy manufacturing plan-specifikus
adatot, ami most nincs a repoban.

#### 3. A feature_class fallback legyen egyertelmu
A varhato minimum logika:
- eloszor az azonos `contour_kind` + azonos `feature_class` szabalyok;
- ha nincs ilyen, akkor az azonos `contour_kind` + `feature_class=default` szabalyok;
- ha igy sincs jelolt, a contour unmatched marad.

#### 4. A hossztartomany-szures a contour-class truthbol jojjon
A `geometry_contour_classes.perimeter_mm` legyen a matching hossz-alapja.
A `min_contour_length_mm` / `max_contour_length_mm` szures erre epuljon.
A task ne kezdjen el tovabbi geometriaszamitasokat vagy manufacturing plan-metrikat gyartani.

#### 5. A tie-break legyen determinisztikus
Ha tobb szabaly is illeszkedik, a valasztas legyen determinisztikus.
Minimum elvart sorrend:
- specifikus `feature_class` elobb, mint `default`;
- kisebb `sort_order` elobb;
- vegul stabil azonosito-szintu tie-break.

A reportban nevezd meg konkretan a hasznalt tie-break szabalyokat.

#### 6. A service eredmenye maradjon kulon matching-output, ne truth-modositas
A service adjon vissza egy tiszta, feldolgozhato eredmenyt, peldaul:
- `geometry_derivative_id`
- `cut_rule_set_id`
- contouronkent:
  - `contour_index`
  - `contour_kind`
  - `feature_class`
  - `matched_rule_id`
  - `matched_rule_summary`
  - `matched_via` (`feature_class` vagy `default`)
  - `unmatched_reason` ha nincs rule

De ne irjon vissza a `geometry_contour_classes` tablaba, es ne hozzon letre uj persisted
matching tablakat.

#### 7. A smoke bizonyitsa a fo vagy-agakat
A task-specifikus smoke legalabb ezt bizonyitsa:
- outer contour outer rule-t kap;
- inner contour inner rule-t kap;
- specifikus `feature_class` szabaly elonyt kap a `default` szaballyal szemben;
- hossz-tartomanyon kivuli contour nem kap szabalyt;
- disabled szabaly nem valaszthato;
- tobb jelolt eseten a tie-break determinisztikus;
- a service nem modosit contour-class truth tablakat.

### DoD
- [ ] Keszul dedikalt rule matching service.
- [ ] A matching engine a `geometry_contour_classes` + `cut_contour_rules` meglevo truthra epul.
- [ ] A matching explicit `cut_rule_set_id` inputtal dolgozik, nem resolver.
- [ ] A `feature_class` fallback egyertelmu es tesztelt.
- [ ] A `min_contour_length_mm` / `max_contour_length_mm` szures mukodik.
- [ ] A tie-break determinisztikus es dokumentalt.
- [ ] Unmatched contour eseten tiszta indok kerul visszaadasra.
- [ ] A task nem ir vissza `geometry_contour_classes` vagy egyeb persisted truth tablaba.
- [ ] A task nem nyitja ki a manufacturing plan / snapshot / export scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task persisted matching truthot kezd gyartani idovel elott;
  - a matching resolverre vagy plan builderre terjed ki;
  - a tie-break nem determinisztikus;
  - a `geometry_contour_classes` truth visszafertozodik rule-id szintu allapottal.
- Mitigacio:
  - explicit no-migration / no-persistencia scope;
  - explicit `cut_rule_set_id` input, nincs resolver;
  - tiszta, dokumentalt precedence sorrend;
  - smoke a matching eredmenyre es a no-write garanciara.
- Rollback:
  - service + smoke + report valtozasok egy task-commitban visszavonhatok;
  - a kesobbi plan builder ugyanarra a matching contractra epulhet vagy cserelheti,
    anelkul hogy domain truth migraciot kellene visszabontani.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/cut_rule_matching.py scripts/smoke_h2_e3_t3_rule_matching_logic.py`
  - `python3 scripts/smoke_h2_e3_t3_rule_matching_logic.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `api/services/geometry_contour_classification.py`
- `api/services/cut_rule_sets.py`
- `api/services/cut_contour_rules.py`
- `scripts/smoke_h2_e2_t2_contour_classification_service.py`
- `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
