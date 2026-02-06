"""Tests for NHQD XML configuration generator."""

from pathlib import Path

import pytest
from lxml import etree

from nhqd.engine.rule_engine import HandlerEntry, HandlerQueueResult
from nhqd.generator.xml_generator import XmlGenerator, XmlGeneratorConfig


@pytest.fixture
def web_handler_result() -> HandlerQueueResult:
    """Create a sample web application handler queue result."""
    return HandlerQueueResult(
        app_type="web",
        handlers=[
            HandlerEntry(
                class_name="GlobalErrorHandler",
                full_class_path="nablarch.fw.handler.GlobalErrorHandler",
                description="Catches all uncaught exceptions",
                position=0,
            ),
            HandlerEntry(
                class_name="HttpResponseHandler",
                full_class_path="nablarch.fw.web.handler.HttpResponseHandler",
                description="Converts HttpResponse to servlet response",
                position=1,
            ),
            HandlerEntry(
                class_name="DbConnectionManagementHandler",
                full_class_path="nablarch.common.handler.DbConnectionManagementHandler",
                description="Manages database connection lifecycle",
                position=2,
            ),
            HandlerEntry(
                class_name="HttpRequestJavaPackageMapping",
                full_class_path="nablarch.fw.web.handler.HttpRequestJavaPackageMapping",
                description="Dispatches to action classes",
                position=3,
            ),
        ],
        constraints_satisfied=["C-01", "C-02"],
    )


@pytest.fixture
def rest_handler_result() -> HandlerQueueResult:
    """Create a sample REST API handler queue result with inner handlers."""
    return HandlerQueueResult(
        app_type="rest",
        handlers=[
            HandlerEntry(
                class_name="GlobalErrorHandler",
                full_class_path="nablarch.fw.handler.GlobalErrorHandler",
                description="Catches all uncaught exceptions",
                position=0,
            ),
            HandlerEntry(
                class_name="JaxRsResponseHandler",
                full_class_path="nablarch.fw.jaxrs.JaxRsResponseHandler",
                description="Converts action return values to HTTP responses",
                position=1,
            ),
            HandlerEntry(
                class_name="RoutesMapping",
                full_class_path="nablarch.fw.jaxrs.JaxRsMethodBinder",
                description="Routes requests to JAX-RS resource methods",
                position=2,
                inner_handlers=[
                    HandlerEntry(
                        class_name="BodyConvertHandler",
                        full_class_path="nablarch.fw.jaxrs.BodyConvertHandler",
                        description="Converts request body to Java objects",
                    ),
                ],
            ),
        ],
        constraints_satisfied=["C-02", "C-03"],
    )


@pytest.fixture
def batch_handler_result() -> HandlerQueueResult:
    """Create a sample batch application handler queue result."""
    return HandlerQueueResult(
        app_type="batch",
        handlers=[
            HandlerEntry(
                class_name="StatusCodeConvertHandler",
                full_class_path="nablarch.fw.handler.StatusCodeConvertHandler",
                description="Converts process exit status codes",
                position=0,
            ),
            HandlerEntry(
                class_name="GlobalErrorHandler",
                full_class_path="nablarch.fw.handler.GlobalErrorHandler",
                description="Catches all uncaught exceptions",
                position=1,
            ),
            HandlerEntry(
                class_name="MultiThreadExecutionHandler",
                full_class_path="nablarch.fw.handler.MultiThreadExecutionHandler",
                description="Manages multi-threaded batch execution",
                position=2,
            ),
            HandlerEntry(
                class_name="LoopHandler",
                full_class_path="nablarch.fw.handler.LoopHandler",
                description="Controls loop processing",
                position=3,
            ),
            HandlerEntry(
                class_name="DataReadHandler",
                full_class_path="nablarch.fw.handler.DataReadHandler",
                description="Reads input data for batch processing",
                position=4,
            ),
        ],
        constraints_satisfied=["C-07", "C-08"],
    )


@pytest.fixture
def xml_generator() -> XmlGenerator:
    """Create an XmlGenerator instance with default config."""
    return XmlGenerator()


