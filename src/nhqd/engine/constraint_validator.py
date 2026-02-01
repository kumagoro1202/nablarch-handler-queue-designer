"""Constraint validator for Nablarch handler queue ordering.

Validates that a given handler queue configuration satisfies all
ordering constraints defined in the knowledge base (C-01 through C-10).
"""

from dataclasses import dataclass
from pathlib import Path

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
        raise NotImplementedError

    def validate(self, handlers: list[HandlerEntry]) -> ValidationReport:
        """Validate handler ordering against all constraints.

        Args:
            handlers: Ordered list of handlers to validate.

        Returns:
            Validation report with per-constraint results.
        """
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError
