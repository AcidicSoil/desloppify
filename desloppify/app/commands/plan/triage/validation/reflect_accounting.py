"""Reflect-stage coverage-ledger parsing and issue-accounting helpers."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from desloppify.base.output.terminal import colorize
from desloppify.engine.plan_triage import extract_issue_citations

DecisionKind = Literal["cluster", "permanent_skip"]


@dataclass(frozen=True)
class ReflectDisposition:
    """One issue's intended disposition as declared by the reflect stage."""

    issue_id: str
    decision: DecisionKind
    target: str

    def to_dict(self) -> dict:
        """Serialize for JSON persistence in ``plan.json``."""
        return {"issue_id": self.issue_id, "decision": self.decision, "target": self.target}

    @classmethod
    def from_dict(cls, data: dict | ReflectDisposition) -> ReflectDisposition:
        """Deserialize from persisted plan data, or pass through unchanged."""
        if isinstance(data, cls):
            return data
        return cls(
            issue_id=data.get("issue_id", ""),
            decision=data.get("decision", "cluster"),  # type: ignore[arg-type]
            target=data.get("target", ""),
        )


@dataclass(frozen=True)
class _IdResolutionMaps:
    """Pre-built lookup structures for resolving ledger tokens to issue IDs."""

    short_id_buckets: dict[str, list[str]]
    short_hex_map: dict[str, str]
    slug_prefix_map: dict[str, str]


def _build_id_resolution_maps(valid_ids: set[str]) -> _IdResolutionMaps:
    short_id_buckets: dict[str, list[str]] = {}
    short_hex_map: dict[str, str] = {}
    slug_prefix_map: dict[str, str] = {}
    ambiguous_slugs: set[str] = set()
    for issue_id in sorted(valid_ids):
        parts = issue_id.rsplit("::", 1)
        short_id = parts[-1]
        slug = parts[0] if len(parts) == 2 else ""
        short_id_buckets.setdefault(short_id, []).append(issue_id)
        if re.fullmatch(r"[0-9a-f]{8,}", short_id):
            existing = short_hex_map.get(short_id)
            if existing is None:
                short_hex_map[short_id] = issue_id
            elif existing != issue_id:
                short_hex_map.pop(short_id, None)
        if not slug:
            continue
        if slug in ambiguous_slugs:
            continue
        if slug in slug_prefix_map:
            slug_prefix_map.pop(slug)
            ambiguous_slugs.add(slug)
            continue
        slug_prefix_map[slug] = issue_id
    return _IdResolutionMaps(
        short_id_buckets=short_id_buckets,
        short_hex_map=short_hex_map,
        slug_prefix_map=slug_prefix_map,
    )


def _clean_ledger_token(raw: str) -> str:
    token = raw.strip().strip("`").strip()
    if token.startswith("[") and token.endswith("]"):
        token = token[1:-1].strip()
    return token


def _extract_ledger_entry(line: str) -> tuple[str, str | None, str | None]:
    """Parse one ledger line into ``(token, decision, target)``."""
    match = re.match(r"-\s*(.+?)\s*->\s*(\w+)\s+[\"']([^\"']+)[\"']", line)
    if match:
        return _clean_ledger_token(match.group(1)), match.group(2).strip().lower(), match.group(3).strip()

    match = re.match(r"-\s*(.+?)\s*->\s*(\w+)\s+(\S+.*)", line)
    if match:
        return (
            _clean_ledger_token(match.group(1)),
            match.group(2).strip().lower(),
            match.group(3).strip().strip("\"'"),
        )

    match = re.match(r"-\s*(.+?)\s*->", line)
    if match:
        return _clean_ledger_token(match.group(1)), None, None

    match = re.match(r"-\s*(.+?)\s*:\s*(\w+)\s+[\"']?([^\"']+?)[\"']?\s*$", line)
    if match:
        return _clean_ledger_token(match.group(1)), match.group(2).strip().lower(), match.group(3).strip()

    match = re.match(r"-\s*([^,]+),\s*(\w+),\s*[\"']?([^\"',]+?)[\"']?\s*$", line)
    if match:
        return _clean_ledger_token(match.group(1)), match.group(2).strip().lower(), match.group(3).strip()

    match = re.match(r"-\s+(\S+)\s*$", line)
    if match:
        token = _clean_ledger_token(match.group(1))
        if token:
            return token, None, None
    return "", None, None


def _resolve_token_to_id(
    token: str,
    valid_ids: set[str],
    maps: _IdResolutionMaps,
    short_id_usage: Counter[str],
) -> str | None:
    if token in valid_ids:
        return token
    bucket = maps.short_id_buckets.get(token)
    if bucket:
        bucket_index = short_id_usage[token]
        resolved = bucket[bucket_index] if bucket_index < len(bucket) else bucket[-1]
        short_id_usage[token] += 1
        return resolved
    for hex_token in re.findall(r"[0-9a-f]{8,}", token):
        resolved = maps.short_hex_map.get(hex_token)
        if resolved:
            return resolved
    return maps.slug_prefix_map.get(token.lower())


