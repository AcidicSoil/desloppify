"""Shared attestation and note validation helpers."""

from __future__ import annotations

import sys

from desloppify.base.output.terminal import colorize

_REQUIRED_ATTESTATION_PHRASES = ("i have actually", "not gaming")
_ATTESTATION_KEYWORD_HINT = ("I have actually", "not gaming")
_MIN_NOTE_LENGTH = 50


def _emit_warning(message: str) -> None:
    """Write resolve preflight warnings to stderr consistently."""
    print(colorize(message, "yellow"), file=sys.stderr)


def _missing_attestation_keywords(attestation: str | None) -> list[str]:
    normalized = " ".join((attestation or "").strip().lower().split())
    return [
        phrase for phrase in _REQUIRED_ATTESTATION_PHRASES if phrase not in normalized
    ]


def validate_attestation(attestation: str | None) -> bool:
    return not _missing_attestation_keywords(attestation)


def show_attestation_requirement(
    label: str,
    attestation: str | None,
    example: str,
) -> None:
    missing = _missing_attestation_keywords(attestation)
    if not attestation:
        _emit_warning(f"{label} requires --attest.")
    elif missing:
        missing_str = ", ".join(f"'{keyword}'" for keyword in missing)
        _emit_warning(
            f"{label} attestation is missing required keyword(s): {missing_str}."
        )
    _emit_warning(
        f"Required keywords: '{_ATTESTATION_KEYWORD_HINT[0]}' and '{_ATTESTATION_KEYWORD_HINT[1]}'."
    )
    print(colorize(f'Example: --attest "{example}"', "dim"), file=sys.stderr)


def validate_note_length(note: str | None) -> bool:
    """Return True if the note meets the minimum length requirement."""
    return note is not None and len(note.strip()) >= _MIN_NOTE_LENGTH


def show_note_length_requirement(note: str | None) -> None:
    """Emit a warning about minimum note length."""
    current = len((note or "").strip())
    _emit_warning(
        f"Note must be at least {_MIN_NOTE_LENGTH} characters (got {current}). "
        f"Describe what you actually did."
    )


__all__ = [
    "_MIN_NOTE_LENGTH",
    "show_attestation_requirement",
    "show_note_length_requirement",
    "validate_attestation",
    "validate_note_length",
]
