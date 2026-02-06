"""XML configuration generator for Nablarch handler queues.

Generates Nablarch component-configuration XML files from
a resolved handler queue configuration.
"""

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from nhqd.engine.rule_engine import HandlerEntry, HandlerQueueResult


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

    NAMESPACE = "http://tis.co.jp/nablarch/component-configuration"
    NSMAP = {None: NAMESPACE}

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
        self.config = config if config is not None else XmlGeneratorConfig()

    def generate(self, result: HandlerQueueResult) -> etree._Element:
        """Generate XML element tree from handler queue result.

        Args:
            result: Handler queue generation result.

        Returns:
            Root XML element of the component configuration.
        """
        # ルート要素の作成
        root = etree.Element(
            "component-configuration",
            nsmap=self.NSMAP,
        )

        # コントローラコンポーネントの作成
        controller_name = self.CONTROLLER_NAMES.get(result.app_type, "webFrontController")
        controller_class = self.CONTROLLER_CLASSES.get(
            result.app_type, "nablarch.fw.web.servlet.WebFrontController"
        )

        if self.config.include_comments:
            root.append(etree.Comment(f" Handler queue for {result.app_type} application "))

        component = etree.SubElement(root, "component")
        component.set("name", controller_name)
        component.set("class", controller_class)

        # handlerQueue プロパティの作成
        property_elem = etree.SubElement(component, "property")
        property_elem.set("name", "handlerQueue")

        # ハンドラリストの作成
        list_elem = etree.SubElement(property_elem, "list")

        # 各ハンドラを追加
        for handler in result.handlers:
            self._add_handler(list_elem, handler)

        return root

    def _add_handler(self, parent: etree._Element, handler: HandlerEntry) -> None:
        """Add a handler component to the parent element.

        Args:
            parent: Parent XML element.
            handler: Handler entry to add.
        """
        if self.config.include_comments and handler.description:
            parent.append(etree.Comment(f" {handler.description} "))

        handler_elem = etree.SubElement(parent, "component")
        handler_elem.set("class", handler.full_class_path)

        # インナーハンドラがある場合（REST APIのRoutesMapping等）
        if handler.inner_handlers:
            inner_property = etree.SubElement(handler_elem, "property")
            inner_property.set("name", "handlerList")
            inner_list = etree.SubElement(inner_property, "list")

            for inner_handler in handler.inner_handlers:
                self._add_handler(inner_list, inner_handler)

    def generate_string(self, result: HandlerQueueResult) -> str:
        """Generate XML configuration as a string.

        Args:
            result: Handler queue generation result.

        Returns:
            XML configuration string.
        """
        root = self.generate(result)
        return etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=self.config.xml_declaration,
            encoding=self.config.encoding,
        ).decode(self.config.encoding)

    def write_file(self, result: HandlerQueueResult, output_path: Path) -> None:
        """Write XML configuration to a file.

        Args:
            result: Handler queue generation result.
            output_path: Path to write the XML file.
        """
        root = self.generate(result)
        tree = etree.ElementTree(root)
        tree.write(
            str(output_path),
            pretty_print=True,
            xml_declaration=self.config.xml_declaration,
            encoding=self.config.encoding,
        )
