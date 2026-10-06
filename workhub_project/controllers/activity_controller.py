from fastapi import APIRouter
from typing import Dict, Any, List
from workhub_project.database.db_utils import get_recent_audit_logs

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]], include_in_schema=False)
@router.get("/", response_model=List[Dict[str, Any]])
def get_activities(limit: int = 20):
    return get_recent_audit_logs(limit=limit)
