"""Command-line interface for agent-context-builder."""

import json
from pathlib import Path

import click

from .config import load_config
from .github import GitHubCollector
from .git_local import GitLocalCollector
from .render import Renderer


@click.group()
@click.version_option()
def cli():
    """Agent context builder: autonomous context generation for agents."""
    pass


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to YAML config file",
)
@click.option(
    "--out",
    type=click.Path(),
    required=True,
    help="Output directory for generated artifacts",
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    default=None,
    help="GitHub API token (optional)",
)
@click.option(
    "--workspace-root",
    envvar="DATACIVICLAB_WORKSPACE",
    default=None,
    help="Local workspace root for git state collection (optional; overrides config)",
)
@click.option(
    "--generated-at",
    default=None,
    help="Fixed timestamp for deterministic output (ISO format, for testing)",
)
def build(config: str, out: str, github_token: str | None, workspace_root: str | None, generated_at: str | None):
    """Build context artifacts.

    Generates session_bootstrap.md, workspace_triage.json, and topic_index.json.
    Local git state is collected only when --workspace-root (or DATACIVICLAB_WORKSPACE) is set.
    """
    config_path = Path(config)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Loading config from {config_path}")
    cfg = load_config(config_path)

    # Resolve workspace root: CLI/env overrides config; None = GitHub-only mode
    resolved_root = Path(workspace_root) if workspace_root else cfg.workspace_root
    if resolved_root:
        click.echo(f"Local workspace: {resolved_root}")
    else:
        click.echo("Local workspace: not configured (GitHub-only mode)")

    click.echo(f"Initializing collectors")
    github_collector = GitHubCollector(cfg.github_org, token=github_token)
    git_collector = GitLocalCollector(resolved_root)

    click.echo(f"Creating renderer")
    renderer = Renderer(
        cfg, github_collector, git_collector, fixed_timestamp=generated_at
    )

    # Generate session_bootstrap.md
    click.echo("Generating session_bootstrap.md")
    bootstrap = renderer.render_session_bootstrap()
    bootstrap_path = out_dir / "session_bootstrap.md"
    bootstrap_path.write_text(bootstrap)
    click.echo(f"  → {bootstrap_path} ({len(bootstrap.split(chr(10)))} lines)")

    # Generate workspace_triage.json
    click.echo("Generating workspace_triage.json")
    triage = renderer.render_workspace_triage()
    triage_path = out_dir / "workspace_triage.json"
    triage_path.write_text(json.dumps(triage, indent=2))
    click.echo(f"  → {triage_path}")

    # Generate topic_index.json
    click.echo("Generating topic_index.json")
    topics = renderer.render_topic_index()
    topics_path = out_dir / "topic_index.json"
    topics_path.write_text(json.dumps(topics, indent=2))
    click.echo(f"  → {topics_path}")

    click.echo(f"\n✓ Build complete: {len(list(out_dir.glob('*')))} artifacts")


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
