"""Shared orchestration bodies for TypeScript coupling phase helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from desloppify.languages._framework.base.types import LangRuntimeContract
from desloppify.state import Issue


def make_boundary_issues(
    single_entries: list[dict],
    path: Path,
    graph: dict,
    lang: LangRuntimeContract,
    shared_prefix: str,
    tools_prefix: str,
    *,
    detect_boundary_candidates_fn,
    rel_fn,
    make_issue_fn,
    log_fn,
) -> tuple[list[Issue], int]:
    """Create boundary-candidate issues, deduplicated against single-use."""
    single_use_emitted = set()
    for entry in single_entries:
        is_size_ok = 50 <= entry["loc"] <= 200
        is_colocated = lang.get_area and (
            lang.get_area(rel_fn(entry["file"])) == lang.get_area(entry["sole_importer"])
        )
        if not is_size_ok and not is_colocated:
            single_use_emitted.add(rel_fn(entry["file"]))

    results: list[Issue] = []
    deduped = 0
    boundary_entries, total_shared = detect_boundary_candidates_fn(
        path,
        graph,
        shared_prefix=shared_prefix,
        tools_prefix=tools_prefix,
        skip_basenames={"index.ts", "index.tsx"},
    )
    for entry in boundary_entries:
        if rel_fn(entry["file"]) in single_use_emitted:
            deduped += 1
            continue
        results.append(
            make_issue_fn(
                "coupling",
                entry["file"],
                f"boundary::{entry['sole_tool']}",
                tier=3,
                confidence="medium",
                summary=(
                    f"Boundary candidate ({entry['loc']} LOC): only used by {entry['sole_tool']} "
                    f"({entry['importer_count']} importers)"
                ),
                detail={
                    "sole_tool": entry["sole_tool"],
                    "importer_count": entry["importer_count"],
                    "loc": entry["loc"],
                },
            )
        )
    if deduped:
        log_fn(
            f"         ({deduped} boundary candidates skipped — covered by single_use)"
        )
    return results, total_shared


def phase_coupling(
    path: Path,
    lang: LangRuntimeContract,
    *,
    make_boundary_issues_fn,
    build_dep_graph_fn,
    detect_single_use_fn,
    get_src_path_fn,
    detect_coupling_violations_fn,
    detect_cross_tool_imports_fn,
    detect_cycles_and_orphans_fn,
    detect_facades_fn,
    detect_pattern_anomalies_fn,
    detect_naming_inconsistencies_fn,
    adjust_potential_fn,
    log_fn,
) -> tuple[list[Issue], dict[str, int]]:
    """Run the coupling phase with dependency-injected collaborators."""
    results: list[Issue] = []
    graph = build_dep_graph_fn(path)
    lang.dep_graph = graph
    zone_map = lang.zone_map

    single_use_issues, single_entries, single_candidates = detect_single_use_fn(
        path, graph, lang
    )
    results.extend(single_use_issues)

    src_path = get_src_path_fn()
    shared_prefix = f"{src_path}/shared/"
    tools_prefix = f"{src_path}/tools/"

    coupling_issues, coupling_edges = detect_coupling_violations_fn(
        path, graph, lang, shared_prefix, tools_prefix
    )
    results.extend(coupling_issues)

    boundary_issues, _ = make_boundary_issues_fn(
        single_entries, path, graph, lang, shared_prefix, tools_prefix
    )
    results.extend(boundary_issues)

    cross_tool_issues, cross_edges = detect_cross_tool_imports_fn(
        path, graph, lang, tools_prefix
    )
    results.extend(cross_tool_issues)

    cycle_orphan_issues, total_graph_files = detect_cycles_and_orphans_fn(path, graph, lang)
    results.extend(cycle_orphan_issues)

    results.extend(detect_facades_fn(graph, lang))

    pattern_issues, total_areas = detect_pattern_anomalies_fn(path)
    results.extend(pattern_issues)

    naming_issues, total_dirs = detect_naming_inconsistencies_fn(path, lang)
    results.extend(naming_issues)

    log_fn(f"         → {len(results)} coupling/structural issues total")
    potentials = {
        "single_use": adjust_potential_fn(zone_map, single_candidates),
        "coupling": coupling_edges + cross_edges,
        "cycles": adjust_potential_fn(zone_map, total_graph_files),
        "orphaned": adjust_potential_fn(zone_map, total_graph_files),
        "patterns": total_areas,
        "naming": total_dirs,
        "facade": adjust_potential_fn(zone_map, total_graph_files),
    }
    return results, potentials


__all__ = ["make_boundary_issues", "phase_coupling"]
