"""Review parser builder extracted from parser_groups_admin."""

from __future__ import annotations

import argparse

from .parser_groups_admin_review_options import (
    _add_batch_execution_options,
    _add_core_options,
    _add_external_review_options,
    _add_postprocessing_options,
    _add_trust_options,
)


def _add_review_parser(sub) -> None:
    p_review = sub.add_parser(
        "review",
        help="Prepare or import holistic subjective review",
        description="Run holistic subjective reviews using LLM-based analysis.",
        epilog="""\
examples:
  desloppify review --prepare
  desloppify review --run-batches --runner codex --parallel --scan-after-import
  desloppify review --external-start --external-runner claude
  desloppify review --external-submit --session-id <id> --import issues.json
  desloppify review --merge --similarity 0.8""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    _add_core_options(p_review)
    _add_external_review_options(p_review)
    _add_batch_execution_options(p_review)
    _add_trust_options(p_review)
    _add_postprocessing_options(p_review)


__all__ = ["_add_review_parser"]
