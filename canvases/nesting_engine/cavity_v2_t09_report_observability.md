# Cavity v2 T09 — Report és observability bővítés

## Cél

A nesting run metrics és a frontend UI kibővítése: a `cavity_plan_v2` összefoglaló adatok jelenjenek meg a result report-ban és a NewRunPage eredmény nézetben. A worker result normalizer `metrics_jsonb` kapja meg a részletes cavity prepack statisztikát, a TypeScript típusok bővülnek, és a UI megjelenít egy cavity prepack összefoglalót.

---

## Miért szükséges

A T06 rekurzív fill és T07 flatten futása után nem látszik, hogy:
- hány virtual parent keletkezett
- hány belső elhelyezés történt (szintenként is)
- volt-e fallback
- hány lyuk tűnt el a solver inputból

Ezeket az adatokat a `cavity_plan_v2.summary` mező már tartalmazza (T06 gyártja), de a normalizer metric és a UI nem jeleníti meg.

---

## Érintett valós fájlok

### Módosítandó:
- `worker/result_normalizer.py` — `metrics_jsonb["cavity_plan"]` mező bővítése
- `frontend/src/lib/types.ts` — `cavity_prepack_summary` típus bővítése (T02 alapoz rá)
- `frontend/src/pages/NewRunPage.tsx` — cavity prepack összefoglaló panel

---

## Nem célok / scope határok

- **Nem** módosítja a cavity prepack algoritmust.
- **Nem** készít új API endpoint-ot.
- **Nem** változtatja a normalizer core logikáját.
- A v1 `cavity_plan_v1` metrics mező megmarad a régi formátumban.

---

## Részletes implementációs lépések

### 1. `worker/result_normalizer.py` bővítése

A `_normalize_solver_output_projection_v2()` vége felé, ahol a `metrics_jsonb["cavity_plan"]` blokk van (sor ~979):

**Jelenlegi (cavity_plan_v1 kompatibilis):**
```python
if cavity_enabled:
    metrics_jsonb["cavity_plan"] = {
        "enabled": True,
        "version": cavity_plan_version,
        "virtual_parent_count": len(virtual_parts),
    }
```

**Bővített (v1 + v2):**
```python
if cavity_enabled:
    cp_metrics: dict[str, Any] = {
        "enabled": True,
        "version": cavity_plan_version,
        "virtual_parent_count": len(virtual_parts),
    }
    if cavity_plan_version == "cavity_plan_v2":
        summary_raw = cavity_plan.get("summary") or {}
        quantity_delta = cavity_plan.get("quantity_delta") or {}
        diagnostics = cavity_plan.get("diagnostics") or []
        # Belső elhelyezések számlálása placement_rows-ból
        internal_count = sum(
            1 for row in placement_rows
            if isinstance(row.get("metadata_jsonb"), dict)
            and row["metadata_jsonb"].get("placement_scope") == "internal_cavity"
        )
        nested_count = sum(
            1 for row in placement_rows
            if isinstance(row.get("metadata_jsonb"), dict)
            and (row["metadata_jsonb"].get("cavity_tree_depth") or 0) >= 2
        )
        proxy_count = sum(
            1 for d in diagnostics
            if isinstance(d, dict) and d.get("code") == "child_has_holes_outer_proxy_used"
        )
        top_holes_removed = len(virtual_parts)
        used_cavity_count = int(summary_raw.get("usable_cavity_count") or 0)
        total_qty_delta = sum(
            int(v.get("internal_qty", 0)) for v in quantity_delta.values()
            if isinstance(v, dict)
        )
        cp_metrics.update({
            "cavity_plan_version": cavity_plan_version,
            "max_cavity_depth": int((cavity_plan.get("policy") or {}).get("max_cavity_depth") or 3),
            "usable_cavity_count": int(summary_raw.get("usable_cavity_count") or 0),
            "used_cavity_count": used_cavity_count,
            "internal_placement_count": int(internal_count),
            "nested_internal_placement_count": int(nested_count),
            "top_level_holes_removed_count": int(top_holes_removed),
            "holed_child_proxy_count": int(proxy_count),
            "total_internal_qty": int(total_qty_delta),
            "quantity_delta_summary": {
                k: {"original": int(v.get("original_required_qty", 0)),
                    "internal": int(v.get("internal_qty", 0)),
                    "top_level": int(v.get("top_level_qty", 0))}
                for k, v in quantity_delta.items()
                if isinstance(v, dict)
            },
            "diagnostics_by_code": _count_diagnostics_by_code(diagnostics),
        })
    metrics_jsonb["cavity_plan"] = cp_metrics
```

