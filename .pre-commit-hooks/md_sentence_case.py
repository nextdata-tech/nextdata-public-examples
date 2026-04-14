#!/usr/bin/env python3
"""Normalize Markdown headings to sentence case for docs under components/docs.

This script is intended for use in pre-commit. It updates files in place and
returns a non-zero exit code if any changes are made.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^(```|~~~)")
ALLOWED_PROPER_NOUNS = {
    "amazon",
    "argo",
    "azure",
    "databricks",
    "dataqualitycompliance",
    "docker",
    "dremio",
    "entra",
    "etls",
    "datalake",
    "event",
    "google",
    "helm",
    "jira",
    "jinja",
    "kubernetes",
    "mars",
    "microsoft",
    "nextdata",
    "nextdataos",
    "nextdataos-compatible",
    "okta",
    "openapi",
    "postgresql",
    "python",
    "snowflake",
    "terraform",
    "unity",
}

PROPER_PHRASES = [
    "Azure Data Lake Storage",
    "Azure Event Hubs",
    "Azure Event Hub",
]


def _is_title_word(word: str) -> bool:
    stripped = word.strip("""'"()[]{}.,:;!?/\\|""")
    if not stripped:
        return False
    if stripped.isupper() and len(stripped) > 1:
        return True
    if stripped.lower() in ALLOWED_PROPER_NOUNS:
        return True
    if stripped[0].isupper() and stripped[1:].islower():
        return True
    return False


def _has_letters(token: str) -> bool:
    return any(ch.isalpha() for ch in token)


def _is_title_case_heading(text: str) -> bool:
    words = [w for w in re.split(r"\s+", text) if w]
    if len(words) < 2:
        return False
    for w in words:
        if not _has_letters(w):
            continue
        if not _is_title_word(w):
            return False
    return True


def _sentence_case_segment(segment: str, capitalize_first: bool) -> str:
    parts = re.split(r"(\s+)", segment)
    result: list[str] = []
    for part in parts:
        if not part or part.isspace():
            result.append(part)
            continue
        if not _has_letters(part):
            result.append(part)
            continue
        core = part.strip("""'"()[]{}.,:;!?/\\|""")
        prefix = part[: part.find(core)] if core in part else ""
        suffix = part[part.find(core) + len(core) :] if core in part else ""
        is_first_word = capitalize_first
        if is_first_word:
            capitalize_first = False
        if core.isupper() and len(core) > 1:
            result.append(part)
            continue
        if core.lower() in ALLOWED_PROPER_NOUNS:
            result.append(part)
            continue
        if is_first_word:
            new_core = core[:1].upper() + core[1:].lower()
        else:
            new_core = core.lower()
        result.append(f"{prefix}{new_core}{suffix}")
    return "".join(result)


def _protect_phrases(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    protected = text
    for idx, phrase in enumerate(sorted(PROPER_PHRASES, key=len, reverse=True)):
        token = f"__{idx}__"
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(protected):
            replacements[token] = phrase
            protected = pattern.sub(token, protected)
    return protected, replacements


def _restore_phrases(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for token, phrase in replacements.items():
        restored = restored.replace(token, phrase)
    return restored


def _sentence_case(text: str) -> str:
    segments = text.split("`")
    output: list[str] = []
    capitalize_first = True
    for i, segment in enumerate(segments):
        if i % 2 == 1:
            output.append(segment)
            continue
        protected, replacements = _protect_phrases(segment)
        converted = _sentence_case_segment(protected, capitalize_first)
        restored = _restore_phrases(converted, replacements)
        if converted != segment:
            if segment.strip():
                capitalize_first = False
        output.append(restored)
    return "`".join(output)


def _process_file(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    in_fence = False
    changed = False
    new_lines: list[str] = []
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            new_lines.append(line)
            continue
        if in_fence:
            new_lines.append(line)
            continue
        match = HEADING_RE.match(line)
        if not match:
            new_lines.append(line)
            continue
        hashes, text = match.groups()
        if _is_title_case_heading(text):
            updated = _sentence_case(text)
            if updated != text:
                line = f"{hashes} {updated}\n" if line.endswith("\n") else f"{hashes} {updated}"
                changed = True
        new_lines.append(line)
    if changed:
        path.write_text("".join(new_lines), encoding="utf-8")
    return changed


def main() -> int:
    changed_files: list[Path] = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            continue
        if path.suffix.lower() != ".md":
            continue
        if _process_file(path):
            changed_files.append(path)
    if changed_files:
        for path in changed_files:
            print(f"Updated headings to sentence case: {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
