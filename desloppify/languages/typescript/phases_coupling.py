"""Coupling and dependency-oriented TypeScript phase helpers."""

from __future__ import annotations

from pathlib import Path

from desloppify.base.discovery.file_paths import rel
from desloppify.base.discovery.paths import get_src_path
from desloppify.base.output.terminal import log
from desloppify.engine.detectors import coupling as coupling_detector_mod
from desloppify.engine.detectors import graph as graph_detector_mod
from desloppify.engine.detectors import naming as naming_detector_mod
from desloppify.engine.detectors import orphaned as orphaned_detector_mod
from desloppify.engine.detectors import single_use as single_use_detector_mod
from desloppify.engine.policy.zones import adjust_potential, filter_entries
from desloppify.languages._framework.base.types import LangRuntimeContract
from desloppify.languages._framework.issue_factories import (
    make_cycle_issues,
    make_facade_issues,
    make_orphaned_issues,
    make_single_use_issues,
)
from desloppify.languages.typescript.detectors import deps as deps_detector_mod
from desloppify.languages.typescript.detectors import facade as facade_detector_mod
from desloppify.languages.typescript.detectors import patterns_analysis as patterns_detector_mod
from desloppify.languages.typescript.phases_coupling_phase import (
    make_boundary_issues as _make_boundary_issues_core,
)
from desloppify.languages.typescript.phases_coupling_phase import (
    phase_coupling as _phase_coupling_core,
)
from desloppify.languages.typescript.phases_config import TS_SKIP_DIRS, TS_SKIP_NAMES
from desloppify.state import Issue, make_issue


def detect_single_use(
    path: Path, graph: dict, lang: LangRuntimeContract
) -> tuple[list[Issue], list[dict], int]:
    """Detect single-use abstractions."""
    single_entries, single_candidates = single_use_detector_mod.detect_single_use_abstractions(
        path, graph, barrel_names=lang.barrel_names
    )
    single_entries = filter_entries(lang.zone_map, single_entries, "single_use")
    issues = make_single_use_issues(
        single_entries, lang.get_area, skip_dir_names={"commands"}, stderr_fn=log
    )
    return issues, single_entries, single_candidates


def detect_coupling_violations(
    path: Path,
    graph: dict,
    lang: LangRuntimeContract,
    shared_prefix: str,
    tools_prefix: str,
) -> tuple[list[Issue], int]:
    """Detect backwards coupling violations."""
    coupling_entries, coupling_edge_counts = coupling_detector_mod.detect_coupling_violations(
        path, graph, shared_prefix=shared_prefix, tools_prefix=tools_prefix
    )
    coupling_entries = filter_entries(lang.zone_map, coupling_entries, "coupling")
    results: list[Issue] = []
    for entry in coupling_entries:
        results.append(
            make_issue(
                "coupling",
                entry["file"],
                entry["target"],
                tier=2,
                confidence="high",
                summary=f"Backwards coupling: shared imports {entry['target']} (tool: {entry['tool']})",
                detail={
                    "target": entry["target"],
                    "tool": entry["tool"],
                    "direction": entry["direction"],
                },
            )
        )
    return results, coupling_edge_counts.eligible_edges


def detect_cross_tool_imports(
    path: Path,
    graph: dict,
    lang: LangRuntimeContract,
    tools_prefix: str,
) -> tuple[list[Issue], int]:
    """Detect cross-tool import violations."""
    cross_tool, cross_edge_counts = coupling_detector_mod.detect_cross_tool_imports(
        path, graph, tools_prefix=tools_prefix
    )
    cross_tool = filter_entries(lang.zone_map, cross_tool, "coupling")
    results: list[Issue] = []
    for entry in cross_tool:
        results.append(
            make_issue(
                "coupling",
                entry["file"],
                entry["target"],
                tier=2,
                confidence="high",
                summary=(
                    f"Cross-tool import: {entry['source_tool']}→{entry['target_tool']} "
                    f"({entry['target']})"
                ),
                detail={
                    "target": entry["target"],
                    "source_tool": entry["source_tool"],
                    "target_tool": entry["target_tool"],
                    "direction": entry["direction"],
                },
            )
        )
    if cross_tool:
        log(f"         cross-tool: {len(cross_tool)} imports")
    return results, cross_edge_counts.eligible_edges


def detect_cycles_and_orphans(
    path: Path, graph: dict, lang: LangRuntimeContract
) -> tuple[list[Issue], int]:
    """Detect import cycles and orphaned files."""
    results: list[Issue] = []
    cycle_entries, _ = graph_detector_mod.detect_cycles(graph)
    cycle_entries = filter_entries(lang.zone_map, cycle_entries, "cycles", file_key="files")
    results.extend(make_cycle_issues(cycle_entries, log))

    orphan_entries, total_graph_files = orphaned_detector_mod.detect_orphaned_files(
        path,
        graph,
        extensions=lang.extensions,
        options=orphaned_detector_mod.OrphanedDetectionOptions(
            extra_entry_patterns=lang.entry_patterns,
            extra_barrel_names=lang.barrel_names,
            dynamic_import_finder=deps_detector_mod.build_dynamic_import_targets,
            alias_resolver=deps_detector_mod.ts_alias_resolver,
        ),
    )
    orphan_entries = filter_entries(lang.zone_map, orphan_entries, "orphaned")
    results.extend(make_orphaned_issues(orphan_entries, log))
    return results, total_graph_files


