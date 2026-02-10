# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **SMART Integrate Connector SDK** (`cdip_connector`), a Python library for building wildlife/conservation data integration connectors that pull data from external sources and push it to the CDIP (Conservation Data Integration Platform) Sensors API. The project is part of the Gundi ecosystem and is in maintenance/deprecated status (superseded by [gundi-integration-action-runner](https://github.com/PADAS/gundi-integration-action-runner)).

## Build & Development

Package manager: **uv** (pyproject.toml with hatchling build backend, uv.lock present)

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/

# Run a single test
uv run pytest tests/test_portalapi.py::TestPortalApi::test_create

# Lint
uv run pylint cdip_connector/

# Format
uv run black cdip_connector/
```

Python requirement: `>=3.8`. The .venv uses Python 3.10.

## Architecture

### Core Library (`cdip_connector/core/`)

- **`connector_base.py`** — The central module. Contains `AbstractConnector` which all connectors subclass. Implements the ETL pipeline: `execute()` → `main()` → `extract_load()` → `extract()` (abstract) + `load()`. Also contains job partitioning logic (`calculate_partition`, `filter_items_for_task`) for running parallel instances via Kubernetes CronJobs or Cloud Run Jobs.
- **`cdip_settings.py`** — All configuration via environment variables using `environs`. Includes Keycloak auth settings, API endpoints, GCP settings, and job partitioning (JOB_COMPLETION_INDEX/COUNT). Can load from a custom env file via `CDIP_SDK_ENVFILE`.
- **`schemas/__init__.py`** — Re-exports all schemas from `gundi_core.schemas` for backward compatibility.
- **`routing.py`** — Pub/Sub topic name definitions for the observation processing pipeline.
- **`cloudstorage.py`** — Abstract `CloudStorage` with `GoogleCloudStorage` and `LocalStorage` implementations for camera trap image handling.
- **`tracing.py`** — OpenTelemetry distributed tracing setup with GCP Cloud Trace export.
- **`logconfig.py`** — JSON-formatted logging configuration. Can be overridden by creating a `local_log_settings.py` module.

### Connector Pattern

Connectors subclass `AbstractConnector` and implement `extract()` as an async generator yielding lists of data records. See `connector_skeleton.py` for the template. The base class handles:
1. Fetching authorized integrations from the Gundi Portal API
2. Partitioning integrations across parallel job instances (hash-based on integration UUID)
3. Batched HTTP POST to the Sensors API with exponential backoff retry
4. State management via `update_state()`

### Key External Dependencies

- **`gundi-client`** — `PortalApi` for portal interactions (auth, integrations, device states)
- **`gundi-core`** — Shared schemas (`IntegrationInformation`, `CDIPBaseModel`, `Position`, etc.)
- **`google-cloud-pubsub`** / **`google-cloud-storage`** — GCP integrations
- **`httpx`** — Async HTTP client for Sensors API calls
- **`backoff`** — Retry logic on HTTP errors

### Job Partitioning

When `JOB_COMPLETION_INDEX` and `JOB_COMPLETION_COUNT` are set (via Kubernetes or Cloud Run), integrations are distributed across job instances using SHA1 hash of the integration UUID modulo partition count. This is configured in `cdip_settings.py` and applied in `connector_base.py:filter_items_for_task()`.
