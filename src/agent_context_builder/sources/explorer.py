"""Data-explorer fetcher — public dataset pages + editorial themes.

The public analysis/dataset pages live in ``data-explorer``:

- ``src/dataset/*.md`` — dataset pages with YAML frontmatter
  (``title``, ``description``, ``dataset_slug``, ``source``, ``period``,
  ``data_driven``). Discovered via file listing (no manual registry).
- ``catalog/themes.json`` — editorial themes mapping ``categories[]`` to
  domain slugs. Single source of truth for the Lab navigation domains.

Replaces the removed ``dataciviclab/analisi/`` directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..github import GitHubCollector
from ..signals import Analysis

_EXPLORER_REPO = "data-explorer"
_DATASET_DIR = "src/dataset"
_THEMES_PATH = "catalog/themes.json"
_PAGE_SUFFIX = ".md"


@dataclass
class ExplorerTheme:
    """Editorial theme from data-explorer catalog/themes.json."""

    slug: str
    name: str
    description: str = ""
    icon: str = ""
    categories: list[str] = field(default_factory=list)


@dataclass
class ExplorerData:
    """Cached data-explorer artifact bundle."""

    analyses: list[Analysis] = field(default_factory=list)
    themes: list[ExplorerTheme] = field(default_factory=list)


class ExplorerFetcher:
    """Fetch data-explorer pages and themes via GitHub raw/contents."""

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._analyses: list[Analysis] | None = None
        self._themes: list[ExplorerTheme] | None = None

    def fetch(self) -> ExplorerData:
        return ExplorerData(
            analyses=self.fetch_analyses(),
            themes=self.fetch_themes(),
        )

    def fetch_analyses(self) -> list[Analysis]:
        """Parse dataset pages from ``data-explorer/src/dataset/*.md``.

        Each page becomes an :class:`Analysis` linked to its dataset via
        frontmatter ``dataset_slug``. Pages without a slug are skipped.
        """
        if self._analyses is not None:
            return self._analyses

        files = self.collector.list_files(_EXPLORER_REPO, _DATASET_DIR, suffix=_PAGE_SUFFIX)
        analyses: list[Analysis] = []
        if files:
            for filename in files:
                if filename.startswith("TEMPLATE"):
                    continue
                slug = (
                    filename[: -len(_PAGE_SUFFIX)] if filename.endswith(_PAGE_SUFFIX) else filename
                )
                raw = self.collector.get_raw_file(_EXPLORER_REPO, f"{_DATASET_DIR}/{filename}")
                if raw is None:
                    analyses.append(
                        Analysis(
                            slug=slug,
                            name=slug,
                            datasets=[slug.replace("-", "_")],
                            path=f"{_DATASET_DIR}/{filename}",
                            status="published",
                        )
                    )
                    continue

                frontmatter = _parse_frontmatter(raw)
                datasets = _resolve_datasets(frontmatter, slug)
                if not datasets:
                    continue
                name = frontmatter.get("title") or slug
                status = _resolve_status(frontmatter)
                analyses.append(
                    Analysis(
                        slug=slug,
                        name=name,
                        datasets=datasets,
                        path=f"{_DATASET_DIR}/{filename}",
                        status=status,
                        description=frontmatter.get("description", ""),
                        source=frontmatter.get("source", ""),
                        period=frontmatter.get("period"),
                    )
                )

        self._analyses = analyses
        return analyses

    def fetch_themes(self) -> list[ExplorerTheme]:
        """Parse ``catalog/themes.json`` from data-explorer."""
        if self._themes is not None:
            return self._themes

        raw = self.collector.get_raw_file(_EXPLORER_REPO, _THEMES_PATH)
        themes = _parse_themes(raw) if raw else []
        self._themes = themes
        return themes


def _parse_frontmatter(raw: str) -> dict[str, Any]:
    """Parse simple YAML-like frontmatter (key: value per line)."""
    result: dict[str, Any] = {}
    lines = raw.splitlines()
    in_frontmatter = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if not in_frontmatter or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        result[key.strip()] = _strip_yaml_quotes(value.strip())
    return result


def _strip_yaml_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _resolve_datasets(frontmatter: dict[str, Any], slug: str) -> list[str]:
    explicit = frontmatter.get("dataset_slug")
    if explicit:
        return [str(explicit)]
    return [slug.replace("-", "_")]


def _resolve_status(frontmatter: dict[str, Any]) -> str:
    status = frontmatter.get("status")
    if status:
        return str(status)
    data_driven = str(frontmatter.get("data_driven", "")).lower()
    return "published" if data_driven == "true" else "active"


def _parse_themes(raw: str) -> list[ExplorerTheme]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    themes_raw = data.get("temi") or data.get("themes") or []
    themes: list[ExplorerTheme] = []
    for t in themes_raw:
        if not isinstance(t, dict) or not t.get("slug"):
            continue
        themes.append(
            ExplorerTheme(
                slug=str(t["slug"]),
                name=str(t.get("name") or t["slug"]),
                description=str(t.get("description") or ""),
                icon=str(t.get("icon") or ""),
                categories=[str(c) for c in (t.get("categories") or [])],
            )
        )
    return themes


# Re-export legacy name used by older imports/tests.
DataciviclabFetcher = ExplorerFetcher
