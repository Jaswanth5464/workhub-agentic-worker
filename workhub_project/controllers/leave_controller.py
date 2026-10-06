from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from workhub_project.services.leave_service import LeaveService

router = APIRouter()
service = LeaveService()

@router.get("", response_model=List[Dict[str, Any]], include_in_schema=False)
@router.get("/", response_model=List[Dict[str, Any]])
def get_all_leaves():
    return service.get_all()

@router.get("/{id}", response_model=Dict[str, Any])
@router.get("/{id}/", response_model=Dict[str, Any], include_in_schema=False)
def get_leave_by_id(id: str):
    record = service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return record

@router.post("", response_model=Dict[str, Any], include_in_schema=False)
@router.post("/", response_model=Dict[str, Any])
def create_leave(data: Dict[str, Any]):
    return service.create(data)

@router.patch("/{id}", response_model=Dict[str, Any])
@router.patch("/{id}/", response_model=Dict[str, Any], include_in_schema=False)
def update_leave(id: str, data: Dict[str, Any]):
    existing = service.get_by_id(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Leave request not found")
    existing.update(data)
    return service.update(id, existing)

@router.delete("/{id}")
@router.delete("/{id}/", include_in_schema=False)
def delete_leave(id: str):
    success = service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return {"message": "Deleted successfully", "id": id}

