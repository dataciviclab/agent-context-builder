"""Local git state collection."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitState:
    """Local git repository state."""

    dirty: bool
    current_branch: str
    branches_ahead: list[str]
    untracked_files: int


class GitLocalCollector:
    """Collect context from local git repositories."""

    def __init__(self, workspace_root: Path):
        """Initialize git collector.

        Args:
            workspace_root: Root path of workspace
        """
        self.workspace_root = Path(workspace_root)

    def get_state(self) -> Optional[GitState]:
        """Get state of local git repository.

        Returns:
            GitState object or None if not a git repo
        """
        try:
            # Check if it's a git repo
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.workspace_root,
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Not a git repo or git not available
            return None

        try:
            # Check if dirty
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True,
            )
            dirty = bool(result.stdout.strip())
            untracked = sum(1 for line in result.stdout.split("\n") if line.startswith("??"))

            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()

            # Get branches ahead
            branches_ahead = self._get_branches_ahead(current_branch)

            return GitState(
                dirty=dirty,
                current_branch=current_branch,
                branches_ahead=branches_ahead,
                untracked_files=untracked,
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to get git state: {e}")
            return None

    def _get_branches_ahead(self, current_branch: str) -> list[str]:
        """Get local branches that are ahead of remote.

        Args:
            current_branch: Current branch name

        Returns:
            List of branch names
        """
        try:
            # Get all branches with their tracking info
            result = subprocess.run(
                ["git", "branch", "-vv"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True,
            )

            ahead_branches = []
            for line in result.stdout.split("\n"):
                if "ahead" in line:
                    # Extract branch name (first word after *)
                    parts = line.split()
                    if len(parts) > 1:
                        branch = parts[1].lstrip("*").strip()
                        ahead_branches.append(branch)
            return ahead_branches
        except subprocess.CalledProcessError:
            return []
