"""
REST API server for the Cyber AI Orchestrator.

Provides endpoints for:
- Status and health
- Session management
- Task execution
- Findings retrieval
- Memory search
- Model listing
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from ..memory.memory_manager import MemoryManager
from ..policies.policy_engine import PolicyEngine
from ..routing.model_router import ModelRouter
from ..tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the FastAPI application."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.warning("FastAPI not installed - API server unavailable")
        return None

    app = FastAPI(title="Cyber AI Orchestrator API", version="0.1.0")

    memory = MemoryManager()
    policy = PolicyEngine()
    model_router = ModelRouter()
    tool_registry = ToolRegistry()

    @app.get("/")
    async def root():
        return {"platform": "Cyber AI Orchestrator", "version": "0.1.0", "status": "running"}

    @app.get("/status")
    async def status():
        return {
            "platform": "Cyber AI Orchestrator",
            "sessions": len(memory.list_sessions()),
            "tools_registered": len(tool_registry.list_tools()),
            "targets_authorized": len(policy.list_authorized_targets()),
            "models": len(model_router.get_all_routes()),
        }

    @app.get("/targets")
    async def list_targets():
        return {"targets": policy.list_targets()}

    @app.get("/targets/authorized")
    async def list_authorized():
        return {"targets": policy.list_authorized_targets()}

    @app.get("/sessions")
    async def list_sessions():
        return {"sessions": memory.list_sessions()}

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        session = memory.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"session": session}

    @app.get("/findings")
    async def get_findings(status: str = None):
        findings = memory.get_findings(status=status)
        return {"findings": findings}

    @app.get("/memory/search")
    async def search_memory(query: str, limit: int = 10):
        results = memory.search_experiences(query, limit=limit)
        return {"results": results}

    @app.get("/tools")
    async def list_tools():
        return {"tools": tool_registry.to_dict()["tools"]}

    @app.get("/models")
    async def list_models():
        routes = model_router.get_all_routes()
        return {"routes": routes}

    logger.info("API server created")
    return app
