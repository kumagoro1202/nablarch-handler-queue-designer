"""YAML requirements parser for NHQD.

Parses structured YAML requirement files into internal representation
used by the rule engine for handler queue generation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DatabaseRequirements:
    """Database-related requirements."""

    enabled: bool = False
    db_type: str = ""
    transaction: str = "none"


@dataclass
class AuthenticationRequirements:
    """Authentication-related requirements."""

    enabled: bool = False
    auth_type: str = "none"
    login_check: bool = False


@dataclass
class SecurityRequirements:
    """Security-related requirements."""

    csrf_protection: bool = False
    secure_headers: bool = False
    cors: bool = False


@dataclass
class SessionRequirements:
    """Session management requirements."""

    enabled: bool = False
    store: str = "http_session"


@dataclass
class LoggingRequirements:
    """Logging requirements."""

    access_log: bool = False
    sql_log: bool = False


@dataclass
class CustomHandler:
    """Custom handler definition."""

    name: str = ""
    position: str = ""
    description: str = ""


@dataclass
class ProjectRequirements:
    """Parsed project requirements for handler queue generation."""

    name: str = ""
    app_type: str = "web"
    database: DatabaseRequirements = field(default_factory=DatabaseRequirements)
    authentication: AuthenticationRequirements = field(default_factory=AuthenticationRequirements)
    security: SecurityRequirements = field(default_factory=SecurityRequirements)
    session: SessionRequirements = field(default_factory=SessionRequirements)
    logging: LoggingRequirements = field(default_factory=LoggingRequirements)
    custom_handlers: list[CustomHandler] = field(default_factory=list)


class YamlRequirementsParser:
    """Parser for NHQD YAML requirement files.

    Reads a structured YAML file describing application requirements
    and produces a ProjectRequirements object for the rule engine.
    """

    def parse_file(self, file_path: Path) -> ProjectRequirements:
        """Parse a YAML requirements file.

        Args:
            file_path: Path to the YAML requirements file.

        Returns:
            Parsed project requirements.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the YAML is malformed.
            ValueError: If required fields are missing.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse_string(content)

    def parse_string(self, yaml_content: str) -> ProjectRequirements:
        """Parse YAML requirements from a string.

        Args:
            yaml_content: YAML content as a string.

        Returns:
            Parsed project requirements.
        """
        data = yaml.safe_load(yaml_content)

        if data is None:
            raise ValueError("Empty YAML content")

        self._validate(data)
        return self._parse_raw(data)

    def _parse_raw(self, data: dict[str, Any]) -> ProjectRequirements:
        """Convert raw YAML dict to ProjectRequirements.

        Args:
            data: Raw parsed YAML dictionary.

        Returns:
            Structured project requirements.
        """
        project = data["project"]
        requirements = data.get("requirements", {})

        # Parse database requirements
        db_data = requirements.get("database", {})
        database = DatabaseRequirements(
            enabled=db_data.get("enabled", False),
            db_type=db_data.get("type", ""),
            transaction=db_data.get("transaction", "none"),
        )

        # Parse authentication requirements
        auth_data = requirements.get("authentication", {})
        authentication = AuthenticationRequirements(
            enabled=auth_data.get("enabled", False),
            auth_type=auth_data.get("type", "none"),
            login_check=auth_data.get("login_check", False),
        )

        # Parse security requirements
        sec_data = requirements.get("security", {})
        security = SecurityRequirements(
            csrf_protection=sec_data.get("csrf_protection", False),
            secure_headers=sec_data.get("secure_headers", False),
            cors=sec_data.get("cors", False),
        )

        # Parse session requirements
        session_data = requirements.get("session", {})
        session = SessionRequirements(
            enabled=session_data.get("enabled", False),
            store=session_data.get("store", "http_session"),
        )

        # Parse logging requirements
        logging_data = requirements.get("logging", {})
        logging = LoggingRequirements(
            access_log=logging_data.get("access_log", False),
            sql_log=logging_data.get("sql_log", False),
        )

        # Parse custom handlers
        custom_handlers_data = requirements.get("custom_handlers", [])
        custom_handlers = [
            CustomHandler(
                name=handler.get("name", ""),
                position=handler.get("position", ""),
                description=handler.get("description", ""),
            )
            for handler in custom_handlers_data
        ]

        return ProjectRequirements(
            name=project["name"],
            app_type=project.get("type", "web"),
            database=database,
            authentication=authentication,
            security=security,
            session=session,
            logging=logging,
            custom_handlers=custom_handlers,
        )

    def _validate(self, data: dict[str, Any]) -> None:
        """Validate required fields in the raw YAML data.

        Args:
            data: Raw parsed YAML dictionary.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if not isinstance(data, dict):
            raise ValueError("YAML data must be a dictionary")

        if "project" not in data:
            raise ValueError("Missing required field: project")

        project = data["project"]
        if not isinstance(project, dict):
            raise ValueError("Field 'project' must be a dictionary")

        if "name" not in project:
            raise ValueError("Missing required field: project.name")

        if not project["name"]:
            raise ValueError("Field 'project.name' cannot be empty")

        if "type" in project:
            valid_types = ["web", "rest", "batch", "batch_resident", "mom_messaging", "http_messaging"]
            if project["type"] not in valid_types:
                raise ValueError(f"Invalid application type: {project['type']}. Must be one of {valid_types}")
