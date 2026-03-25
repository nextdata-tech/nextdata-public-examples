#!/usr/bin/env python3
"""Validate relative Markdown links and anchors under components/docs.

Checks that referenced files exist and that section anchors resolve to either
Markdown headers or explicit HTML anchors using id attributes only.
"""

from __future__ import annotations

import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HTML_ANCHOR_RE = re.compile(r"<a\s+id=[\"']([^\"']+)[\"']", re.IGNORECASE)
HTML_HREF_RE = re.compile(r"<a\s+[^>]*href=[\"']([^\"']+)[\"']", re.IGNORECASE)
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MD_AUTOLINK_RE = re.compile(r"<([^>]+)>")

EXCLUDED_FILES = {
    # Paths are relative to data_products/
}

EXCLUDED_LINKS = {
}

EXCLUDED_EXTERNAL_PREFIXES = {
}

EXCLUDED_INTERNAL_PREFIXES = {
}


def _is_excluded_external_prefix(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in EXCLUDED_EXTERNAL_PREFIXES)


def _match_excluded_internal_prefix(link: str) -> str | None:
    trimmed = link
    if trimmed.startswith("./"):
        trimmed = trimmed[2:]
    if trimmed.startswith("../"):
        trimmed = trimmed.lstrip("./")
    for prefix in EXCLUDED_INTERNAL_PREFIXES:
        if trimmed.startswith(prefix) or trimmed.lstrip("/").startswith(
            prefix.lstrip("/")
        ):
            return prefix
    return None


@dataclass(frozen=True)
class LinkTarget:
    file_path: Path
    anchor: str | None
    line_number: int
    raw_link: str


@dataclass(frozen=True)
class ExternalLink:
    url: str
    line_number: int
    raw_link: str


def _slugify(text: str) -> str:
    # Remove inline code and HTML tags.
    text = "".join(text.split("`"))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def _collect_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    text = path.read_text(encoding="utf-8")
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            heading = match.group(2)
            slug = _slugify(heading)
            if slug:
                anchors.add(slug)
        for anchor_match in HTML_ANCHOR_RE.finditer(line):
            anchor = anchor_match.group(1).strip()
            if anchor:
                anchors.add(anchor)
                anchors.add(anchor.lower())
    return anchors


def _normalize_link(raw_link: str) -> str:
    link = raw_link.strip()
    if link.startswith("<") and link.endswith(">"):
        link = link[1:-1].strip()
    if " " in link:
        link = link.split(" ", 1)[0].strip()
    docsify_route = False
    if link.startswith("/#/"):
        link = f"/{link[3:]}"
        docsify_route = True
    elif link.startswith("#/"):
        link = f"/{link[2:]}"
        docsify_route = True
    if docsify_route and link.startswith("/"):
        path_query, hash_fragment = (link.split("#", 1) + [""])[:2]
        path_part, query_part = (path_query.split("?", 1) + [""])[:2]
        anchor = hash_fragment
        if query_part.startswith("id="):
            anchor = query_part[3:]
            query_part = ""
        if path_part and not Path(path_part).suffix:
            path_part = f"{path_part}.md"
        rebuilt = path_part
        if query_part:
            rebuilt = f"{rebuilt}?{query_part}"
        if anchor:
            rebuilt = f"{rebuilt}#{anchor}"
        link = rebuilt
    return link


def _is_relative_internal(link: str) -> bool:
    lowered = link.lower()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
        return False
    if link.startswith("//"):
        return False
    return True


def _is_external_url(link: str) -> bool:
    lowered = link.lower()
    return lowered.startswith(("http://", "https://"))


def _resolve_path(base: Path, raw_path: str) -> Path | None:
    candidate = (base / raw_path).resolve()
    if candidate.exists() and candidate.is_file():
        return candidate
    if candidate.exists() and candidate.is_dir():
        readme = candidate / "README.md"
        if readme.exists():
            return readme
    if candidate.suffix == "":
        md_candidate = candidate.with_suffix(".md")
        if md_candidate.exists():
            return md_candidate
        readme = candidate / "README.md"
        if readme.exists():
            return readme
    return None

def _is_probable_link(link: str) -> bool:
    if link.startswith("#"):
        return True
    if link.startswith(("./", "../")):
        return True
    if "/" in link or "." in link:
        return True
    return False


