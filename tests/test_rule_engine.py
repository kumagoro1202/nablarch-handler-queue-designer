"""Tests for NHQD rule-based inference engine."""

from pathlib import Path

import pytest

from nhqd.engine.rule_engine import HandlerEntry, HandlerQueueResult, RuleEngine
from nhqd.parser.yaml_parser import (
    AuthenticationRequirements,
    DatabaseRequirements,
    ProjectRequirements,
    SecurityRequirements,
    SessionRequirements,
    LoggingRequirements,
)


@pytest.fixture
def knowledge_base_path() -> Path:
    """Return path to knowledge base directory."""
    return Path(__file__).parent.parent / "src" / "nhqd" / "knowledge"


@pytest.fixture
def rule_engine(knowledge_base_path: Path) -> RuleEngine:
    """Create a RuleEngine instance with default knowledge base."""
    return RuleEngine(knowledge_base_path)


class TestRuleEngine:
    """Tests for the rule-based handler queue generation engine."""

    def test_generate_web_standard_pattern(self, rule_engine: RuleEngine) -> None:
        """Generate standard web application handler queue."""
        requirements = ProjectRequirements(
            name="TestWebApp",
            app_type="web",
            database=DatabaseRequirements(enabled=True, transaction="required"),
            security=SecurityRequirements(csrf_protection=True),
        )

        result = rule_engine.generate(requirements)

        assert result.app_type == "web"
        assert len(result.handlers) > 0

        # 必須ハンドラの存在確認
        handler_names = [h.class_name for h in result.handlers]
        assert "GlobalErrorHandler" in handler_names
        assert "HttpResponseHandler" in handler_names
        assert "HttpRequestJavaPackageMapping" in handler_names

        # DB関連ハンドラの存在確認（database.enabled=True）
        assert "DbConnectionManagementHandler" in handler_names
        assert "TransactionManagementHandler" in handler_names

        # CSRFハンドラの存在確認（csrf_protection=True）
        assert "CsrfTokenVerificationHandler" in handler_names

        # ディスパッチハンドラが末尾にあることを確認
        assert result.handlers[-1].class_name == "HttpRequestJavaPackageMapping"

    def test_generate_rest_minimal_pattern(self, rule_engine: RuleEngine) -> None:
        """Generate minimal REST API handler queue."""
        requirements = ProjectRequirements(
            name="TestRestApi",
            app_type="rest",
            database=DatabaseRequirements(enabled=False),
        )

        result = rule_engine.generate(requirements)

        assert result.app_type == "rest"
        assert len(result.handlers) > 0

        handler_names = [h.class_name for h in result.handlers]
        assert "GlobalErrorHandler" in handler_names
        assert "JaxRsResponseHandler" in handler_names
        assert "RoutesMapping" in handler_names

        # DB無効なのでDBハンドラは含まれない
        assert "DbConnectionManagementHandler" not in handler_names
        assert "TransactionManagementHandler" not in handler_names

        # RoutesMappingが末尾にあることを確認
        assert result.handlers[-1].class_name == "RoutesMapping"

    def test_generate_batch_ondemand_pattern(self, rule_engine: RuleEngine) -> None:
        """Generate on-demand batch handler queue."""
        requirements = ProjectRequirements(
            name="TestBatch",
            app_type="batch",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)

        assert result.app_type == "batch"
        assert len(result.handlers) > 0

        handler_names = [h.class_name for h in result.handlers]
        assert "GlobalErrorHandler" in handler_names
        assert "MultiThreadExecutionHandler" in handler_names
        assert "LoopHandler" in handler_names
        assert "DataReadHandler" in handler_names

        # DataReadHandlerが末尾にあることを確認
        assert result.handlers[-1].class_name == "DataReadHandler"

    def test_generate_batch_resident_pattern(self, rule_engine: RuleEngine) -> None:
        """Generate resident batch handler queue."""
        requirements = ProjectRequirements(
            name="TestResidentBatch",
            app_type="batch_resident",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)

        assert result.app_type == "batch_resident"
        # batch_residentパターンが存在すれば検証
        if len(result.handlers) > 0:
            handler_names = [h.class_name for h in result.handlers]
            assert "GlobalErrorHandler" in handler_names

    def test_db_disabled_excludes_db_handlers(self, rule_engine: RuleEngine) -> None:
        """Omit DB handlers when database is not required."""
        requirements = ProjectRequirements(
            name="TestWebNoDb",
            app_type="web",
            database=DatabaseRequirements(enabled=False),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]
        assert "DbConnectionManagementHandler" not in handler_names
        assert "TransactionManagementHandler" not in handler_names

    def test_csrf_enabled_includes_csrf_handler(self, rule_engine: RuleEngine) -> None:
        """Include CSRF handler when CSRF protection is enabled."""
        requirements = ProjectRequirements(
            name="TestWebCsrf",
            app_type="web",
            security=SecurityRequirements(csrf_protection=True),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]
        assert "CsrfTokenVerificationHandler" in handler_names

    def test_csrf_disabled_excludes_csrf_handler(self, rule_engine: RuleEngine) -> None:
        """Exclude CSRF handler when CSRF protection is disabled."""
        requirements = ProjectRequirements(
            name="TestWebNoCsrf",
            app_type="web",
            security=SecurityRequirements(csrf_protection=False),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]
        assert "CsrfTokenVerificationHandler" not in handler_names

    def test_topological_sort_respects_constraints(self, rule_engine: RuleEngine) -> None:
        """Verify topological sort produces constraint-valid ordering."""
        requirements = ProjectRequirements(
            name="TestConstraints",
            app_type="web",
            database=DatabaseRequirements(enabled=True, transaction="required"),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]

        # C-01: TransactionManagementHandler must be after DbConnectionManagementHandler
        if "DbConnectionManagementHandler" in handler_names and "TransactionManagementHandler" in handler_names:
            db_pos = handler_names.index("DbConnectionManagementHandler")
            tx_pos = handler_names.index("TransactionManagementHandler")
            assert db_pos < tx_pos, "C-01 violated: Transaction handler before DB connection handler"

        # C-02: Dispatch handler must be last
        dispatch_handlers = {"HttpRequestJavaPackageMapping", "RoutesMapping", "DataReadHandler"}
        last_handler = handler_names[-1]
        assert last_handler in dispatch_handlers, f"C-02 violated: {last_handler} is not a dispatch handler at end"

    def test_cycle_detection_raises_error(self, rule_engine: RuleEngine) -> None:
        """Detect and raise error on circular constraints."""
        import networkx as nx

        # 循環制約を持つグラフを直接作成してテスト
        graph = nx.DiGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")  # サイクル作成

        with pytest.raises(ValueError, match="Circular constraint"):
            rule_engine._topological_sort(graph)

    def test_unsupported_app_type_raises_error(self, rule_engine: RuleEngine) -> None:
        """Raise error for unsupported application type."""
        with pytest.raises(ValueError, match="Unsupported application type"):
            rule_engine._load_base_pattern("unsupported_type")

    def test_session_enabled_includes_session_handler(self, rule_engine: RuleEngine) -> None:
        """Include session handler when session is enabled."""
        requirements = ProjectRequirements(
            name="TestWebSession",
            app_type="web",
            session=SessionRequirements(enabled=True),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]
        assert "SessionStoreHandler" in handler_names

    def test_access_log_enabled_includes_log_handler(self, rule_engine: RuleEngine) -> None:
        """Include access log handler when access logging is enabled."""
        requirements = ProjectRequirements(
            name="TestWebAccessLog",
            app_type="web",
            logging=LoggingRequirements(access_log=True),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]
        assert "HttpAccessLogHandler" in handler_names

    def test_login_check_includes_auth_handler(self, rule_engine: RuleEngine) -> None:
        """Include login check handler when authentication is required."""
        requirements = ProjectRequirements(
            name="TestWebAuth",
            app_type="web",
            authentication=AuthenticationRequirements(login_check=True),
        )

        result = rule_engine.generate(requirements)

        handler_names = [h.class_name for h in result.handlers]
        assert "LoginUserPrincipalCheckHandler" in handler_names
