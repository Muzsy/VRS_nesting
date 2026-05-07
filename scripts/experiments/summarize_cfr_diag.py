#!/usr/bin/env python3
"""Parse CFR_DIAG_V1 log lines and produce summary JSON + Markdown."""

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

LOG_RE = re.compile(
    r"CFR_DIAG_V1 "
    r"nfp_poly_count=(\d+) "
    r"nfp_total_vertices=(\d+) "
    r"nfp_max_vertices=(\d+) "
    r"ifp_vertices=(\d+) "
    r"union_time_ms=([\d.]+) "
    r"diff_time_ms=([\d.]+) "
    r"component_count=(\d+) "
    r"component_total_vertices=(\d+) "
    r"candidate_count=(\d+) "
    r"total_cfr_time_ms=([\d.]+)"
)


def parse_log(path: str) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            m = LOG_RE.search(line)
            if m:
                records.append({
                    "nfp_poly_count": int(m.group(1)),
                    "nfp_total_vertices": int(m.group(2)),
                    "nfp_max_vertices": int(m.group(3)),
                    "ifp_vertices": int(m.group(4)),
                    "union_time_ms": float(m.group(5)),
                    "diff_time_ms": float(m.group(6)),
                    "component_count": int(m.group(7)),
                    "component_total_vertices": int(m.group(8)),
                    "candidate_count": int(m.group(9)),
                    "total_cfr_time_ms": float(m.group(10)),
                })
    return records


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(len(s) * 0.95)
    return s[min(idx, len(s) - 1)]


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else "tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag.log"
    out_dir = Path(log_path).parent

    records = parse_log(log_path)
    if not records:
        print("No CFR_DIAG_V1 records found!")
        sys.exit(1)

    nfp_poly_counts = [r["nfp_poly_count"] for r in records]
    nfp_total_verts = [r["nfp_total_vertices"] for r in records]
    union_times = [r["union_time_ms"] for r in records]
    diff_times = [r["diff_time_ms"] for r in records]
    total_times = [r["total_cfr_time_ms"] for r in records]
    component_counts = [r["component_count"] for r in records]

    top10_slowest = sorted(records, key=lambda r: r["total_cfr_time_ms"], reverse=True)[:10]

    # Group by nfp_poly_count buckets
    bucket_times = defaultdict(list)
    for r in records:
        bucket_times[r["nfp_poly_count"]].append(r["total_cfr_time_ms"])

    bucket_avg = {k: sum(v) / len(v) for k, v in bucket_times.items()}

    summary = {
        "total_cfr_calls": len(records),
        "max_nfp_poly_count": max(nfp_poly_counts),
        "max_nfp_total_vertices": max(nfp_total_verts),
        "max_nfp_max_vertices": max(r["nfp_max_vertices"] for r in records),
        "max_union_time_ms": max(union_times),
        "max_diff_time_ms": max(diff_times),
        "max_total_cfr_time_ms": max(total_times),
        "max_component_count": max(component_counts),
        "avg_union_time_ms": round(sum(union_times) / len(union_times), 2),
        "avg_diff_time_ms": round(sum(diff_times) / len(diff_times), 2),
        "avg_total_cfr_time_ms": round(sum(total_times) / len(total_times), 2),
        "p95_total_cfr_time_ms": round(p95(total_times), 2),
        "union_vs_diff_ratio": round(sum(union_times) / max(sum(diff_times), 0.001), 3),
        "top10_slowest": top10_slowest,
        "avg_time_by_nfp_count": {str(k): round(v, 2) for k, v in sorted(bucket_avg.items())},
    }

    json_path = out_dir / "t06a_lv8_cfr_diag_summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"JSON saved: {json_path}")

    # Markdown
    md_lines = [
        "# T06a — CFR Bottleneck Audit Summary",
        "",
        "## Key Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total CFR calls | {summary['total_cfr_calls']} |",
        f"| Max NFP poly count | {summary['max_nfp_poly_count']} |",
        f"| Max NFP total vertices | {summary['max_nfp_total_vertices']} |",
        f"| Max single NFP vertices | {summary['max_nfp_max_vertices']} |",
        f"| Max union_time_ms | {summary['max_union_time_ms']:.2f} |",
        f"| Max diff_time_ms | {summary['max_diff_time_ms']:.2f} |",
        f"| Max total CFR time | {summary['max_total_cfr_time_ms']:.2f}ms |",
        f"| Avg union_time_ms | {summary['avg_union_time_ms']:.2f}ms |",
        f"| Avg diff_time_ms | {summary['avg_diff_time_ms']:.2f}ms |",
        f"| Avg total CFR time | {summary['avg_total_cfr_time_ms']:.2f}ms |",
        f"| p95 total CFR time | {summary['p95_total_cfr_time_ms']:.2f}ms |",
        f"| Union/Diff time ratio | {summary['union_vs_diff_ratio']:.3f}x |",
        "",
        "## Top 10 Slowest CFR Calls",
        "",
        f"| Rank | nfp_poly | nfp_total_v | union_ms | diff_ms | total_ms | components |",
        f"|------|----------|-------------|----------|---------|----------|------------|",
    ]
    for i, r in enumerate(top10_slowest, 1):
        md_lines.append(
            f"| {i} | {r['nfp_poly_count']} | {r['nfp_total_vertices']} | "
            f"{r['union_time_ms']:.2f} | {r['diff_time_ms']:.2f} | "
            f"{r['total_cfr_time_ms']:.2f} | {r['component_count']} |"
        )

    md_lines += [
        "",
        "## Avg CFR Time by NFP Polygon Count",
        "",
        f"| NFP polys | Avg total_ms |",
        f"|------------|--------------|",
    ]
    for k, v in sorted(summary["avg_time_by_nfp_count"].items(), key=lambda x: int(x[0])):
        md_lines.append(f"| {k} | {v:.2f} |")

    ratio = summary["union_vs_diff_ratio"]
    md_lines += [
        "",
        "## Hypothesis Evaluation",
        "",
        f"- **A) NFP union is main bottleneck**: "
        f"UNION avg={summary['avg_union_time_ms']:.2f}ms, DIFF avg={summary['avg_diff_time_ms']:.2f}ms "
        f"ratio={ratio:.1f}x — "
        + ("YES, union dominates" if ratio > 2 else "NO, roughly comparable"),
        "",
        "- **B) IFP difference is main bottleneck**: "
        f"DIFF max={summary['max_diff_time_ms']:.2f}ms — "
        + ("significant at scale" if summary['max_diff_time_ms'] > 50 else "not primary bottleneck"),
        "",
        "- **C) Candidate extraction/sorting bottleneck**: "
        f"max component_count={summary['max_component_count']} — "
        + ("high component count may contribute" if summary['max_component_count'] > 20 else "moderate component count"),
        "",
        "- **D) Too many irrelevant NFP polygons**: "
        f"max_nfp_poly_count={summary['max_nfp_poly_count']} — "
        + ("BBOX prefilter recommended" if summary['max_nfp_poly_count'] > 50 else "moderate polygon count"),
        "",
        "- **E) CGAL output vertex count**: "
        f"max_nfp_total_vertices={summary['max_nfp_total_vertices']} — "
        + ("high vertex count confirmed" if summary['max_nfp_total_vertices'] > 5000 else "moderate vertex count"),
        "",
        "- **F) Strategy::List is wrong**: i_overlay uses Strategy::List — "
        "measurement-based change only, no blind swap",
        "",
        "- **G) Cache working but CFR recomputation**: "
        "cache hit rate ~99% confirmed in T05z, bottleneck is per-call CFR not cache lookup",
    ]

    md_path = out_dir / "t06a_lv8_cfr_diag_summary.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    print(f"MD saved: {md_path}")


if __name__ == "__main__":
    main()
