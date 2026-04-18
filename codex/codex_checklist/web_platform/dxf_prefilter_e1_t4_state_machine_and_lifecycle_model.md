# Codex checklist - dxf_prefilter_e1_t4_state_machine_and_lifecycle_model

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a lifecycle dokumentum: `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- [x] A dokumentum explicit kulonvalasztja a file ingest, preflight run, acceptance outcome es geometry revision lifecycle retegeket
- [x] A dokumentum rogziti a V1 minimum future canonical prefilter allapotokat docs-szinten
- [x] A dokumentum rogziti a mappinget a meglevo `app.geometry_validation_status` truth es a future prefilter state machine kozott
- [x] A dokumentum rogziti, hogy a state machine es a persistence modell kulon feladat
- [x] A dokumentum tartalmaz magas szintu transition tablat trigger/event -> next state szerkezettel
- [x] A dokumentum tartalmaz tiltott atmenet / anti-pattern listat
- [x] A dokumentum kulon jeloli a current-code truth, a future canonical contract es a later extension reszeket
- [x] A dokumentum repo-grounded hivatkozasokat ad az enum migrationokra, file object / geometry revision / validation report / files route / geometry import service kodhelyekre
- [x] A task docs-only maradt (nincs SQL migration / route / service implementacio)
- [x] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz
- [x] A runner prompt explicit tiltja a state-machine implementacios scope creep-et
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
