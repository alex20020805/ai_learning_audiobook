"""Runnable loopback application factory for the private Mac pilot."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from ai_learning_audiobook.app import create_app


def create_runtime_app() -> FastAPI:
    """Create the Local Orchestrator using operator-configured durable storage.

    Inputs:
        None; reads `AI_AUDIOBOOK_DATA_ROOT` from the process environment when present.
    Functionality:
        Resolves the durable data root, defaulting to a repository-local ignored work area,
        and delegates construction to the tested application factory.
    Outputs:
        A configured FastAPI application for a loopback-only Uvicorn process.
    Failures:
        Propagates invalid path and filesystem failures from application construction.
    """
    data_root = Path(os.environ.get("AI_AUDIOBOOK_DATA_ROOT", "work/local-orchestrator"))
    return create_app(data_root=data_root)
