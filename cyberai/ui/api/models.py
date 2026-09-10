"""Model endpoints.

    GET   /api/v1/models         model registry
    GET   /api/v1/models/routing task-type → alias routing table
    PATCH /api/v1/models/routing update one route
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cyberai.ui.api._helpers import require_fields
from cyberai.ui.server import EVENT_BUS

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("")
async def list_models():
    from cyberai.llm_gateway import LLMGateway
    gw = LLMGateway()
    try:
        return {"models": gw.list_registry()}
    finally:
        pass


@router.get("/routing")
async def get_routing():
    from cyberai.orchestrator.routing.model_router import ModelRouter
    mr = ModelRouter()
    routes = mr.get_all_routes()
    return {"routes": routes}


@router.patch("/routing")
async def update_routing(body: Dict[str, Any]):
    require_fields(body, "task_type", "model_alias")
    task_type = str(body["task_type"]).strip()
    model_alias = str(body["model_alias"]).strip()
    from cyberai.orchestrator.routing.model_router import ModelRouter
    try:
        mr = ModelRouter()
        mr.update_route(task_type, model_alias)
        import yaml as _yaml
        with open(mr.config_path, "w", encoding="utf-8") as f:
            _yaml.dump({"routes": mr.get_all_routes()}, f,
                       default_flow_style=False)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
    EVENT_BUS.publish("audit", {
        "actor": "OPERATOR", "agent": "-", "tool": "model_router",
        "target": "-", "action": f"route {task_type} -> {model_alias}",
        "result": "SUCCESS", "session": "-",
    })
    return {"ok": True, "routes": mr.get_all_routes()}
