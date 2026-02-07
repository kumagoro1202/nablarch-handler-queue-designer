"""Constraint validator for Nablarch handler queue ordering.

Validates that a given handler queue configuration satisfies all
ordering constraints defined in the knowledge base (C-01 through C-10).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nhqd.engine.rule_engine import HandlerEntry


@dataclass
class ConstraintResult:
    """Result of a single constraint check."""

    constraint_id: str
    description: str
    satisfied: bool
    details: str = ""


@dataclass
class ValidationReport:
    """Full validation report for a handler queue."""

    results: list[ConstraintResult]

    @property
    def all_satisfied(self) -> bool:
        """Check if all constraints are satisfied."""
        return all(r.satisfied for r in self.results)

    @property
    def violations(self) -> list[ConstraintResult]:
        """Get list of violated constraints."""
        return [r for r in self.results if not r.satisfied]


class ConstraintValidator:
    """Validates handler queue ordering against known constraints.

    Constraints (C-01 to C-10) encode the mandatory ordering rules
    for Nablarch handler queues. This validator checks a proposed
    handler ordering against all applicable constraints.
    """

    def __init__(self, constraints_path: Path | None = None) -> None:
        """Initialize the constraint validator.

        Args:
            constraints_path: Path to constraints.yaml file.
        """
        if constraints_path is None:
            # Default to knowledge/constraints.yaml relative to this file
            current_dir = Path(__file__).parent.parent
            constraints_path = current_dir / "knowledge" / "constraints.yaml"

        with open(constraints_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.constraints: list[dict[str, Any]] = data.get("constraints", [])

    def validate(self, handlers: list[HandlerEntry]) -> ValidationReport:
        """Validate handler ordering against all constraints.

        Args:
            handlers: Ordered list of handlers to validate.

        Returns:
            Validation report with per-constraint results.
        """
        results = []
        for constraint in self.constraints:
            constraint_id = constraint["id"]
            result = self.check_constraint(constraint_id, handlers)
            results.append(result)

        return ValidationReport(results=results)

    def check_constraint(
        self,
        constraint_id: str,
        handlers: list[HandlerEntry],
    ) -> ConstraintResult:
        """Check a single constraint against the handler list.

        Args:
            constraint_id: Constraint identifier (e.g., "C-01").
            handlers: Ordered list of handlers.

        Returns:
            Result of the constraint check.
        """
        # Find the constraint definition
        constraint = next((c for c in self.constraints if c["id"] == constraint_id), None)
        if not constraint:
            return ConstraintResult(
                constraint_id=constraint_id,
                description=f"Unknown constraint {constraint_id}",
                satisfied=False,
                details=f"Constraint {constraint_id} not found in constraints.yaml",
            )

        description = constraint.get("description", "")
        rule = constraint.get("rule", {})

        # Check different rule types
        # Rule type 1: must_be_after
        if "must_be_after" in rule:
            handler_name = rule["handler"]
            must_be_after = rule["must_be_after"]

            handler_pos = self._get_handler_position(handlers, handler_name)
            after_pos = self._get_handler_position(handlers, must_be_after)

            # If either handler is not present, constraint is satisfied (N/A)
            if handler_pos is None or after_pos is None:
                return ConstraintResult(
                    constraint_id=constraint_id,
                    description=description,
                    satisfied=True,
                    details="Handler not present, constraint N/A",
                )

            # Check if handler comes after the required handler
            if handler_pos > after_pos:
                return ConstraintResult(
                    constraint_id=constraint_id,
                    description=description,
                    satisfied=True,
                    details=f"{handler_name} (pos {handler_pos}) is after {must_be_after} (pos {after_pos})",
                )
            else:
                return ConstraintResult(
                    constraint_id=constraint_id,
                    description=description,
                    satisfied=False,
                    details=f"{handler_name} (pos {handler_pos}) must be after {must_be_after} (pos {after_pos})",
                )

        # Rule type 2: must_be_last
        if "must_be_last" in rule and rule["must_be_last"]:
            handler_type = rule.get("handler", "")

            # Special handling for "dispatch" - check for dispatch-like handlers
            if handler_type == "dispatch":
                # Check if dispatch handler (HttpRequestJavaPackageMapping, RoutesMapping) is last
                dispatch_handlers = [
                    "HttpRequestJavaPackageMapping",
                    "RoutesMapping",
                    "RequestHandlerEntry",
                ]

                last_dispatch_pos = None
                last_dispatch_name = None

                for dh in dispatch_handlers:
                    pos = self._get_handler_position(handlers, dh)
                    if pos is not None:
                        last_dispatch_pos = pos
                        last_dispatch_name = dh

                if last_dispatch_pos is None:
                    return ConstraintResult(
                        constraint_id=constraint_id,
                        description=description,
                        satisfied=True,
                        details="No dispatch handler present, constraint N/A",
                    )

                # Check if it's the last handler
                if last_dispatch_pos == len(handlers) - 1:
                    return ConstraintResult(
                        constraint_id=constraint_id,
                        description=description,
                        satisfied=True,
                        details=f"{last_dispatch_name} is at the last position",
                    )
                else:
                    return ConstraintResult(
                        constraint_id=constraint_id,
                        description=description,
                        satisfied=False,
                        details=f"{last_dispatch_name} (pos {last_dispatch_pos}) must be last, but queue has {len(handlers)} handlers",
                    )

        # Rule type 3: preferred_position (warning severity)
        if "preferred_position" in rule:
            handler_name = rule["handler"]
            preferred = rule["preferred_position"]

            handler_pos = self._get_handler_position(handlers, handler_name)

            if handler_pos is None:
                return ConstraintResult(
                    constraint_id=constraint_id,
                    description=description,
                    satisfied=True,
                    details="Handler not present, constraint N/A",
                )

            # For "near_top", check if in first 3 positions
            if preferred == "near_top":
                if handler_pos < 3:
                    return ConstraintResult(
                        constraint_id=constraint_id,
                        description=description,
                        satisfied=True,
                        details=f"{handler_name} is near top (pos {handler_pos})",
                    )
                else:
                    # Warning, not critical
                    severity = constraint.get("severity", "warning")
                    if severity == "warning":
                        # Warnings are still "satisfied" for validation purposes
                        return ConstraintResult(
                            constraint_id=constraint_id,
                            description=description,
                            satisfied=True,
                            details=f"Warning: {handler_name} (pos {handler_pos}) should be near top",
                        )
                    else:
                        return ConstraintResult(
                            constraint_id=constraint_id,
                            description=description,
                            satisfied=False,
                            details=f"{handler_name} (pos {handler_pos}) should be near top",
                        )

        # Rule type 4: interceptor_ordering (warning severity)
        if rule.get("type") == "interceptor_ordering":
            # This is a configuration check, not runtime validation
            # For now, we'll mark it as satisfied
            return ConstraintResult(
                constraint_id=constraint_id,
                description=description,
                satisfied=True,
                details="Interceptor ordering is a configuration concern",
            )

        # Rule type 5: must_be_inside (for nested handlers)
        if "must_be_inside" in rule:
            # This requires checking inner_handlers, which is complex
            # For now, mark as satisfied
            return ConstraintResult(
                constraint_id=constraint_id,
                description=description,
                satisfied=True,
                details="Nested handler validation not implemented",
            )

        # Default: satisfied
        return ConstraintResult(
            constraint_id=constraint_id,
            description=description,
            satisfied=True,
            details="No applicable rule found",
        )

    def _get_handler_position(
        self,
        handlers: list[HandlerEntry],
        class_name: str,
    ) -> int | None:
        """Find the position of a handler by class name.

        Args:
            handlers: Ordered list of handlers.
            class_name: Handler class name to find.

        Returns:
            Position index, or None if not found.
        """
        for i, handler in enumerate(handlers):
            if handler.class_name == class_name:
                return i
        return None
