"""Risoluzione dei repo nel workspace locale.

Il workspace del Lab è multi-repo con i repo dati raggruppati per dominio
(``diritto-legge/open-politica``, ``pubblica-amministrazione/open-siope``):
il nome del repo è la chiave (config ACB, registry), il path no. Qui l'unica
funzione che traduce nome → directory, usata dai collector locali.
"""

from __future__ import annotations

from pathlib import Path


def resolve_repo_path(workspace_root: Path | str | None, repo: str) -> Path | None:
    """Path del repo nel workspace (diretto o annidato ``{dominio}/{repo}``).

    Args:
        workspace_root: Root del workspace (None = modalità GitHub-only).
        repo: Nome del repo (es. ``open-politica``).

    Returns:
        Directory del repo se esiste, altrimenti None.
    """
    if workspace_root is None:
        return None
    root = Path(workspace_root)
    direct = root / repo
    if direct.is_dir():
        return direct
    if not root.is_dir():
        return None
    for parent in sorted(p for p in root.iterdir() if p.is_dir()):
        if parent.name.startswith("."):
            continue
        nested = parent / repo
        if nested.is_dir():
            return nested
    return None


__all__ = ["resolve_repo_path"]