def detect_facades(graph: dict, lang: LangRuntimeContract) -> list[Issue]:
    """Detect re-export facade files."""
    facade_entries, _ = facade_detector_mod.detect_reexport_facades(graph)
    facade_entries = filter_entries(lang.zone_map, facade_entries, "facade")
    return make_facade_issues(facade_entries, log)


def detect_pattern_anomalies(path: Path) -> tuple[list[Issue], int]:
    """Detect pattern consistency anomalies across areas."""
    pattern_result = patterns_detector_mod.detect_pattern_anomalies_result(path)
    pattern_entries = pattern_result.entries
    total_areas = pattern_result.population_size
    results: list[Issue] = []
    for entry in pattern_entries:
        results.append(
            make_issue(
                "patterns",
                entry["area"],
                entry["family"],
                tier=3,
                confidence=entry.get("confidence", "low"),
                summary=f"Competing patterns ({entry['family']}): {entry['review'][:120]}",
                detail={
                    "family": entry["family"],
                    "patterns_used": entry["patterns_used"],
                    "pattern_count": entry["pattern_count"],
                    "review": entry["review"],
                },
            )
        )
    return results, total_areas


def detect_naming_inconsistencies(
    path: Path, lang: LangRuntimeContract
) -> tuple[list[Issue], int]:
    """Detect naming convention inconsistencies within directories."""
    naming_entries, total_dirs = naming_detector_mod.detect_naming_inconsistencies(
        path,
        file_finder=lang.file_finder,
        skip_names=TS_SKIP_NAMES,
        skip_dirs=TS_SKIP_DIRS,
    )
    results: list[Issue] = []
    for entry in naming_entries:
        results.append(
            make_issue(
                "naming",
                entry["directory"],
                entry["minority"],
                tier=3,
                confidence="low",
                summary=(
                    f"Naming inconsistency: {entry['minority_count']} {entry['minority']} files "
                    f"in {entry['majority']}-majority dir ({entry['total_files']} total)"
                ),
                detail={
                    "majority": entry["majority"],
                    "majority_count": entry["majority_count"],
                    "minority": entry["minority"],
                    "minority_count": entry["minority_count"],
                    "outliers": entry["outliers"],
                },
            )
        )
    return results, total_dirs


def make_boundary_issues_impl(
    single_entries: list[dict],
    path: Path,
    graph: dict,
    lang: LangRuntimeContract,
    shared_prefix: str,
    tools_prefix: str,
) -> tuple[list[dict], int]:
    """Create boundary-candidate issues, deduplicated against single-use."""
    return _make_boundary_issues_core(
        single_entries,
        path,
        graph,
        lang,
        shared_prefix,
        tools_prefix,
        detect_boundary_candidates_fn=coupling_detector_mod.detect_boundary_candidates,
        rel_fn=rel,
        make_issue_fn=make_issue,
        log_fn=log,
    )


def phase_coupling_impl(
    path: Path,
    lang: LangRuntimeContract,
    *,
    make_boundary_issues_fn=make_boundary_issues_impl,
) -> tuple[list[Issue], dict[str, int]]:
    """Run the coupling phase with injectable boundary issue construction."""
    return _phase_coupling_core(
        path,
        lang,
        make_boundary_issues_fn=make_boundary_issues_fn,
        build_dep_graph_fn=deps_detector_mod.build_dep_graph,
        detect_single_use_fn=detect_single_use,
        get_src_path_fn=get_src_path,
        detect_coupling_violations_fn=detect_coupling_violations,
        detect_cross_tool_imports_fn=detect_cross_tool_imports,
        detect_cycles_and_orphans_fn=detect_cycles_and_orphans,
        detect_facades_fn=detect_facades,
        detect_pattern_anomalies_fn=detect_pattern_anomalies,
        detect_naming_inconsistencies_fn=detect_naming_inconsistencies,
        adjust_potential_fn=adjust_potential,
        log_fn=log,
    )


__all__ = [
    "coupling_detector_mod",
    "detect_coupling_violations",
    "detect_cross_tool_imports",
    "detect_cycles_and_orphans",
    "detect_facades",
    "detect_naming_inconsistencies",
    "detect_pattern_anomalies",
    "detect_single_use",
    "make_boundary_issues_impl",
    "orphaned_detector_mod",
    "phase_coupling_impl",
]