_CLUSTER_DECISIONS = frozenset({"cluster"})
_SKIP_DECISIONS = frozenset({"skip", "dismiss", "defer", "drop", "remove"})


def _normalize_decision(raw: str) -> str:
    lower = raw.lower()
    if lower in _CLUSTER_DECISIONS:
        return "cluster"
    if lower in _SKIP_DECISIONS:
        return "permanent_skip"
    return lower


@dataclass
class _LedgerParseResult:
    """Combined output of a single pass over the Coverage Ledger section."""

    hits: Counter[str]
    dispositions: list[ReflectDisposition]
    found_section: bool


def _walk_coverage_ledger(
    report: str,
    valid_ids: set[str],
) -> _LedgerParseResult:
    maps = _build_id_resolution_maps(valid_ids)
    hits: Counter[str] = Counter()
    dispositions: list[ReflectDisposition] = []
    short_id_usage: Counter[str] = Counter()
    in_ledger = False
    found_section = False

    for raw_line in report.splitlines():
        line = raw_line.strip()
        if re.fullmatch(r"##\s+Coverage Ledger", line, re.IGNORECASE):
            in_ledger = True
            found_section = True
            continue
        if in_ledger and re.match(r"##\s+", line):
            break
        if not in_ledger:
            continue

        token, decision, target = _extract_ledger_entry(line)
        if not token:
            continue

        issue_id = _resolve_token_to_id(token, valid_ids, maps, short_id_usage)
        if not issue_id:
            for hex_token in re.findall(r"[0-9a-f]{8,}", line):
                resolved = maps.short_hex_map.get(hex_token)
                if resolved:
                    issue_id = resolved
                    break

        if not issue_id:
            continue
        hits[issue_id] += 1
        if not decision or not target:
            continue
        normalized = _normalize_decision(decision)
        if normalized in {"cluster", "permanent_skip"}:
            dispositions.append(
                ReflectDisposition(
                    issue_id=issue_id,
                    decision=normalized,  # type: ignore[arg-type]
                    target=target,
                )
            )

    return _LedgerParseResult(
        hits=hits,
        dispositions=dispositions,
        found_section=found_section,
    )


def parse_reflect_dispositions(
    report: str,
    valid_ids: set[str],
) -> list[ReflectDisposition]:
    """Parse structured dispositions from the Coverage Ledger section."""
    return _walk_coverage_ledger(report, valid_ids).dispositions


def analyze_reflect_issue_accounting(
    *,
    report: str,
    valid_ids: set[str],
) -> tuple[set[str], list[str], list[str]]:
    """Return cited, missing, and duplicate issue IDs referenced by reflect."""
    result = _walk_coverage_ledger(report, valid_ids)
    if result.found_section and result.hits:
        cited = set(result.hits)
        duplicates = sorted(issue_id for issue_id, count in result.hits.items() if count > 1)
        missing = sorted(valid_ids - cited)
        return cited, missing, duplicates

    maps = _build_id_resolution_maps(valid_ids)
    cited = extract_issue_citations(report, valid_ids)
    for issue_id in valid_ids:
        if issue_id in report:
            cited.add(issue_id)

    short_hits: Counter[str] = Counter()
    for token in re.findall(r"[0-9a-f]{8,}", report):
        resolved = maps.short_hex_map.get(token)
        if resolved:
            cited.add(resolved)
            short_hits[resolved] += 1

    duplicates = sorted(issue_id for issue_id, count in short_hits.items() if count > 1)
    missing = sorted(valid_ids - cited)
    return cited, missing, duplicates


def validate_reflect_accounting(
    *,
    report: str,
    valid_ids: set[str],
) -> tuple[bool, set[str], list[str], list[str]]:
    """Require the reflect report to account for each open issue exactly once."""
    cited, missing, duplicates = analyze_reflect_issue_accounting(
        report=report,
        valid_ids=valid_ids,
    )
    if not missing and not duplicates:
        return True, cited, missing, duplicates

    print(
        colorize(
            "  Reflect report must account for every open review issue exactly once.",
            "red",
        )
    )
    if missing:
        missing_short = ", ".join(issue_id.rsplit("::", 1)[-1] for issue_id in missing[:10])
        print(colorize(f"    Missing: {missing_short}", "yellow"))
    if duplicates:
        duplicate_short = ", ".join(issue_id.rsplit("::", 1)[-1] for issue_id in duplicates[:10])
        print(colorize(f"    Duplicated: {duplicate_short}", "yellow"))
    print(colorize("  Fix the reflect blueprint before running organize.", "dim"))
    if missing:
        print(colorize("  Expected format — include a ## Coverage Ledger section:", "dim"))
        print(colorize('    - <hash> -> cluster "cluster-name"', "dim"))
        print(colorize('    - <hash> -> skip "reason"', "dim"))
        print(colorize("  Also accepted: bare hashes, colon-separated, comma-separated.", "dim"))
    return False, cited, missing, duplicates


__all__ = [
    "ReflectDisposition",
    "analyze_reflect_issue_accounting",
    "parse_reflect_dispositions",
    "validate_reflect_accounting",
]
