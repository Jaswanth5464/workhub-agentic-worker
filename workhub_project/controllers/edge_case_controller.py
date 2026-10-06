"""
Edge-Case Simulation & Chaos Configuration Controller for WorkHub Web.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()

# Global Edge Case Simulation State
edge_case_config = {
    "enabled": False,
    "network_delay_ms": 0,
    "simulate_session_expiry": False,
    "random_server_error_rate": 0.0,
    "button_disabled_delay_ms": 0,
    "stale_dom_simulation": False
}


class EdgeCaseUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    network_delay_ms: Optional[int] = None
    simulate_session_expiry: Optional[bool] = None
    random_server_error_rate: Optional[float] = None
    button_disabled_delay_ms: Optional[int] = None
    stale_dom_simulation: Optional[bool] = None


@router.get("/config")
async def get_edge_case_config() -> Dict[str, Any]:
    return {"status": "ok", "config": edge_case_config}


@router.post("/config")
async def update_edge_case_config(req: EdgeCaseUpdateRequest) -> Dict[str, Any]:
    global edge_case_config
    if req.enabled is not None:
        edge_case_config["enabled"] = req.enabled
    if req.network_delay_ms is not None:
        edge_case_config["network_delay_ms"] = req.network_delay_ms
    if req.simulate_session_expiry is not None:
        edge_case_config["simulate_session_expiry"] = req.simulate_session_expiry
    if req.random_server_error_rate is not None:
        edge_case_config["random_server_error_rate"] = req.random_server_error_rate
    if req.button_disabled_delay_ms is not None:
        edge_case_config["button_disabled_delay_ms"] = req.button_disabled_delay_ms
    if req.stale_dom_simulation is not None:
        edge_case_config["stale_dom_simulation"] = req.stale_dom_simulation
        
    return {"status": "updated", "config": edge_case_config}
