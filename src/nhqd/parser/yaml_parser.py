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
        raise NotImplementedError

    def parse_string(self, yaml_content: str) -> ProjectRequirements:
        """Parse YAML requirements from a string.

        Args:
            yaml_content: YAML content as a string.

        Returns:
            Parsed project requirements.
        """
        raise NotImplementedError

    def _parse_raw(self, data: dict[str, Any]) -> ProjectRequirements:
        """Convert raw YAML dict to ProjectRequirements.

        Args:
            data: Raw parsed YAML dictionary.

        Returns:
            Structured project requirements.
        """
        raise NotImplementedError

    def _validate(self, data: dict[str, Any]) -> None:
        """Validate required fields in the raw YAML data.

        Args:
            data: Raw parsed YAML dictionary.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        raise NotImplementedError
