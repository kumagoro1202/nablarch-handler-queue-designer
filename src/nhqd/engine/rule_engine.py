"""Rule-based inference engine for handler queue generation.

Determines the optimal handler queue configuration based on application
requirements, base patterns, and ordering constraints. Uses a DAG-based
topological sort to resolve handler ordering.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

from nhqd.parser.yaml_parser import ProjectRequirements


@dataclass
class HandlerEntry:
    """A single handler in the generated queue."""

    class_name: str
    full_class_path: str
    description: str = ""
    position: int = 0
    is_custom: bool = False
    required: bool = True
    required_when: str | None = None
    fixed_position: str | None = None
    inner_handlers: list["HandlerEntry"] = field(default_factory=list)


@dataclass
class HandlerQueueResult:
    """Result of handler queue generation."""

    app_type: str
    handlers: list[HandlerEntry] = field(default_factory=list)
    constraints_satisfied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RuleEngine:
    """Rule-based engine for generating Nablarch handler queue configurations.

    Workflow:
        1. Select base pattern from application type
        2. Add/remove handlers based on requirements flags
        3. Build ordering constraint DAG
        4. Topological sort to determine final order
        5. Validate all constraints are satisfied
    """

    # ディスパッチハンドラ（末尾に配置すべきハンドラ）
    DISPATCH_HANDLERS = {
        "HttpRequestJavaPackageMapping",
        "RoutesMapping",
        "DataReadHandler",
    }

    def __init__(self, knowledge_base_path: Path | None = None) -> None:
        """Initialize the rule engine.

        Args:
            knowledge_base_path: Path to knowledge base directory containing
                handler_catalog.yaml, constraints.yaml, and patterns/.
        """
        if knowledge_base_path is None:
            # デフォルトはパッケージ内のknowledgeディレクトリ
            knowledge_base_path = Path(__file__).parent.parent / "knowledge"

        self.knowledge_base_path = knowledge_base_path
        self.handler_catalog: dict[str, dict[str, Any]] = {}
        self.constraints: list[dict[str, Any]] = []
        self.patterns: dict[str, dict[str, Any]] = {}

        self._load_knowledge_base()

    def _load_knowledge_base(self) -> None:
        """Load handler catalog, constraints, and patterns from YAML files."""
        # ハンドラカタログの読み込み
        catalog_path = self.knowledge_base_path / "handler_catalog.yaml"
        if catalog_path.exists():
            with open(catalog_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                for handler in data.get("handlers", []):
                    self.handler_catalog[handler["name"]] = handler

        # 制約の読み込み
        constraints_path = self.knowledge_base_path / "constraints.yaml"
        if constraints_path.exists():
            with open(constraints_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.constraints = data.get("constraints", [])

        # パターンの読み込み
        patterns_dir = self.knowledge_base_path / "patterns"
        if patterns_dir.exists():
            for pattern_file in patterns_dir.glob("*.yaml"):
                with open(pattern_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "pattern" in data:
                        pattern = data["pattern"]
                        app_type = pattern.get("app_type", pattern_file.stem)
                        self.patterns[app_type] = pattern

    def generate(self, requirements: ProjectRequirements) -> HandlerQueueResult:
        """Generate a handler queue configuration from requirements.

        Args:
            requirements: Parsed project requirements.

        Returns:
            Generated handler queue with ordering and validation results.
        """
        # 1. ベースパターンの読み込み
        base_handlers = self._load_base_pattern(requirements.app_type)

        # 2. 要件に基づきハンドラを追加/削除
        filtered_handlers = self._apply_requirements(base_handlers, requirements)

        # 3. 順序制約グラフの構築
        graph = self._build_constraint_graph(filtered_handlers)

        # 4. トポロジカルソートで順序決定
        sorted_names = self._topological_sort(graph)

        # 5. ソート結果に基づきハンドラリストを再構成
        handler_map = {h.class_name: h for h in filtered_handlers}
        sorted_handlers = []
        for i, name in enumerate(sorted_names):
            if name in handler_map:
                handler = handler_map[name]
                handler.position = i
                sorted_handlers.append(handler)

        # 6. 制約充足確認
        constraints_satisfied = self._check_constraints(sorted_handlers, requirements.app_type)

        return HandlerQueueResult(
            app_type=requirements.app_type,
            handlers=sorted_handlers,
            constraints_satisfied=constraints_satisfied,
            warnings=[],
        )

    def _load_base_pattern(self, app_type: str) -> list[HandlerEntry]:
        """Load the base handler pattern for the given application type.

        Args:
            app_type: Application type (web, rest, batch, etc.).

        Returns:
            Base list of handlers for the application type.

        Raises:
            ValueError: If the application type is not supported.
        """
        if app_type not in self.patterns:
            raise ValueError(f"Unsupported application type: {app_type}")

        pattern = self.patterns[app_type]
        handlers: list[HandlerEntry] = []

        for h in pattern.get("handlers", []):
            inner_handlers = []
            for inner in h.get("inner_handlers", []):
                inner_handlers.append(
                    HandlerEntry(
                        class_name=inner["name"],
                        full_class_path=inner["full_class"],
                        description=self._get_handler_description(inner["name"]),
                        required=inner.get("required", False),
                        required_when=inner.get("required_when"),
                    )
                )

            handlers.append(
                HandlerEntry(
                    class_name=h["name"],
                    full_class_path=h["full_class"],
                    description=self._get_handler_description(h["name"]),
                    required=h.get("required", False),
                    required_when=h.get("required_when"),
                    fixed_position=h.get("fixed_position"),
                    inner_handlers=inner_handlers,
                )
            )

        return handlers

    def _get_handler_description(self, handler_name: str) -> str:
        """Get description for a handler from the catalog."""
        if handler_name in self.handler_catalog:
            return self.handler_catalog[handler_name].get("description", "")
        return ""

    def _apply_requirements(
        self,
        base_handlers: list[HandlerEntry],
        requirements: ProjectRequirements,
    ) -> list[HandlerEntry]:
        """Add or remove handlers based on requirement flags.

        Args:
            base_handlers: Base pattern handlers.
            requirements: Project requirements.

        Returns:
            Modified handler list.
        """
        result: list[HandlerEntry] = []

        for handler in base_handlers:
            if self._should_include_handler(handler, requirements):
                # インナーハンドラも同様にフィルタリング
                filtered_inner = [
                    h for h in handler.inner_handlers if self._should_include_handler(h, requirements)
                ]
                handler.inner_handlers = filtered_inner
                result.append(handler)

        return result

    def _should_include_handler(self, handler: HandlerEntry, requirements: ProjectRequirements) -> bool:
        """Determine if a handler should be included based on requirements."""
        if handler.required:
            return True

        if handler.required_when is None:
            return False

        # required_when の条件を評価
        condition = handler.required_when

        # database.enabled
        if condition == "database.enabled":
            return requirements.database.enabled

        # database.transaction
        if condition == "database.transaction":
            return requirements.database.transaction != "none"

        # security.csrf_protection
        if condition == "security.csrf_protection":
            return requirements.security.csrf_protection

        # security.secure_headers
        if condition == "security.secure_headers":
            return requirements.security.secure_headers

        # session.enabled
        if condition == "session.enabled":
            return requirements.session.enabled

        # logging.access_log
        if condition == "logging.access_log":
            return requirements.logging.access_log

        # authentication.login_check
        if condition == "authentication.login_check":
            return requirements.authentication.login_check

        # validation.bean_validation
        if condition == "validation.bean_validation":
            return True  # デフォルトで有効

        return False

    def _build_constraint_graph(self, handlers: list[HandlerEntry]) -> nx.DiGraph:
        """Build a DAG of ordering constraints for the given handlers.

        Args:
            handlers: List of handlers to order.

        Returns:
            Directed acyclic graph of ordering constraints.
        """
        graph = nx.DiGraph()

        # ハンドラをノードとして追加
        handler_names = {h.class_name for h in handlers}
        for name in handler_names:
            graph.add_node(name)

        # 制約に基づきエッジを追加
        for constraint in self.constraints:
            rule = constraint.get("rule", {})

            # must_be_after 制約
            if "must_be_after" in rule:
                handler = rule.get("handler")
                after = rule.get("must_be_after")

                if handler in handler_names:
                    if isinstance(after, list):
                        for a in after:
                            if a in handler_names:
                                graph.add_edge(a, handler)
                    elif after in handler_names:
                        graph.add_edge(after, handler)

        # パターン順序に基づく暗黙的な制約
        # パターンファイルの順序を基本順序として使用
        for i, handler in enumerate(handlers):
            if i > 0:
                prev_handler = handlers[i - 1]
                if not graph.has_edge(handler.class_name, prev_handler.class_name):
                    # サイクルを作らない範囲で順序を追加
                    if prev_handler.class_name in graph and handler.class_name in graph:
                        try:
                            # サイクルチェック
                            if not nx.has_path(graph, handler.class_name, prev_handler.class_name):
                                graph.add_edge(prev_handler.class_name, handler.class_name)
                        except nx.NodeNotFound:
                            pass

        return graph

    def _topological_sort(self, graph: nx.DiGraph) -> list[str]:
        """Perform topological sort on the constraint DAG.

        Args:
            graph: Constraint DAG.

        Returns:
            Ordered list of handler class names.

        Raises:
            ValueError: If the graph contains cycles.
        """
        try:
            return list(nx.topological_sort(graph))
        except nx.NetworkXUnfeasible as e:
            raise ValueError("Circular constraint detected in handler ordering") from e

    def _check_constraints(self, handlers: list[HandlerEntry], app_type: str) -> list[str]:
        """Check which constraints are satisfied.

        Args:
            handlers: Ordered list of handlers.
            app_type: Application type.

        Returns:
            List of satisfied constraint IDs.
        """
        satisfied = []
        handler_positions = {h.class_name: i for i, h in enumerate(handlers)}

        for constraint in self.constraints:
            constraint_id = constraint.get("id", "")
            applicable_types = constraint.get("applicable_types", [])

            if app_type not in applicable_types:
                continue

            rule = constraint.get("rule", {})

            # must_be_after 制約の検証
            if "must_be_after" in rule:
                handler = rule.get("handler")
                after = rule.get("must_be_after")

                if handler not in handler_positions:
                    continue

                is_satisfied = True
                if isinstance(after, list):
                    for a in after:
                        if a in handler_positions:
                            if handler_positions[handler] <= handler_positions[a]:
                                is_satisfied = False
                                break
                elif after in handler_positions:
                    if handler_positions[handler] <= handler_positions[after]:
                        is_satisfied = False

                if is_satisfied:
                    satisfied.append(constraint_id)

            # must_be_last 制約の検証
            elif "must_be_last" in rule and rule["must_be_last"]:
                # ディスパッチハンドラが末尾にあるかチェック
                if handlers:
                    last_handler = handlers[-1]
                    if last_handler.class_name in self.DISPATCH_HANDLERS:
                        satisfied.append(constraint_id)

        return satisfied
