"""XML configuration generator for Nablarch handler queues.

Generates Nablarch component-configuration XML files from
a resolved handler queue configuration.
"""

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from nhqd.engine.rule_engine import HandlerQueueResult


@dataclass
class XmlGeneratorConfig:
    """Configuration for XML generation."""

    indent: int = 2
    xml_declaration: bool = True
    encoding: str = "UTF-8"
    include_comments: bool = True


class XmlGenerator:
    """Generates Nablarch XML component-configuration files.

    Produces valid XML configuration that can be directly used in
    Nablarch's component-configuration system for defining handler queues.
    """

    CONTROLLER_CLASSES: dict[str, str] = {
        "web": "nablarch.fw.web.servlet.WebFrontController",
        "rest": "nablarch.fw.web.servlet.WebFrontController",
        "batch": "nablarch.fw.launcher.Main",
        "batch_resident": "nablarch.fw.launcher.Main",
        "mom_messaging": "nablarch.fw.launcher.Main",
        "http_messaging": "nablarch.fw.web.servlet.WebFrontController",
    }

    CONTROLLER_NAMES: dict[str, str] = {
        "web": "webFrontController",
        "rest": "webFrontController",
        "batch": "main",
        "batch_resident": "main",
        "mom_messaging": "main",
        "http_messaging": "webFrontController",
    }

    def __init__(self, config: XmlGeneratorConfig | None = None) -> None:
        """Initialize the XML generator.

        Args:
            config: Optional generator configuration.
        """
        raise NotImplementedError

    def generate(self, result: HandlerQueueResult) -> etree._Element:
        """Generate XML element tree from handler queue result.

        Args:
            result: Handler queue generation result.

        Returns:
            Root XML element of the component configuration.
        """
        raise NotImplementedError

    def generate_string(self, result: HandlerQueueResult) -> str:
        """Generate XML configuration as a string.

        Args:
            result: Handler queue generation result.

        Returns:
            XML configuration string.
        """
        raise NotImplementedError

    def write_file(self, result: HandlerQueueResult, output_path: Path) -> None:
        """Write XML configuration to a file.

        Args:
            result: Handler queue generation result.
            output_path: Path to write the XML file.
        """
        raise NotImplementedError
