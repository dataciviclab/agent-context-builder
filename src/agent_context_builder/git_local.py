"""Local git state collection."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitState:
    """Local git repository state."""

    available: bool
    reason: str | None  # "path_not_found", "not_git_repo", "git_error" when available=False
    dirty: bool | None
    current_branch: str | None
    branches_ahead: list[str] = field(default_factory=list)
    untracked_files: int = 0


class GitLocalCollector:
    """Collect context from local git repositories."""

    def __init__(self, workspace_root: Path | None):
        """Initialize git collector.

        Args:
            workspace_root: Root path of workspace, or None to disable local collection.
        """
        self.workspace_root = Path(workspace_root) if workspace_root else None

    def get_state(self) -> GitState:
        """Get state of workspace root git repository.

        Returns:
            GitState object (available=False if local collection disabled or not a git repo)
        """
        if self.workspace_root is None:
            return GitState(available=False, reason="local_disabled", dirty=None, current_branch=None)
        return self._get_repo_state(self.workspace_root)

    def get_repos_state(self, repos: list[str]) -> dict[str, GitState]:
        """Get state for each configured repo under workspace.

        Args:
            repos: List of repo names under workspace_root

        Returns:
            Dict mapping repo name to GitState (always present, check available field)
        """
        if self.workspace_root is None:
            return {
                repo: GitState(available=False, reason="local_disabled", dirty=None, current_branch=None)
                for repo in repos
            }
        states = {}
        for repo in repos:
            repo_path = self.workspace_root / repo
            states[repo] = self._get_repo_state(repo_path)
        return states

    def _get_repo_state(self, repo_path: Path) -> GitState:
        """Get state of a specific git repository.

        Args:
            repo_path: Path to repo directory

        Returns:
            GitState — always returned; check available and reason fields
        """
        if not repo_path.exists():
            return GitState(available=False, reason="path_not_found", dirty=None, current_branch=None)

        try:
            # Check if it's a git repo
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return GitState(available=False, reason="not_git_repo", dirty=None, current_branch=None)
        except FileNotFoundError:
            return GitState(available=False, reason="git_error", dirty=None, current_branch=None)

        try:
            # Check if dirty
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            dirty = bool(result.stdout.strip())
            untracked = sum(1 for line in result.stdout.split("\n") if line.startswith("??"))

            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()

            # Get branches ahead
            branches_ahead = self._get_branches_ahead(repo_path)

            return GitState(
                available=True,
                reason=None,
                dirty=dirty,
                current_branch=current_branch,
                branches_ahead=branches_ahead,
                untracked_files=untracked,
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to get git state for {repo_path}: {e}")
            return GitState(available=False, reason="git_error", dirty=None, current_branch=None)

    def _get_branches_ahead(self, repo_path: Path) -> list[str]:
        """Get local branches that are ahead of remote.

        Args:
            repo_path: Path to repo directory

        Returns:
            List of branch names ahead of their remote tracking branch
        """
        try:
            # Get all branches with their tracking info
            result = subprocess.run(
                ["git", "branch", "-vv"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            ahead_branches = []
            for line in result.stdout.split("\n"):
                if "ahead" not in line:
                    continue
                # git branch -vv output:
                #   * main   abc1234 [origin/main: ahead 1] msg   (current branch)
                #     feat   def5678 [origin/feat: ahead 2] msg   (other branch)
                # parts[0] is '*' for current branch, branch name otherwise
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "*":
                    branch = parts[1] if len(parts) > 1 else ""
                else:
                    branch = parts[0]
                if branch:
                    ahead_branches.append(branch)
            return ahead_branches
        except subprocess.CalledProcessError:
            return []
