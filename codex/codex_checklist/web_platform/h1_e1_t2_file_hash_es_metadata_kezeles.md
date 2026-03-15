# Codex checklist - h1_e1_t2_file_hash_es_metadata_kezeles

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] `complete_upload` a DB `storage_bucket` mezot kanonikus source bucketrol allitja
- [x] `complete_upload` a DB `file_name` mezot `storage_path` basename-bol kepzi
- [x] `complete_upload` szerveroldalon szamolja a `byte_size` mezot a valos storage objektumbol
- [x] `complete_upload` szerveroldalon szamolja a `sha256` mezot a valos storage objektumbol
- [x] `complete_upload` szerveroldalon, determinisztikus szaballyal allitja elo a `mime_type` truth-ot
- [x] Sikertelen object letoltes eseten nem jon letre felrevezeto `app.file_objects` rekord
- [x] Legacy metadata mezo parsing legfeljebb backward-compat marad, nem irja felul a szerver truth-ot
- [x] Letrejott a task-specifikus smoke script: `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py`
- [x] Smoke script futtatva: `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
