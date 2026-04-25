#!/usr/bin/env python3
"""
Offline source-level smoke for T7: strategy_field_sources UI polish.
No DB, Supabase, worker, solver binary, or node_modules required.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

passed: list[str] = []
failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"  PASS  {name}")
    else:
        failed.append(name)
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. RunDetailPage — strategy_field_sources UI
# ---------------------------------------------------------------------------
print("\n[1] frontend/src/pages/RunDetailPage.tsx — strategy_field_sources rendering")

run_detail_src = read(REPO_ROOT / "frontend" / "src" / "pages" / "RunDetailPage.tsx")

check("RunDetailPage: uses strategy_field_sources", "strategy_field_sources" in run_detail_src)
check("RunDetailPage: Strategy field sources UI text", "Strategy field sources" in run_detail_src)
check("RunDetailPage: fallback No field source evidence", "No field source evidence" in run_detail_src)
check("RunDetailPage: Strategy and engine audit still present", "Strategy and engine audit" in run_detail_src)
check("RunDetailPage: Not available yet fallback still present", "Not available yet" in run_detail_src)
check("RunDetailPage: sorted key rendering (.sort())", ".sort()" in run_detail_src)
check("RunDetailPage: Object.keys on strategy_field_sources", "Object.keys" in run_detail_src)

# ---------------------------------------------------------------------------
# 2. frontend/src/lib/types.ts — ViewerDataResponse interface
# ---------------------------------------------------------------------------
print("\n[2] frontend/src/lib/types.ts — ViewerDataResponse strategy_field_sources")

types_src = read(REPO_ROOT / "frontend" / "src" / "lib" / "types.ts")

check("types.ts: strategy_field_sources field", "strategy_field_sources?" in types_src)
check("types.ts: Record<string, string> type", "Record<string, string>" in types_src)

# ---------------------------------------------------------------------------
# 3. frontend/e2e/support/mockApi.ts — ViewerData interface
# ---------------------------------------------------------------------------
print("\n[3] frontend/e2e/support/mockApi.ts — ViewerData strategy_field_sources")

mock_src = read(REPO_ROOT / "frontend" / "e2e" / "support" / "mockApi.ts")

check("mockApi.ts: strategy_field_sources in ViewerData", "strategy_field_sources" in mock_src)

# ---------------------------------------------------------------------------
# 4. T7 E2E spec
# ---------------------------------------------------------------------------
print("\n[4] T7 Playwright spec")

t7_spec_path = REPO_ROOT / "frontend" / "e2e" / "new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts"
check("T7 spec exists", t7_spec_path.exists())

if t7_spec_path.exists():
    t7_src = t7_spec_path.read_text(encoding="utf-8")
    check("T7 spec: strategy_field_sources payload", "strategy_field_sources" in t7_src)
    check("T7 spec: quality_profile assertion", "quality_profile" in t7_src)
    check("T7 spec: engine_backend_hint assertion", "engine_backend_hint" in t7_src)
    check("T7 spec: global_default assertion", "global_default" in t7_src)
    check("T7 spec: run_config source assertion", "run_config" in t7_src)
    check("T7 spec: request source assertion", '"request"' in t7_src or "'request'" in t7_src)
    check("T7 spec: Strategy field sources assertion", "Strategy field sources" in t7_src)
    check("T7 spec: fallback test present", "No field source evidence" in t7_src or "fallback" in t7_src.lower())
    check("T7 spec: null/empty field sources test", "null" in t7_src and ("fallback" in t7_src.lower() or "No field source" in t7_src))

# ---------------------------------------------------------------------------
# 5. Rollout doc — strategy_field_sources not a known limitation anymore
# ---------------------------------------------------------------------------
print("\n[5] Rollout doc — strategy_field_sources known limitation removed")

rollout_path = REPO_ROOT / "docs" / "web_platform" / "architecture" / "new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md"
check("Rollout doc exists", rollout_path.exists())

if rollout_path.exists():
    rdoc = rollout_path.read_text(encoding="utf-8")
    # The old limitation said "not yet rendered" — it must be gone
    old_limitation_phrases = [
        "not yet rendered in the Run Detail audit card",
        "A future T6/polish task can add",
        "is not yet rendered",
    ]
    for phrase in old_limitation_phrases:
        check(
            f"Rollout doc: old known limitation phrase removed: {phrase[:60]!r}",
            phrase not in rdoc,
            f"still contains: {phrase!r}",
        )
    # Should now mention field sources are covered / rendered
    check(
        "Rollout doc: mentions field-source breakdown is now shown",
        "field source" in rdoc.lower() or "field_source" in rdoc.lower(),
    )

# ---------------------------------------------------------------------------
# 6. Artefakt-fegyelem
# ---------------------------------------------------------------------------
print("\n[6] Artefakt-fegyelem — T7 saját alkönyvtár, nincs root-level duplikátum")

t7_slug = "new_run_wizard_step2_strategy_t7_strategy_field_sources_polish"
check("T7 canvas dir exists", (REPO_ROOT / "canvases" / "web_platform" / t7_slug).is_dir())
check("T7 goal yaml dir exists", (REPO_ROOT / "codex" / "goals" / "canvases" / "web_platform" / t7_slug).is_dir())
check("T7 runner prompt dir exists", (REPO_ROOT / "codex" / "prompts" / "web_platform" / t7_slug).is_dir())

canvas_root = REPO_ROOT / "canvases" / "web_platform"
root_md = list(canvas_root.glob("new_run_wizard_step2_strategy_t7*.md"))
check("No root-level T7 canvas .md duplicate", len(root_md) == 0, f"found: {[f.name for f in root_md]}")

goals_root = REPO_ROOT / "codex" / "goals" / "canvases" / "web_platform"
root_yaml = list(goals_root.glob("new_run_wizard_step2_strategy_t7*.yaml"))
check("No root-level T7 goal yaml duplicate", len(root_yaml) == 0, f"found: {[f.name for f in root_yaml]}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = len(passed) + len(failed)
print(f"\n{'='*60}")
if failed:
    print(f"FAIL: {len(failed)} check(s) failed, {len(passed)} passed ({total} total)")
    for name in failed:
        print(f"  - {name}")
    sys.exit(1)
else:
    print(f"PASS: {len(passed)} checks passed ({total} total)")
    sys.exit(0)
