"""CLI entry point for NHQD.

Provides command-line interface using click for generating
Nablarch handler queue configurations from YAML requirements.
"""

from pathlib import Path

import click

from nhqd import __version__


@click.group()
@click.version_option(version=__version__, prog_name="nhqd")
def main() -> None:
    """Nablarch Handler Queue Designer - Automated handler queue configuration tool."""


@main.command()
@click.argument("requirements_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Output directory for generated files.",
)
@click.option(
    "-f", "--format",
    "output_format",
    type=click.Choice(["xml", "markdown", "both"]),
    default="both",
    help="Output format.",
)
def generate(requirements_file: Path, output_dir: Path, output_format: str) -> None:
    """Generate handler queue configuration from a requirements YAML file."""
    raise NotImplementedError("generate command is not yet implemented")


@main.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
def validate(config_file: Path) -> None:
    """Validate an existing handler queue configuration against constraints."""
    raise NotImplementedError("validate command is not yet implemented")


@main.command()
def list_handlers() -> None:
    """List all available Nablarch handlers in the catalog."""
    raise NotImplementedError("list-handlers command is not yet implemented")


if __name__ == "__main__":
    main()
