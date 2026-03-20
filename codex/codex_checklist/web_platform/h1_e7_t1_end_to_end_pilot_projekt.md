# Codex checklist - h1_e7_t1_end_to_end_pilot_projekt

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott dedikalt pilot smoke script: `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`
- [x] Letrejott dedikalt pilot runbook: `docs/qa/h1_end_to_end_pilot_runbook.md`
- [x] A pilot vegigviszi a H1 minimum lanchosszt (ingest -> geometry -> derivatives -> part/sheet -> project inputs -> run/snapshot -> worker projection/artifacts)
- [x] A pilot explicit evidence-et ellenoriz: run `done`, nem ures projection, ertelmes run_metrics, kotelezo artifact kindok
- [x] A pilot nem nyitott H2/H3 vagy altalanos stabilizacios scope-ot
- [x] Core kodigazitas nem kellett; csak pilot harness dokumentacio frissult
- [x] `python3 -m py_compile scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py` PASS
- [x] `python3 scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve, AUTO_VERIFY blokkal
