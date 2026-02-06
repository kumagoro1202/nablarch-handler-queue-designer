"""End-to-end tests for NHQD.

Tests the complete flow from requirements to XML generation,
validating that all components work together correctly.
"""

from pathlib import Path

import pytest
from lxml import etree

from nhqd.engine.rule_engine import RuleEngine
from nhqd.generator.xml_generator import XmlGenerator, XmlGeneratorConfig
from nhqd.parser.yaml_parser import (
    AuthenticationRequirements,
    DatabaseRequirements,
    LoggingRequirements,
    ProjectRequirements,
    SecurityRequirements,
    SessionRequirements,
)


@pytest.fixture
def knowledge_base_path() -> Path:
    """Return path to knowledge base directory."""
    return Path(__file__).parent.parent / "src" / "nhqd" / "knowledge"


@pytest.fixture
def rule_engine(knowledge_base_path: Path) -> RuleEngine:
    """Create a RuleEngine instance."""
    return RuleEngine(knowledge_base_path)


@pytest.fixture
def xml_generator() -> XmlGenerator:
    """Create an XmlGenerator instance."""
    return XmlGenerator()


class TestWebApplicationE2E:
    """End-to-end tests for web application handler queue generation."""

    def test_complete_web_flow(self, rule_engine: RuleEngine, xml_generator: XmlGenerator) -> None:
        """Test complete flow: Requirements -> RuleEngine -> XmlGenerator."""
        # 1. 要件を定義（examples/web_app_requirements.yaml と同等）
        requirements = ProjectRequirements(
            name="Customer Management System",
            app_type="web",
            database=DatabaseRequirements(enabled=True, db_type="PostgreSQL", transaction="required"),
            authentication=AuthenticationRequirements(enabled=True, auth_type="session", login_check=True),
            security=SecurityRequirements(csrf_protection=True, secure_headers=True, cors=False),
            session=SessionRequirements(enabled=True, store="db"),
            logging=LoggingRequirements(access_log=True, sql_log=True),
        )

        # 2. ルールエンジンでハンドラキューを生成
        result = rule_engine.generate(requirements)

        # 3. 結果の検証
        assert result.app_type == "web"
        assert len(result.handlers) > 0

        handler_names = [h.class_name for h in result.handlers]

        # 必須ハンドラの存在確認
        assert "GlobalErrorHandler" in handler_names
        assert "HttpResponseHandler" in handler_names
        assert "HttpRequestJavaPackageMapping" in handler_names

        # 要件に基づくハンドラの存在確認
        assert "DbConnectionManagementHandler" in handler_names  # database.enabled=True
        assert "TransactionManagementHandler" in handler_names   # database.transaction=required
        assert "CsrfTokenVerificationHandler" in handler_names   # security.csrf_protection=True
        assert "SessionStoreHandler" in handler_names            # session.enabled=True
        assert "HttpAccessLogHandler" in handler_names           # logging.access_log=True
        assert "LoginUserPrincipalCheckHandler" in handler_names # authentication.login_check=True

        # ディスパッチハンドラが末尾にあることを確認（C-02制約）
        assert result.handlers[-1].class_name == "HttpRequestJavaPackageMapping"

        # 4. XML生成
        xml_string = xml_generator.generate_string(result)

        # 5. XMLの検証
        assert "<?xml" in xml_string
        assert "component-configuration" in xml_string
        assert "webFrontController" in xml_string

        # XMLとしてパース可能であることを確認
        parsed = etree.fromstring(xml_string.encode("UTF-8"))
        assert parsed is not None

    def test_web_flow_with_file_output(
        self, rule_engine: RuleEngine, xml_generator: XmlGenerator, tmp_path: Path
    ) -> None:
        """Test complete flow with file output."""
        requirements = ProjectRequirements(
            name="TestWebApp",
            app_type="web",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        output_path = tmp_path / "handler-queue.xml"

        xml_generator.write_file(result, output_path)

        assert output_path.exists()
        content = output_path.read_bytes()
        parsed = etree.fromstring(content)
        assert parsed is not None

    def test_constraint_c01_satisfied(self, rule_engine: RuleEngine) -> None:
        """C-01: TransactionManagementHandler must be after DbConnectionManagementHandler."""
        requirements = ProjectRequirements(
            name="TestWebApp",
            app_type="web",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        handler_names = [h.class_name for h in result.handlers]

        # 両方のハンドラが存在することを確認
        assert "DbConnectionManagementHandler" in handler_names
        assert "TransactionManagementHandler" in handler_names

        # 順序が正しいことを確認
        db_pos = handler_names.index("DbConnectionManagementHandler")
        tx_pos = handler_names.index("TransactionManagementHandler")
        assert db_pos < tx_pos, "C-01 violated: Transaction handler before DB connection handler"


class TestRestApiE2E:
    """End-to-end tests for REST API handler queue generation."""

    def test_complete_rest_flow(self, rule_engine: RuleEngine, xml_generator: XmlGenerator) -> None:
        """Test complete REST API flow with inner handlers."""
        requirements = ProjectRequirements(
            name="REST API Service",
            app_type="rest",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        # ルールエンジンでハンドラキューを生成
        result = rule_engine.generate(requirements)

        assert result.app_type == "rest"
        handler_names = [h.class_name for h in result.handlers]

        # REST固有ハンドラの確認
        assert "GlobalErrorHandler" in handler_names
        assert "JaxRsResponseHandler" in handler_names
        assert "RoutesMapping" in handler_names

        # RoutesMappingが末尾にあることを確認
        assert result.handlers[-1].class_name == "RoutesMapping"

        # RoutesMappingにインナーハンドラがあることを確認
        routes_mapping = result.handlers[-1]
        assert len(routes_mapping.inner_handlers) > 0

        inner_handler_names = [h.class_name for h in routes_mapping.inner_handlers]
        assert "BodyConvertHandler" in inner_handler_names

        # XML生成
        xml_string = xml_generator.generate_string(result)

        # インナーハンドラがXMLに含まれることを確認
        assert "BodyConvertHandler" in xml_string
        assert "handlerList" in xml_string

    def test_rest_minimal_configuration(self, rule_engine: RuleEngine) -> None:
        """Test REST API with minimal configuration (no DB)."""
        requirements = ProjectRequirements(
            name="Simple REST API",
            app_type="rest",
            database=DatabaseRequirements(enabled=False),
        )

        result = rule_engine.generate(requirements)
        handler_names = [h.class_name for h in result.handlers]

        # DBハンドラが含まれていないことを確認
        assert "DbConnectionManagementHandler" not in handler_names
        assert "TransactionManagementHandler" not in handler_names


class TestBatchApplicationE2E:
    """End-to-end tests for batch application handler queue generation."""

    def test_complete_batch_flow(self, rule_engine: RuleEngine, xml_generator: XmlGenerator) -> None:
        """Test complete batch application flow."""
        requirements = ProjectRequirements(
            name="Batch Processing",
            app_type="batch",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)

        assert result.app_type == "batch"
        handler_names = [h.class_name for h in result.handlers]

        # バッチ固有ハンドラの確認
        assert "GlobalErrorHandler" in handler_names
        assert "MultiThreadExecutionHandler" in handler_names
        assert "LoopHandler" in handler_names
        assert "DataReadHandler" in handler_names

        # DataReadHandlerが末尾にあることを確認
        assert result.handlers[-1].class_name == "DataReadHandler"

        # XML生成
        xml_string = xml_generator.generate_string(result)

        # バッチ用コントローラであることを確認
        assert "main" in xml_string
        assert "nablarch.fw.launcher.Main" in xml_string

    def test_constraint_c07_satisfied(self, rule_engine: RuleEngine) -> None:
        """C-07: LoopHandler must be after MultiThreadExecutionHandler."""
        requirements = ProjectRequirements(
            name="TestBatch",
            app_type="batch",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        handler_names = [h.class_name for h in result.handlers]

        assert "MultiThreadExecutionHandler" in handler_names
        assert "LoopHandler" in handler_names

        multi_pos = handler_names.index("MultiThreadExecutionHandler")
        loop_pos = handler_names.index("LoopHandler")
        assert multi_pos < loop_pos, "C-07 violated: LoopHandler before MultiThreadExecutionHandler"

    def test_constraint_c08_satisfied(self, rule_engine: RuleEngine) -> None:
        """C-08: DataReadHandler must be after LoopHandler."""
        requirements = ProjectRequirements(
            name="TestBatch",
            app_type="batch",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        handler_names = [h.class_name for h in result.handlers]

        assert "LoopHandler" in handler_names
        assert "DataReadHandler" in handler_names

        loop_pos = handler_names.index("LoopHandler")
        data_pos = handler_names.index("DataReadHandler")
        assert loop_pos < data_pos, "C-08 violated: DataReadHandler before LoopHandler"


class TestErrorCases:
    """Tests for error handling."""

    def test_unsupported_app_type_raises_error(self, rule_engine: RuleEngine) -> None:
        """Unsupported application type should raise ValueError."""
        requirements = ProjectRequirements(
            name="Unknown App",
            app_type="unknown_type",
        )

        with pytest.raises(ValueError, match="Unsupported application type"):
            rule_engine.generate(requirements)

    def test_cycle_detection(self, rule_engine: RuleEngine) -> None:
        """Circular constraints should be detected."""
        import networkx as nx

        # 循環制約を持つグラフを直接作成
        graph = nx.DiGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")

        with pytest.raises(ValueError, match="Circular constraint"):
            rule_engine._topological_sort(graph)


class TestXmlGeneratorConfigOptions:
    """Tests for XmlGenerator configuration options."""

    def test_comments_enabled(self, rule_engine: RuleEngine) -> None:
        """Test XML generation with comments enabled."""
        config = XmlGeneratorConfig(include_comments=True)
        generator = XmlGenerator(config)

        requirements = ProjectRequirements(
            name="TestApp",
            app_type="web",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        xml_string = generator.generate_string(result)

        assert "<!--" in xml_string

    def test_comments_disabled(self, rule_engine: RuleEngine) -> None:
        """Test XML generation with comments disabled."""
        config = XmlGeneratorConfig(include_comments=False)
        generator = XmlGenerator(config)

        requirements = ProjectRequirements(
            name="TestApp",
            app_type="web",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        xml_string = generator.generate_string(result)

        # コメントが含まれていないことを確認（アプリタイプのコメント以外）
        # include_comments=Falseなので、descriptionベースのコメントは含まれない
        assert "Catches all uncaught exceptions" not in xml_string


class TestMultipleAppTypes:
    """Tests for multiple application types in a single test run."""

    @pytest.mark.parametrize("app_type,expected_controller", [
        ("web", "webFrontController"),
        ("rest", "webFrontController"),
        ("batch", "main"),
    ])
    def test_controller_name_by_app_type(
        self, rule_engine: RuleEngine, xml_generator: XmlGenerator, app_type: str, expected_controller: str
    ) -> None:
        """Verify correct controller name for each application type."""
        requirements = ProjectRequirements(
            name="TestApp",
            app_type=app_type,
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)
        xml_string = xml_generator.generate_string(result)

        assert f'name="{expected_controller}"' in xml_string
