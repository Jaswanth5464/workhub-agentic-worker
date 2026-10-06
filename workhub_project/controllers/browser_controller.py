"""
FastAPI Automation API Controller for Autonomous Browser Agent.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from workhub_project.browser.browser_manager import get_browser_manager
from workhub_project.browser.observation_tools import ObservationTools
from workhub_project.browser.interaction_tools import InteractionTools
from workhub_project.browser.wait_manager import WaitManager
from workhub_project.browser.verifier import ActionVerifier
from workhub_project.browser.recovery_manager import RecoveryManager
from workhub_project.browser.stuck_detector import StuckDetector
from workhub_project.browser.session_manager import SessionManager
from workhub_project.browser.telemetry import get_telemetry_manager

router = APIRouter()
browser_mgr = get_browser_manager()
interactor = InteractionTools()
recovery_mgr = RecoveryManager()
stuck_det = StuckDetector()
session_mgr = SessionManager()
telemetry_mgr = get_telemetry_manager()


class SessionRequest(BaseModel):
    session_id: Optional[str] = "default"
    url: Optional[str] = "http://localhost:3000/index.html"


class ObserveRequest(BaseModel):
    session_id: Optional[str] = "default"
    show_overlay: Optional[bool] = True


class ClickRequest(BaseModel):
    session_id: Optional[str] = "default"
    target: str


class FillRequest(BaseModel):
    session_id: Optional[str] = "default"
    target: str
    value: Any


class SelectRequest(BaseModel):
    session_id: Optional[str] = "default"
    target: str
    value: str


class UploadRequest(BaseModel):
    session_id: Optional[str] = "default"
    target: str
    file_path: str


class WaitRequest(BaseModel):
    session_id: Optional[str] = "default"
    condition: str
    target: Optional[str] = None
    value: Optional[str] = None
    timeout: Optional[int] = 8000


class VerifyRequest(BaseModel):
    session_id: Optional[str] = "default"
    action_name: str
    ui_target: Optional[str] = None
    expected_ui_text: Optional[str] = None
    db_query: Optional[str] = None
    db_expected_val: Optional[Any] = None


class RecoverRequest(BaseModel):
    session_id: Optional[str] = "default"
    failure_type: str
    target_url: Optional[str] = None


class ScreenshotRequest(BaseModel):
    session_id: Optional[str] = "default"
    filename: Optional[str] = None


@router.post("/session")
async def start_session(req: SessionRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    if req.url:
        await page.goto(req.url, wait_until="networkidle", timeout=10000)
    return {
        "status": "connected",
        "session_id": req.session_id,
        "url": page.url,
        "title": await page.title()
    }


@router.post("/observe")
async def observe(req: ObserveRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await ObservationTools.observe_page(page, show_overlay=req.show_overlay)


@router.post("/inspect_form")
async def inspect_form(session_id: str = "default", form_target: Optional[str] = None):
    page, _ = await browser_mgr.get_session(session_id)
    return await ObservationTools.inspect_form(page, form_target)


@router.post("/click")
async def click_element(req: ClickRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    # Check stuck detector
    stuck_status = await stuck_det.record_and_check(req.session_id, "click", req.target, page)
    res = await interactor.click(req.target, page, session_id=req.session_id)
    res["stuck_check"] = stuck_status
    return res


@router.post("/fill")
async def fill_field(req: FillRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    await stuck_det.record_and_check(req.session_id, "fill", req.target, page)
    return await interactor.fill_input(req.target, req.value, page, session_id=req.session_id)


@router.post("/select")
async def select_dropdown(req: SelectRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await interactor.select_option(req.target, req.value, page, session_id=req.session_id)


@router.post("/upload")
async def upload_document(req: UploadRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await interactor.upload_file(req.target, req.file_path, page, session_id=req.session_id)


@router.post("/wait")
async def wait_condition(req: WaitRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await WaitManager.wait_for_condition(
        page=page,
        condition=req.condition,
        target=req.target,
        value=req.value,
        timeout=req.timeout
    )


@router.post("/verify")
async def verify_action(req: VerifyRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await ActionVerifier.verify(
        page=page,
        action_name=req.action_name,
        ui_target=req.ui_target,
        expected_ui_text=req.expected_ui_text,
        db_query=req.db_query,
        db_expected_val=req.db_expected_val
    )


@router.post("/recover")
async def trigger_recovery(req: RecoverRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await recovery_mgr.recover(
        failure_type=req.failure_type,
        page=page,
        session_id=req.session_id,
        target_url=req.target_url
    )


@router.post("/screenshot")
async def take_screenshot(req: ScreenshotRequest):
    page, _ = await browser_mgr.get_session(req.session_id)
    return await ObservationTools.take_screenshot(page, filename=req.filename)


@router.get("/state")
async def get_state(session_id: str = "default"):
    page, _ = await browser_mgr.get_session(session_id)
    state = await ObservationTools.get_page_state(page)
    health = await browser_mgr.check_health(session_id)
    state["health"] = health
    return state


@router.get("/telemetry/events")
async def stream_telemetry():
    """SSE telemetry event stream."""
    return StreamingResponse(
        telemetry_mgr.subscribe(),
        media_type="text/event-stream"
    )
