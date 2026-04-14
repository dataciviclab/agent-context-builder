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
    help="GitHub API token (optional, uses gh CLI fallback)",
)
def build(config: str, out: str, github_token: str | None):
    """Build context artifacts.

    Generates session_bootstrap.md, workspace_triage.json, and topic_index.json.
    """
    config_path = Path(config)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Loading config from {config_path}")
    cfg = load_config(config_path)

    click.echo(f"Initializing collectors")
    github_collector = GitHubCollector(cfg.github_org, token=github_token)
    git_collector = GitLocalCollector(cfg.workspace_root)

    click.echo(f"Creating renderer")
    renderer = Renderer(cfg, github_collector, git_collector)

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
