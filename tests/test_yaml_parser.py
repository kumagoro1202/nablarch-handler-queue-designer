"""Tests for NHQD YAML requirements parser."""

import pytest
import yaml

from nhqd.parser.yaml_parser import (
    ProjectRequirements,
    YamlRequirementsParser,
)


class TestYamlRequirementsParser:
    """Tests for YamlRequirementsParser."""

    def test_parse_minimal_web_requirements(self) -> None:
        """Parse a minimal web application requirements file."""
        yaml_content = """
project:
  name: "Minimal App"
  type: web
"""
        parser = YamlRequirementsParser()
        result = parser.parse_string(yaml_content)

        assert result.name == "Minimal App"
        assert result.app_type == "web"
        assert result.database.enabled is False
        assert result.authentication.enabled is False

    def test_parse_full_web_requirements(self) -> None:
        """Parse a complete web application requirements file with all options."""
        yaml_content = """
project:
  name: "Full Featured App"
  type: web

requirements:
  database:
    enabled: true
    type: PostgreSQL
    transaction: required

  authentication:
    enabled: true
    type: session
    login_check: true

  security:
    csrf_protection: true
    secure_headers: true
    cors: false

  session:
    enabled: true
    store: db

  logging:
    access_log: true
    sql_log: true
"""
        parser = YamlRequirementsParser()
        result = parser.parse_string(yaml_content)

        assert result.name == "Full Featured App"
        assert result.app_type == "web"
        assert result.database.enabled is True
        assert result.database.db_type == "PostgreSQL"
        assert result.database.transaction == "required"
        assert result.authentication.enabled is True
        assert result.authentication.auth_type == "session"
        assert result.authentication.login_check is True
        assert result.security.csrf_protection is True
        assert result.security.secure_headers is True
        assert result.security.cors is False
        assert result.session.enabled is True
        assert result.session.store == "db"
        assert result.logging.access_log is True
        assert result.logging.sql_log is True

    def test_parse_rest_requirements(self) -> None:
        """Parse REST API requirements."""
        yaml_content = """
project:
  name: "REST API"
  type: rest

requirements:
  database:
    enabled: true
    type: Oracle
    transaction: required
"""
        parser = YamlRequirementsParser()
        result = parser.parse_string(yaml_content)

        assert result.name == "REST API"
        assert result.app_type == "rest"
        assert result.database.enabled is True

    def test_parse_batch_requirements(self) -> None:
        """Parse batch application requirements."""
        yaml_content = """
project:
  name: "Batch Job"
  type: batch

requirements:
  database:
    enabled: true
    type: DB2
    transaction: required

  logging:
    sql_log: true
"""
        parser = YamlRequirementsParser()
        result = parser.parse_string(yaml_content)

        assert result.name == "Batch Job"
        assert result.app_type == "batch"
        assert result.database.enabled is True
        assert result.logging.sql_log is True

    def test_parse_with_custom_handlers(self) -> None:
        """Parse requirements including custom handler definitions."""
        yaml_content = """
project:
  name: "Custom App"
  type: web

requirements:
  custom_handlers:
    - name: "AuditLogHandler"
      position: "after:TransactionManagementHandler"
      description: "Records audit log entries"
    - name: "CacheHandler"
      position: "before:DatabaseConnectionManagementHandler"
      description: "Cache layer"
"""
        parser = YamlRequirementsParser()
        result = parser.parse_string(yaml_content)

        assert result.name == "Custom App"
        assert len(result.custom_handlers) == 2
        assert result.custom_handlers[0].name == "AuditLogHandler"
        assert result.custom_handlers[0].position == "after:TransactionManagementHandler"
        assert result.custom_handlers[0].description == "Records audit log entries"
        assert result.custom_handlers[1].name == "CacheHandler"

    def test_parse_invalid_app_type_raises_error(self) -> None:
        """Reject invalid application type."""
        yaml_content = """
project:
  name: "Invalid App"
  type: invalid_type
"""
        parser = YamlRequirementsParser()

        with pytest.raises(ValueError, match="Invalid application type"):
            parser.parse_string(yaml_content)

    def test_parse_missing_project_name_raises_error(self) -> None:
        """Reject requirements without project name."""
        yaml_content = """
project:
  type: web
"""
        parser = YamlRequirementsParser()

        with pytest.raises(ValueError, match="Missing required field: project.name"):
            parser.parse_string(yaml_content)

    def test_parse_empty_file_raises_error(self) -> None:
        """Reject empty YAML file."""
        yaml_content = ""

        parser = YamlRequirementsParser()

        with pytest.raises(ValueError, match="Empty YAML content"):
            parser.parse_string(yaml_content)

    def test_parse_malformed_yaml_raises_error(self) -> None:
        """Reject malformed YAML content."""
        yaml_content = """
project:
  name: "Malformed
  type: web
"""
        parser = YamlRequirementsParser()

        with pytest.raises(yaml.YAMLError):
            parser.parse_string(yaml_content)
