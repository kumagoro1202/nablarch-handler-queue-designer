"""CLI entry point for NHQD.

Provides command-line interface using click for generating
Nablarch handler queue configurations from YAML requirements.
"""

from pathlib import Path

import click
import yaml

from nhqd import __version__
from nhqd.engine.constraint_validator import ConstraintValidator
from nhqd.engine.rule_engine import RuleEngine
from nhqd.generator.xml_generator import XmlGenerator
from nhqd.parser.yaml_parser import YamlRequirementsParser


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
    click.echo(f"Generating handler queue from {requirements_file}...")

    # Parse requirements YAML
    parser = YamlRequirementsParser()
    requirements = parser.parse_file(requirements_file)

    click.echo(f"Project: {requirements.name} ({requirements.app_type})")

    # Generate handler queue using rule engine
    engine = RuleEngine()
    result = engine.generate(requirements)

    click.echo(f"Generated {len(result.handlers)} handlers")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate outputs based on format
    if output_format in ("xml", "both"):
        # Generate XML
        xml_generator = XmlGenerator()
        xml_string = xml_generator.generate_string(result)

        xml_output = output_dir / "handler-queue-config.xml"
        with open(xml_output, "w", encoding="utf-8") as f:
            f.write(xml_string)

        click.echo(f"XML output: {xml_output}")

    if output_format in ("markdown", "both"):
        # Generate Markdown documentation
        md_output = output_dir / "handler-queue-documentation.md"
        with open(md_output, "w", encoding="utf-8") as f:
            f.write(f"# {requirements.name} - Handler Queue Configuration\n\n")
            f.write(f"**Application Type**: {requirements.app_type}\n\n")
            f.write("## Handler Queue\n\n")
            for i, handler in enumerate(result.handlers, 1):
                f.write(f"{i}. **{handler.class_name}**\n")
                f.write(f"   - Full Class: `{handler.full_class_path}`\n")
                if handler.description:
                    f.write(f"   - Description: {handler.description}\n")
                f.write("\n")

            if result.warnings:
                f.write("## Warnings\n\n")
                for warning in result.warnings:
                    f.write(f"- {warning}\n")

        click.echo(f"Markdown output: {md_output}")

    click.echo("Generation complete!")


@main.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
def validate(config_file: Path) -> None:
    """Validate an existing handler queue configuration against constraints."""
    click.echo(f"Validating handler queue configuration: {config_file}")

    # Note: Full XML parsing implementation would require lxml parsing
    # For MVP, we provide a placeholder that acknowledges the file exists
    # and would perform validation if XML parsing was fully implemented

    if not config_file.exists():
        click.echo(f"Error: Configuration file not found: {config_file}", err=True)
        raise click.Abort()

    click.echo("Validation complete - XML parsing not yet fully implemented")
    click.echo("Future implementation will parse XML and validate against C-01 through C-10 constraints")


@main.command()
def list_handlers() -> None:
    """List all available Nablarch handlers in the catalog."""
    # Load handler catalog
    knowledge_base_path = Path(__file__).parent / "knowledge"
    catalog_path = knowledge_base_path / "handler_catalog.yaml"

    if not catalog_path.exists():
        click.echo(f"Error: Handler catalog not found: {catalog_path}", err=True)
        raise click.Abort()

    with open(catalog_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    handlers = data.get("handlers", [])

    click.echo(f"Nablarch Handler Catalog ({len(handlers)} handlers)\n")
    click.echo("=" * 80)

    # Group handlers by category
    handlers_by_category: dict[str, list[dict]] = {}
    for handler in handlers:
        category = handler.get("category", "other")
        if category not in handlers_by_category:
            handlers_by_category[category] = []
        handlers_by_category[category].append(handler)

    # Display by category
    for category, cat_handlers in sorted(handlers_by_category.items()):
        click.echo(f"\n{category.upper()} ({len(cat_handlers)} handlers)")
        click.echo("-" * 80)

        for handler in cat_handlers:
            name = handler.get("name", "Unknown")
            full_class = handler.get("full_class", "")
            description = handler.get("description", "No description")
            applicable = handler.get("applicable_types", [])

            click.echo(f"\n  {name}")
            click.echo(f"    Class: {full_class}")
            click.echo(f"    Description: {description}")
            click.echo(f"    Applicable: {', '.join(applicable)}")

    click.echo("\n" + "=" * 80)


if __name__ == "__main__":
    main()
