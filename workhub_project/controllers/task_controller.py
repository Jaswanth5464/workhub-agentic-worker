from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from workhub_project.services.task_service import TaskService

router = APIRouter()
service = TaskService()

@router.get("/", response_model=List[Dict[str, Any]])
def get_all_tasks():
    return service.get_all()

@router.get("/{id}", response_model=Dict[str, Any])
def get_task_by_id(id: str):
    record = service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record

@router.post("/", response_model=Dict[str, Any])
def create_task(data: Dict[str, Any]):
    return service.create(data)

@router.patch("/{id}", response_model=Dict[str, Any])
def update_task(id: str, data: Dict[str, Any]):
    existing = service.get_by_id(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    existing.update(data)
    return service.update(id, existing)

@router.delete("/{id}")
def delete_task(id: str):
    success = service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted successfully", "id": id}
