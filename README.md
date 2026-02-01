# Nablarch Handler Queue Designer (NHQD)

Automated handler queue configuration tool for the [Nablarch](https://nablarch.github.io/) framework.

## Overview

NHQD generates optimal Nablarch handler queue configurations from structured YAML requirements. It uses a rule-based inference engine with DAG-based topological sorting to ensure all handler ordering constraints are satisfied.

### Supported Application Types

| Type | Description |
|------|-------------|
| `web` | Web applications (HTML/JSP) |
| `rest` | RESTful web services (JAX-RS) |
| `batch` | On-demand batch applications |
| `batch_resident` | Resident batch applications |
| `mom_messaging` | MOM-based messaging |
| `http_messaging` | HTTP-based messaging |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Nablarch Handler Queue Designer              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │   Parser    │──→│  Rule Engine  │──→│  Generator   │  │
│  │  (YAML)    │   │  (DAG Sort)  │   │  (XML/MD)    │  │
│  └────────────┘   └──────┬───────┘   └──────────────┘  │
│                          │                               │
│                ┌─────────┴─────────┐                     │
│                │  Knowledge Base    │                     │
│                │  - Handler Catalog │                     │
│                │  - Constraints     │                     │
│                │  - Patterns        │                     │
│                └───────────────────┘                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Generate handler queue from requirements

```bash
nhqd generate examples/web_app_requirements.yaml -o output/
```

### Validate existing configuration

```bash
nhqd validate path/to/handler-queue-config.xml
```

### List available handlers

```bash
nhqd list-handlers
```

## Requirements File Format

```yaml
project:
  name: "My Application"
  type: web  # web | rest | batch | batch_resident | mom_messaging | http_messaging

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
```

See `examples/web_app_requirements.yaml` for a complete example.

## Ordering Constraints

NHQD enforces the following handler ordering constraints:

| ID | Rule | Severity |
|----|------|----------|
| C-01 | Transaction must be after DB connection | Critical |
| C-02 | Dispatch handler must be last | Critical |
| C-03 | RoutesMapping inner handlers must be inside RoutesMapping | Critical |
| C-04 | HTTP messaging parser must be after response handler | Critical |
| C-05 | HTTP messaging parser must be after thread context | Critical |
| C-06 | Health check must be after response handler | Warning |
| C-07 | LoopHandler must be after MultiThreadExecutionHandler | Critical |
| C-08 | DataReadHandler must be after LoopHandler | Critical |
| C-09 | GlobalErrorHandler should be near top | Warning |
| C-10 | Interceptor order must be explicit | Warning |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
