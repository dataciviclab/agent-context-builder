"""Dataciviclab hub fetcher — analyses registry, analysis READMEs.

Fetches and parses artifacts from the ``dataciviclab`` hub repository:

- ``analisi/registry/active.md`` — markdown table mapping analysis slugs
  to discussions and issues.
- ``analisi/{slug}/README.md`` — analysis page with YAML frontmatter
  containing ``dataset_slug``, ``title``, ``status``, ``topics``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..github import GitHubCollector
from ..signals import Analysis

_REPO = "dataciviclab"
_REGISTRY_PATH = "analisi/registry/active.md"


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
        1. Fetch ``analisi/registry/active.md`` and parse the markdown
           table to get ``{slug, discussion, issue}``.
        2. For each analysis slug, fetch
           ``analisi/{slug}/README.md`` and extract YAML frontmatter
           (``dataset_slug``, ``title``, ``status``).
        """
        if self._cache is not _UNSET:
            return self._cache  # type: ignore[return-value]

        raw_registry = self.collector.get_raw_file(_REPO, _REGISTRY_PATH)
        if raw_registry is None:
            self._cache = []
            return []

        registry_entries = _parse_active_md(raw_registry)
        analyses: list[Analysis] = []

        for slug, discussion, issue in registry_entries:
            readme_path = f"analisi/{slug}/README.md"
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
                        discussion=discussion,
                        issue=issue,
                        path=readme_path,
                    )
                )
                continue

            frontmatter = _parse_frontmatter(raw_readme)
            datasets = _resolve_datasets(frontmatter, slug)
            name = frontmatter.get("title", slug)
            status = frontmatter.get("status", "active")

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
        result[key.strip()] = value.strip()
    return result


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