Helper:
```python
def _count_diagnostics_by_code(diagnostics: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in diagnostics:
        if isinstance(d, dict):
            code = str(d.get("code") or "unknown")
            counts[code] = counts.get(code, 0) + 1
    return counts
```

### 2. `frontend/src/lib/types.ts` bővítése

`cavity_prepack_summary` típus frissítése (T02 alapján):

```typescript
cavity_prepack_summary?: {
  enabled: boolean;
  version?: string;
  cavity_plan_version?: string;
  virtual_parent_count?: number;
  internal_placement_count?: number;
  nested_internal_placement_count?: number;
  used_cavity_count?: number;
  usable_cavity_count?: number;
  top_level_holes_removed_count?: number;
  holed_child_proxy_count?: number;
  total_internal_qty?: number;
  max_cavity_depth?: number;
  quantity_delta_summary?: Record<string, {
    original: number;
    internal: number;
    top_level: number;
  }>;
  diagnostics_by_code?: Record<string, number>;
};
```

### 3. `frontend/src/pages/NewRunPage.tsx` bővítése

Ha a run result tartalmaz `cavity_prepack_summary`-t, jelenítsen meg egy összefoglaló panelt. Keress egy megfelelő helyet a run result section-ben (ahol a meglévő metrics vagy run info megjelenik).

```tsx
{result?.metrics_jsonb?.cavity_plan?.enabled && (
  <div className="cavity-prepack-summary">
    <h4>Cavity prepack összefoglaló</h4>
    <ul>
      <li>Verzió: {result.metrics_jsonb.cavity_plan.version ?? "n/a"}</li>
      <li>Virtuális parentek: {result.metrics_jsonb.cavity_plan.virtual_parent_count ?? 0}</li>
      <li>Belső elhelyezések: {result.metrics_jsonb.cavity_plan.internal_placement_count ?? 0}</li>
      <li>Matrjoska (≥2. szint): {result.metrics_jsonb.cavity_plan.nested_internal_placement_count ?? 0}</li>
      <li>Top-level solver holes eltávolítva: {result.metrics_jsonb.cavity_plan.top_level_holes_removed_count ?? 0}</li>
      <li>Lyukas child proxy: {result.metrics_jsonb.cavity_plan.holed_child_proxy_count ?? 0}</li>
    </ul>
  </div>
)}
```

Ügyelj rá, hogy a `result.metrics_jsonb` típusát a `types.ts` alapján kell elérni. Ha a types.ts-ben más struktúra van, igazodj ahhoz.

---

## Adatmodell / contract változások

- `metrics_jsonb.cavity_plan` mező bővítése v2 specifikus mezőkkel
- `cavity_prepack_summary` TypeScript típus bővítése
- Nincs API contract breaking change — minden új mező optional

---

## Backward compatibility szempontok

- v1 `cavity_plan_v1` esetén a `metrics_jsonb.cavity_plan` megtartja az egyszerű formátumát (csak `enabled`, `version`, `virtual_parent_count`)
- A v2 specifikus mezők csak v2 plan esetén kerülnek a metrics-be
- A frontend panel csak akkor jelenik meg, ha `cavity_plan.enabled === true`

---

## Hibakódok / diagnosztikák

- `diagnostics_by_code` mező összeszámolja a cavity prepack diagnosztikákat kód szerint
- Ha a summary mező hiányzik a cavity_plan-ból, az értékek `0` default-ot kapnak

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
cd frontend && npx tsc --noEmit
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t09_report_observability.md
```

Tesztesetek:
- `test_v2_metrics_contain_cavity_plan_summary`: v2 plan futás után `metrics_jsonb.cavity_plan` tartalmazza az összes új mezőt
- `test_v1_metrics_unchanged`: v1 plan futás után a cavity_plan mező egyszerű formátumú
- TypeScript build hibamentes

---

## Elfogadási feltételek

- `metrics_jsonb.cavity_plan` tartalmazza v2 esetén: `internal_placement_count`, `nested_internal_placement_count`, `top_level_holes_removed_count`, `holed_child_proxy_count`, `quantity_delta_summary`
- TypeScript típusok frissítve
- Frontend panel megjelenik ha `cavity_plan.enabled`
- v1 tesztek változatlanul zöldek

---

## Rollback / safety notes

- A `metrics_jsonb` bővítés backward compatible: meglévő kód nem omlik össze
- A frontend panel `{condition && ...}` guard mögé van téve
- TypeScript típus bővítés backward compatible (optional mezők)

---

## Dependency

- T07 (normalizer flatten, metrics_jsonb cavity_plan blokk) — kötelező
- T02 (QualityProfileName + cavity_prepack_summary alap) — ajánlott
