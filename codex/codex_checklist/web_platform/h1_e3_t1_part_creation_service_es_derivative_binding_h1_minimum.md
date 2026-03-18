# Codex checklist - h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult kulon H1-minimum schema migracio a `part_revisions` geometry/derivative bindinghez
- [x] Keszult explicit `api/services/part_creation.py` service
- [x] Keszult minimalis `api/routes/parts.py` endpoint es be van kotve az `api/main.py`-ba
- [x] A service csak projektbe tartozo, `validated` geometry revisiont fogad el
- [x] A service kotelezoen `nesting_canonical` derivative-re epit
- [x] Uj `code` eseten uj `part_definition` + `revision_no = 1` jon letre
- [x] Meglevo `code` eseten a kovetkezo `revision_no` jon letre es frissul a `current_revision_id`
- [x] A `part_revision` rekord explicit geometry/derivative bindinget tarol
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`
- [x] A smoke fake kliens implementalja az `execute_rpc()`-t a `create_part_revision_atomic` hivasra
- [x] A report explicit modon jeloli a T1 implementacio T2 (`20260317120000`) migration fuggoseget
- [x] `python3 -m py_compile api/services/part_creation.py api/routes/parts.py api/main.py scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
