# Codex checklist - h0_e6_t1_storage_bucket_strategia_es_path_policy

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a dedikalt storage source-of-truth doksi: `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- [x] A doksi rogzitette a kanonikus H0 bucket inventoryt (`source-files`, `geometry-artifacts`, `run-artifacts`)
- [x] A doksi rogzitette az entitas -> bucket mappinget (`app.file_objects`, `app.run_artifacts`, reserved `geometry-artifacts`)
- [x] A doksi bucketenkent kanonikus path mintat ad
- [x] A doksi explicit kimondja, hogy `app.geometry_derivatives` nem storage-truth
- [x] A doksi rogzitette az immutabilitas / overwrite alapelveket
- [x] A doksi elokesziti a H0-E6-T2 policy taskot, de nem implemental policyt
- [x] Minimal docs szinkron megtortent a fo architecture es H0 roadmap dokumentumban
- [x] A task szandekosan nem hozott letre migraciot
- [x] A task szandekosan nem hozott letre storage provisioning scriptet
- [x] A task szandekosan nem hozott letre RLS policyt
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
