"""Dataciviclab hub fetcher — analysis READMEs via directory discovery.

Fetches and parses artifacts from the ``dataciviclab`` hub repository:

- ``analisi/`` — directory listing discovers analysis slugs automatically.
- ``analisi/{slug}/README.md`` — analysis page with YAML frontmatter
  containing ``dataset_slug``, ``title``, ``status``, ``topics``,
  and optionally ``discussion`` / ``issue`` numbers.

Using directory listing (instead of a manual registry file) ensures
that analyses are discovered automatically: just create ``analisi/{slug}/``
with a ``README.md`` and ACB will pick it up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..github import GitHubCollector
from ..signals import Analysis

_REPO = "dataciviclab"
_ANALISI_DIR = "analisi"
# Directories under analisi/ that are not analyses
_EXCLUDED_DIRS = {"_template", "registry", "__pycache__"}


@dataclass
class DataciviclabData:
    """Cached dataciviclab artifact bundle."""

    analyses: list[Analysis] = field(default_factory=list)


class DataciviclabFetcher:
    """Fetch dataciviclab artifacts from GitHub raw URLs."""

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._cache: list[Analysis] | None | object = _UNSET

    def fetch(self) -> DataciviclabData:
        """Fetch all dataciviclab artifacts."""
        return DataciviclabData(analyses=self.fetch_analyses())

    def fetch_analyses(self) -> list[Analysis]:
        """Parse analyses from dataciviclab/analisi/.

        Strategy:
        1. List directories under ``analisi/`` via GitHub Contents API
           to discover analysis slugs automatically.
        2. For each analysis slug, fetch
           ``analisi/{slug}/README.md`` and extract YAML frontmatter
           (``dataset_slug``, ``title``, ``status``, ``discussion``, ``issue``).
        3. If the README is not fetchable, infer dataset slug from the
           analysis slug (hyphens → underscores) and use slug as name.

        No manual registry is needed — any directory under ``analisi/``
        with a ``README.md`` is automatically discovered.
        """
        if self._cache is not _UNSET:
            return self._cache  # type: ignore[return-value]

        slugs = self.collector.list_directory(_REPO, _ANALISI_DIR)
        if slugs is None:
            # Fallback: try the old registry approach
            raw_registry = self.collector.get_raw_file(_REPO, f"{_ANALISI_DIR}/registry/active.md")
            if raw_registry is not None:
                registry_entries = _parse_active_md(raw_registry)
                slugs = [entry[0] for entry in registry_entries]
            if not slugs:
                self._cache = []
                return []

        # Filter out non-analysis directories
        slugs = [s for s in slugs if s not in _EXCLUDED_DIRS]
        analyses: list[Analysis] = []

        for slug in slugs:
            readme_path = f"{_ANALISI_DIR}/{slug}/README.md"
            raw_readme = self.collector.get_raw_file(_REPO, readme_path)

            if raw_readme is None:
                # Fallback: infer datasets from slug
                fallback_datasets = _slug_to_datasets(slug)
                analyses.append(
                    Analysis(
                        slug=slug,
                        name=slug,
                        datasets=fallback_datasets,
                        status="active",
                        path=readme_path,
                    )
                )
                continue

            frontmatter = _parse_frontmatter(raw_readme)
            datasets = _resolve_datasets(frontmatter, slug)
            name = frontmatter.get("title", slug)
            status = frontmatter.get("status", "active")
            discussion = _parse_discussion_number(frontmatter)
            issue = _parse_issue_number(frontmatter)

            analyses.append(
                Analysis(
                    slug=slug,
                    name=name,
                    datasets=datasets,
                    discussion=discussion,
                    issue=issue,
                    path=readme_path,
                    status=status,
                )
            )

        self._cache = analyses
        return analyses


def _parse_active_md(raw: str) -> list[tuple[str, int | None, int | None]]:
    """Parse the markdown table from ``active.md``.

    Expected format::

        | filone | discussion | issue | stato |
        |--------|------------|-------|-------|
        | irpef-comunale | [#88](url) | --- | active |
        | civile-flussi | --- | --- | active |

    Returns a list of ``(slug, discussion_number, issue_number)``.
    """
    entries: list[tuple[str, int | None, int | None]] = []
    lines = raw.splitlines()

    # Find the separator line (---|---|---) and start parsing from next line
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\|[-:\s]+\|[-:\s]+\|[-:\s]+\|[-:\s]+\|$", stripped):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped.startswith("|"):
            continue

        cells = [c.strip() for c in stripped.split("|")]
        # Expected: | filone | discussion | issue | stato |
        if len(cells) < 5:
            continue

        slug = cells[1].strip()
        if not slug or slug == "filone":
            continue

        discussion = _extract_issue_number(cells[2])
        issue = _extract_issue_number(cells[3])
        entries.append((slug, discussion, issue))

    return entries


def _extract_issue_number(cell: str) -> int | None:
    """Extract an issue/discussion number from a markdown link cell.

    Handles ``#88``, ``[#88](url)``, ``---``, ``—``, empty.
    """
    cell = cell.strip()
    if not cell or cell in ("---", "—", "-"):
        return None
    # Match [#N](url) or just #N
    m = re.search(r"#(\d+)", cell)
    if m:
        return int(m.group(1))
    return None


def _parse_frontmatter(raw: str) -> dict[str, Any]:
    """Parse YAML-like frontmatter from a markdown file.

    Handles the simple key: value format used in analysis READMEs::

        ---
        title: AIFA Spesa farmaceutica convenzionata 2018-2024
        description: ...
        date: 2026-05-24
        topics: sanita
        status: active
        dataset_slug: aifa_spesa_consumo
        discussion: 242
        issue: 110
        ---

    Returns a dict with frontmatter keys. Does NOT use pyyaml to keep
    the dependency profile light — the format is constrained enough for
    simple line-based parsing.
    """
    result: dict[str, Any] = {}
    lines = raw.splitlines()
    in_frontmatter = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                # End of frontmatter
                break
        if not in_frontmatter:
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        result[key.strip()] = _strip_yaml_quotes(value.strip())
    return result


def _strip_yaml_quotes(value: str) -> str:
    """Strip surrounding YAML quotes (single or double) from a value.

    Handles ``"value"``, ``'value'``, and plain values.
    Does NOT handle escaped quotes inside the value.
    """
    if len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
    return value


def _parse_discussion_number(frontmatter: dict[str, Any]) -> int | None:
    """Extract discussion number from frontmatter ``discussion`` field.

    Accepts a plain integer, a string ``"242"``, or ``None``/missing.
    """
    raw = frontmatter.get("discussion")
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _parse_issue_number(frontmatter: dict[str, Any]) -> int | None:
    """Extract issue number from frontmatter ``issue`` field.

    Accepts a plain integer, a string ``"110"``, or ``None``/missing.
    """
    raw = frontmatter.get("issue")
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _slug_to_datasets(slug: str) -> list[str]:
    """Convert an analysis slug to dataset slug(s) by convention.

    The default convention replaces hyphens with underscores.
    """
    return [slug.replace("-", "_")]


def _resolve_datasets(frontmatter: dict[str, Any], slug: str) -> list[str]:
    """Resolve dataset slugs from an analysis frontmatter.

    Uses the explicit ``dataset_slug`` field if present, otherwise
    falls back to converting the analysis slug (hyphens → underscores).
    """
    explicit = frontmatter.get("dataset_slug")
    if explicit:
        return [explicit]
    return _slug_to_datasets(slug)


class _Unset:
    pass


_UNSET = _Unset()