class TestXmlGenerator:
    """Tests for Nablarch XML configuration generation."""

    def test_generate_web_xml(self, xml_generator: XmlGenerator, web_handler_result: HandlerQueueResult) -> None:
        """Generate valid XML for web application handler queue."""
        root = xml_generator.generate(web_handler_result)

        # ルート要素の確認（名前空間がデフォルトとして設定されている）
        assert root.tag == "component-configuration"

        # コンポーネント要素の確認
        components = root.findall("component")
        assert len(components) == 1

        component = components[0]
        assert component.get("name") == "webFrontController"
        assert component.get("class") == "nablarch.fw.web.servlet.WebFrontController"

        # ハンドラリストの確認
        property_elem = component.find("property")
        assert property_elem is not None
        assert property_elem.get("name") == "handlerQueue"

        list_elem = property_elem.find("list")
        assert list_elem is not None

        handlers = list_elem.findall("component")
        assert len(handlers) == 4

    def test_generate_rest_xml_with_inner_handlers(
        self, xml_generator: XmlGenerator, rest_handler_result: HandlerQueueResult
    ) -> None:
        """Generate XML with RoutesMapping inner handler structure."""
        root = xml_generator.generate(rest_handler_result)

        # handlerQueueを取得
        handlers = root.findall(".//property[@name='handlerQueue']/list/component")
        assert len(handlers) == 3

        # RoutesMapping（最後のハンドラ）のインナーハンドラを確認
        routes_mapping = handlers[-1]
        inner_property = routes_mapping.find("property")
        assert inner_property is not None
        assert inner_property.get("name") == "handlerList"

        inner_handlers = inner_property.findall("list/component")
        assert len(inner_handlers) == 1
        assert inner_handlers[0].get("class") == "nablarch.fw.jaxrs.BodyConvertHandler"

    def test_generate_batch_xml(
        self, xml_generator: XmlGenerator, batch_handler_result: HandlerQueueResult
    ) -> None:
        """Generate XML for batch application."""
        root = xml_generator.generate(batch_handler_result)

        component = root.find("component")
        assert component is not None
        assert component.get("name") == "main"
        assert component.get("class") == "nablarch.fw.launcher.Main"

        handlers = root.findall(".//property[@name='handlerQueue']/list/component")
        assert len(handlers) == 5

    def test_xml_has_correct_controller_class(self, xml_generator: XmlGenerator) -> None:
        """Verify controller class matches application type."""
        test_cases = [
            ("web", "webFrontController", "nablarch.fw.web.servlet.WebFrontController"),
            ("rest", "webFrontController", "nablarch.fw.web.servlet.WebFrontController"),
            ("batch", "main", "nablarch.fw.launcher.Main"),
            ("batch_resident", "main", "nablarch.fw.launcher.Main"),
        ]

        for app_type, expected_name, expected_class in test_cases:
            result = HandlerQueueResult(
                app_type=app_type,
                handlers=[
                    HandlerEntry(
                        class_name="TestHandler",
                        full_class_path="test.Handler",
                    )
                ],
            )
            root = xml_generator.generate(result)
            component = root.find("component")
            assert component is not None, f"No component for {app_type}"
            assert component.get("name") == expected_name, f"Wrong name for {app_type}"
            assert component.get("class") == expected_class, f"Wrong class for {app_type}"

    def test_xml_handler_order_matches_result(
        self, xml_generator: XmlGenerator, web_handler_result: HandlerQueueResult
    ) -> None:
        """Verify handler order in XML matches generation result."""
        root = xml_generator.generate(web_handler_result)

        handlers = root.findall(".//property[@name='handlerQueue']/list/component")

        expected_classes = [h.full_class_path for h in web_handler_result.handlers]
        actual_classes = [h.get("class") for h in handlers]

        assert actual_classes == expected_classes

    def test_xml_includes_comments_when_enabled(self, web_handler_result: HandlerQueueResult) -> None:
        """Include descriptive comments when configured."""
        config = XmlGeneratorConfig(include_comments=True)
        generator = XmlGenerator(config)

        xml_string = generator.generate_string(web_handler_result)

        # コメントが含まれていることを確認
        assert "<!-- " in xml_string
        assert "Catches all uncaught exceptions" in xml_string

    def test_xml_excludes_comments_when_disabled(self, web_handler_result: HandlerQueueResult) -> None:
        """Omit comments when configured."""
        config = XmlGeneratorConfig(include_comments=False)
        generator = XmlGenerator(config)

        xml_string = generator.generate_string(web_handler_result)

        # コメントが含まれていないことを確認
        assert "<!-- Catches" not in xml_string

    def test_generate_string_produces_valid_xml(
        self, xml_generator: XmlGenerator, web_handler_result: HandlerQueueResult
    ) -> None:
        """String output is valid, parseable XML."""
        xml_string = xml_generator.generate_string(web_handler_result)

        # XMLとしてパース可能であることを確認
        # lxml outputs single quotes in XML declaration
        assert xml_string.startswith("<?xml version='1.0' encoding='UTF-8'?>")

        # パースしてエラーが出ないことを確認
        parsed = etree.fromstring(xml_string.encode("UTF-8"))
        assert parsed is not None

        # 名前空間が正しいことを確認
        assert "http://tis.co.jp/nablarch/component-configuration" in xml_string

    def test_write_file_creates_output(
        self, xml_generator: XmlGenerator, web_handler_result: HandlerQueueResult, tmp_path: Path
    ) -> None:
        """Write XML file to disk."""
        output_path = tmp_path / "handler-queue.xml"

        xml_generator.write_file(web_handler_result, output_path)

        # ファイルが作成されたことを確認
        assert output_path.exists()

        # ファイル内容が有効なXMLであることを確認
        with open(output_path, "rb") as f:
            content = f.read()
            parsed = etree.fromstring(content)
            assert parsed is not None

    def test_custom_encoding(self, web_handler_result: HandlerQueueResult) -> None:
        """Support custom encoding configuration."""
        config = XmlGeneratorConfig(encoding="UTF-8")
        generator = XmlGenerator(config)

        xml_string = generator.generate_string(web_handler_result)
        # lxml outputs single quotes in XML declaration
        assert "encoding='UTF-8'" in xml_string

    def test_xml_declaration_can_be_disabled(self, web_handler_result: HandlerQueueResult) -> None:
        """XML declaration can be omitted."""
        config = XmlGeneratorConfig(xml_declaration=False)
        generator = XmlGenerator(config)

        xml_string = generator.generate_string(web_handler_result)
        assert not xml_string.startswith("<?xml")