def _comment_spans(line: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        open_idx = line.find("<!--", start)
        if open_idx == -1:
            break
        close_idx = line.find("-->", open_idx + 4)
        if close_idx == -1:
            break
        spans.append((open_idx, close_idx + 3))
        start = close_idx + 3
    return spans


def _is_commented(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    for span_start, span_end in spans:
        if span_start <= start and end <= span_end:
            return True
    return False


def _extract_link_targets(
    path: Path, docs_root: Path, check_external: bool
) -> tuple[list[LinkTarget], list[ExternalLink], set[str]]:
    text = path.read_text(encoding="utf-8")
    in_fence = False
    targets: list[LinkTarget] = []
    externals: list[ExternalLink] = []
    base_dir = path.parent
    skipped_internal_prefixes: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        comment_spans = _comment_spans(line)
        for match in MD_LINK_RE.finditer(line):
            if _is_commented(comment_spans, match.start(), match.end()):
                continue
            raw_link = match.group(1)
            link = _normalize_link(raw_link)
            if link in EXCLUDED_LINKS:
                continue
            if link.startswith("#") and not link.startswith("#/"):
                targets.append(
                    LinkTarget(path, link[1:] or None, line_number, raw_link)
                )
                continue
            if _is_external_url(link):
                if check_external:
                    externals.append(ExternalLink(link, line_number, raw_link))
                continue
            if not _is_relative_internal(link):
                continue
            matched_prefix = _match_excluded_internal_prefix(link)
            if matched_prefix:
                skipped_internal_prefixes.add(matched_prefix)
                continue
            file_part, anchor = _split_anchor(link)
            if file_part.startswith("/"):
                resolved = _resolve_path(docs_root, file_part.lstrip("/"))
            else:
                resolved = _resolve_path(base_dir, file_part)
            if resolved:
                targets.append(LinkTarget(resolved, anchor, line_number, raw_link))
            else:
                targets.append(
                    LinkTarget(Path(file_part), anchor, line_number, raw_link)
                )
        for match in HTML_HREF_RE.finditer(line):
            if _is_commented(comment_spans, match.start(), match.end()):
                continue
            raw_link = match.group(1)
            link = _normalize_link(raw_link)
            if link in EXCLUDED_LINKS:
                continue
            if link.startswith("#") and not link.startswith("#/"):
                targets.append(
                    LinkTarget(path, link[1:] or None, line_number, raw_link)
                )
                continue
            if _is_external_url(link):
                if check_external:
                    externals.append(ExternalLink(link, line_number, raw_link))
                continue
            if not _is_relative_internal(link):
                continue
            matched_prefix = _match_excluded_internal_prefix(link)
            if matched_prefix:
                skipped_internal_prefixes.add(matched_prefix)
                continue
            file_part, anchor = _split_anchor(link)
            if file_part.startswith("/"):
                resolved = _resolve_path(docs_root, file_part.lstrip("/"))
            else:
                resolved = _resolve_path(base_dir, file_part)
            if resolved:
                targets.append(LinkTarget(resolved, anchor, line_number, raw_link))
            else:
                targets.append(
                    LinkTarget(Path(file_part), anchor, line_number, raw_link)
                )
        for match in MD_AUTOLINK_RE.finditer(line):
            if _is_commented(comment_spans, match.start(), match.end()):
                continue
            raw_link = match.group(1)
            if raw_link.lstrip().startswith("!--"):
                continue
            if " " in raw_link:
                continue
            trimmed = raw_link.strip()
            if trimmed.startswith("/") and trimmed[1:].isalpha():
                continue
            link = _normalize_link(raw_link)
            if link in EXCLUDED_LINKS:
                continue
            if not _is_probable_link(link):
                continue
            if link.startswith("#") and not link.startswith("#/"):
                targets.append(
                    LinkTarget(path, link[1:] or None, line_number, raw_link)
                )
                continue
            if _is_external_url(link):
                if check_external:
                    externals.append(ExternalLink(link, line_number, raw_link))
                continue
            if not _is_relative_internal(link):
                continue
            matched_prefix = _match_excluded_internal_prefix(link)
            if matched_prefix:
                skipped_internal_prefixes.add(matched_prefix)
                continue
            file_part, anchor = _split_anchor(link)
            if file_part.startswith("/"):
                resolved = _resolve_path(docs_root, file_part.lstrip("/"))
            else:
                resolved = _resolve_path(base_dir, file_part)
            if resolved:
                targets.append(LinkTarget(resolved, anchor, line_number, raw_link))
            else:
                targets.append(
                    LinkTarget(Path(file_part), anchor, line_number, raw_link)
                )
    return targets, externals, skipped_internal_prefixes


def _split_anchor(link: str) -> tuple[str, str | None]:
    if "#" not in link:
        return link, None
    path, anchor = link.split("#", 1)
    return path, anchor or None


def _anchor_exists(anchor: str, anchors: set[str]) -> bool:
    if anchor in anchors:
        return True
    if anchor.lower() in anchors:
        return True
    return False


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return False
    return relative in EXCLUDED_FILES


def _collect_docs_files(root: Path, requested: list[Path] | None = None) -> list[Path]:
    if not requested:
        return sorted(
            path for path in root.rglob("*.md") if not _is_excluded(path, root)
        )
    files: list[Path] = []
    for item in requested:
        if item.is_dir():
            files.extend(
                sorted(
                    path for path in item.rglob("*.md") if not _is_excluded(path, root)
                )
            )
        elif (
            item.is_file()
            and item.suffix.lower() == ".md"
            and not _is_excluded(item, root)
        ):
            files.append(item)
    return files


def _strip_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _redirects_to_root(original_url: str, final_url: str) -> bool:
    original_path = urlsplit(original_url).path.rstrip("/")
    final_path = urlsplit(final_url).path.rstrip("/")
    if original_path in {"", "/"}:
        return False
    return final_path in {"", "/"}


def _check_external_url(url: str, timeout: float = 5.0) -> str | None:
    target = _strip_fragment(url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        request = Request(target, method="HEAD", headers=headers)
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if _redirects_to_root(target, final_url):
                return f"redirected to {final_url}"
            return None
    except HTTPError as exc:
        if exc.code not in {403, 404, 405}:
            return f"{exc.code} {exc.reason}"
    except URLError as exc:
        return str(exc.reason)

    try:
        request = Request(target, method="GET", headers=headers)
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if _redirects_to_root(target, final_url):
                return f"redirected to {final_url}"
            return None
    except HTTPError as exc:
        return f"{exc.code} {exc.reason}"
    except URLError as exc:
        return str(exc.reason)


def _validate_links(
    root: Path,
    requested: list[Path] | None = None,
    check_external: bool = False,
    repo_root: Path | None = None,
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    anchors_map: dict[Path, set[str]] = {}
    external_cache: dict[str, str | None] = {}
    skipped_internal_prefixes: set[str] = set()
    all_docs = _collect_docs_files(root)
    for doc_path in all_docs:
        anchors_map[doc_path.resolve()] = _collect_anchors(doc_path)

    for doc_path in _collect_docs_files(root, requested):
        link_targets, external_targets, skipped_prefixes = _extract_link_targets(
            doc_path, root, check_external
        )
        skipped_internal_prefixes.update(skipped_prefixes)
        for target in link_targets:
            if not target.file_path.exists():
                errors.append(
                    f"{doc_path}:{target.line_number}: missing file {target.file_path} (link: {target.raw_link})"
                )
                continue
            if target.anchor:
                resolved_target = target.file_path.resolve()
                if resolved_target not in anchors_map:
                    anchors_map[resolved_target] = _collect_anchors(resolved_target)
                anchors = anchors_map.get(resolved_target, set())
                if not _anchor_exists(target.anchor, anchors):
                    errors.append(
                        f"{doc_path}:{target.line_number}: missing anchor #{target.anchor} "
                        f"in {target.file_path} (link: {target.raw_link})"
                    )
        for external in external_targets:
            if _is_excluded_external_prefix(external.url):
                continue
            if external.url not in external_cache:
                external_cache[external.url] = _check_external_url(external.url)
            error = external_cache[external.url]
            if error:
                errors.append(
                    f"{doc_path}:{external.line_number}: external link failed ({error}) "
                    f"(link: {external.raw_link})"
                )
    return errors, skipped_internal_prefixes


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "components" / "docs"
        root.mkdir(parents=True, exist_ok=True)
        a = root / "a.md"
        b = root / "b.md"
        c = root / "c.md"
        a.write_text(
            "# Alpha Heading\n\nSee [Beta](b.md#beta-heading).\n"
            '<a href="b.md#custom-anchor">Beta HTML</a>\n',
            encoding="utf-8",
        )
        b.write_text('# Beta Heading\n\n<a id="custom-anchor"></a>\n', encoding="utf-8")
        c.write_text(
            "# Runtime data product API\n\n"
            "[Docsify](#/c?id=runtime-data-product-api)\n",
            encoding="utf-8",
        )
        errors, _skipped = _validate_links(root)
        if errors:
            for error in errors:
                print(error)
            return 1
    return 0


def main() -> int:
    ignored_flags = {"--self-test", "--warn", "--check-external-links"}
    args = [arg for arg in sys.argv[1:] if arg not in ignored_flags]
    warn_only = "--warn" in sys.argv[1:]
    check_external = "--check-external-links" in sys.argv[1:]
    if "--self-test" in sys.argv[1:]:
        return _self_test()
    repo_root = Path(__file__).resolve().parents[1]
    docs_root = repo_root / "data_products"
    if not docs_root.exists():
        print(f"{docs_root} not found", file=sys.stderr)
        return 2
    requested = [Path(arg).resolve() for arg in args] if args else None
    errors, skipped_internal_prefixes = _validate_links(
        docs_root,
        requested,
        check_external=check_external,
        repo_root=repo_root,
    )
    if errors:
        for error in errors:
            if warn_only:
                print(f"warning: {error}", file=sys.stderr)
            else:
                print(error)
        if warn_only:
            sys.stderr.flush()
            return 0
        return 1
    if warn_only and skipped_internal_prefixes:
        skipped = ", ".join(sorted(skipped_internal_prefixes))
        print(
            f"warning: internal link checks skip prefixes: {skipped}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
