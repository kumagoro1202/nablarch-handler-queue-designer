"""Tests for NHQD constraint validator."""

import pytest

from nhqd.engine.constraint_validator import (
    ConstraintResult,
    ConstraintValidator,
    ValidationReport,
)
from nhqd.engine.rule_engine import HandlerEntry


class TestConstraintValidator:
    """Tests for handler queue constraint validation."""

    def test_valid_web_queue_passes_all_constraints(self) -> None:
        """Standard web queue satisfies all constraints."""
        validator = ConstraintValidator()

        # Valid web application queue
        handlers = [
            HandlerEntry(class_name="GlobalErrorHandler", full_class_path="nablarch.fw.GlobalErrorHandler"),
            HandlerEntry(class_name="HttpResponseHandler", full_class_path="nablarch.fw.HttpResponseHandler"),
            HandlerEntry(
                class_name="DbConnectionManagementHandler",
                full_class_path="nablarch.common.handler.DbConnectionManagementHandler",
            ),
            HandlerEntry(
                class_name="TransactionManagementHandler",
                full_class_path="nablarch.common.handler.TransactionManagementHandler",
            ),
            HandlerEntry(
                class_name="HttpRequestJavaPackageMapping",
                full_class_path="nablarch.fw.HttpRequestJavaPackageMapping",
            ),
        ]

        report = validator.validate(handlers)
        assert report.all_satisfied is True
        assert len(report.violations) == 0

    def test_c01_transaction_before_db_fails(self) -> None:
        """C-01: Transaction before DB connection is a violation."""
        validator = ConstraintValidator()

        # Invalid: TransactionManagementHandler before DbConnectionManagementHandler
        handlers = [
            HandlerEntry(
                class_name="TransactionManagementHandler",
                full_class_path="nablarch.common.handler.TransactionManagementHandler",
            ),
            HandlerEntry(
                class_name="DbConnectionManagementHandler",
                full_class_path="nablarch.common.handler.DbConnectionManagementHandler",
            ),
        ]

        result = validator.check_constraint("C-01", handlers)
        assert result.satisfied is False
        assert "TransactionManagementHandler" in result.details
        assert "must be after" in result.details

    def test_c02_dispatch_not_last_fails(self) -> None:
        """C-02: Dispatch handler not at end is a violation."""
        validator = ConstraintValidator()

        # Invalid: Dispatch handler not last
        handlers = [
            HandlerEntry(
                class_name="HttpRequestJavaPackageMapping",
                full_class_path="nablarch.fw.HttpRequestJavaPackageMapping",
            ),
            HandlerEntry(class_name="HttpResponseHandler", full_class_path="nablarch.fw.HttpResponseHandler"),
        ]

        result = validator.check_constraint("C-02", handlers)
        assert result.satisfied is False
        assert "must be last" in result.details

    def test_c07_loop_before_multithread_fails(self) -> None:
        """C-07: LoopHandler before MultiThreadExecutionHandler is a violation."""
        validator = ConstraintValidator()

        # Invalid: LoopHandler before MultiThreadExecutionHandler
        handlers = [
            HandlerEntry(class_name="LoopHandler", full_class_path="nablarch.fw.LoopHandler"),
            HandlerEntry(
                class_name="MultiThreadExecutionHandler",
                full_class_path="nablarch.fw.MultiThreadExecutionHandler",
            ),
        ]

        result = validator.check_constraint("C-07", handlers)
        assert result.satisfied is False
        assert "must be after" in result.details

    def test_c08_dataread_before_loop_fails(self) -> None:
        """C-08: DataReadHandler before LoopHandler is a violation."""
        validator = ConstraintValidator()

        # Invalid: DataReadHandler before LoopHandler
        handlers = [
            HandlerEntry(class_name="DataReadHandler", full_class_path="nablarch.fw.DataReadHandler"),
            HandlerEntry(class_name="LoopHandler", full_class_path="nablarch.fw.LoopHandler"),
        ]

        result = validator.check_constraint("C-08", handlers)
        assert result.satisfied is False
        assert "must be after" in result.details

    def test_c09_global_error_not_near_top_warns(self) -> None:
        """C-09: GlobalErrorHandler not near top produces warning."""
        validator = ConstraintValidator()

        # GlobalErrorHandler far from top (position 5)
        handlers = [
            HandlerEntry(class_name="Handler1", full_class_path="a.Handler1"),
            HandlerEntry(class_name="Handler2", full_class_path="a.Handler2"),
            HandlerEntry(class_name="Handler3", full_class_path="a.Handler3"),
            HandlerEntry(class_name="Handler4", full_class_path="a.Handler4"),
            HandlerEntry(class_name="Handler5", full_class_path="a.Handler5"),
            HandlerEntry(class_name="GlobalErrorHandler", full_class_path="nablarch.fw.GlobalErrorHandler"),
        ]

        result = validator.check_constraint("C-09", handlers)
        # C-09 is a warning, so it's still "satisfied" but with a warning detail
        assert result.satisfied is True
        assert "Warning" in result.details or "should be near top" in result.details

    def test_empty_handler_list(self) -> None:
        """Validate empty handler list."""
        validator = ConstraintValidator()

        handlers = []

        report = validator.validate(handlers)
        # Empty list should pass all constraints (N/A)
        assert report.all_satisfied is True

    def test_all_satisfied_property(self) -> None:
        """ValidationReport.all_satisfied reflects constraint results."""
        # All satisfied
        results = [
            ConstraintResult(constraint_id="C-01", description="Test", satisfied=True),
            ConstraintResult(constraint_id="C-02", description="Test", satisfied=True),
        ]
        report = ValidationReport(results=results)
        assert report.all_satisfied is True

        # One violation
        results_with_violation = [
            ConstraintResult(constraint_id="C-01", description="Test", satisfied=True),
            ConstraintResult(constraint_id="C-02", description="Test", satisfied=False),
        ]
        report_with_violation = ValidationReport(results=results_with_violation)
        assert report_with_violation.all_satisfied is False

    def test_violations_property(self) -> None:
        """ValidationReport.violations filters to failed constraints."""
        results = [
            ConstraintResult(constraint_id="C-01", description="Test", satisfied=True),
            ConstraintResult(constraint_id="C-02", description="Test", satisfied=False),
            ConstraintResult(constraint_id="C-03", description="Test", satisfied=False),
        ]
        report = ValidationReport(results=results)
        violations = report.violations

        assert len(violations) == 2
        assert all(not v.satisfied for v in violations)
        assert violations[0].constraint_id == "C-02"
        assert violations[1].constraint_id == "C-03"
