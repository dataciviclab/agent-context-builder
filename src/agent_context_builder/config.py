"""Configuration models for agent-context-builder."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Topic(BaseModel):
    """Topic configuration."""

    name: str = Field(..., description="Topic name")
    repos: list[str] = Field(default_factory=list, description="Relevant repos")
    paths: list[str] = Field(default_factory=list, description="Relevant file paths")


class Config(BaseModel):
    """Root configuration for agent-context-builder."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace_root: Path = Field(..., description="Root of workspace")
    github_org: str = Field(..., description="GitHub organization")
    repos: list[str] = Field(
        default_factory=list, description="Primary repos to monitor"
    )
    topics: dict[str, Topic] = Field(default_factory=dict, description="Topic index")

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML config file

        Returns:
            Loaded Config instance
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        # Parse topics
        topics_raw = data.pop("topics", {})
        topics = {}
        for topic_name, topic_data in topics_raw.items():
            topics[topic_name] = Topic(name=topic_name, **topic_data)

        return cls(topics=topics, **data)


def load_config(config_path: Path) -> Config:
    """Load configuration from file.

    Args:
        config_path: Path to config file (YAML or JSON)

    Returns:
        Loaded configuration

    Raises:
        FileNotFoundError: If config file does not exist
        ValueError: If config file format is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if config_path.suffix == ".yml" or config_path.suffix == ".yaml":
        return Config.from_yaml(config_path)
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")
