from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from workhub_project.services.benefit_service import BenefitService

router = APIRouter()
service = BenefitService()

@router.get("/", response_model=List[Dict[str, Any]])
def get_all_benefits():
    return service.get_all()

@router.get("/{id}", response_model=Dict[str, Any])
def get_benefit_by_id(id: str):
    record = service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record

@router.post("/", response_model=Dict[str, Any])
def create_benefit(data: Dict[str, Any]):
    return service.create(data)

@router.patch("/{id}", response_model=Dict[str, Any])
def update_benefit(id: str, data: Dict[str, Any]):
    existing = service.get_by_id(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    existing.update(data)
    return service.update(id, existing)

@router.delete("/{id}")
def delete_benefit(id: str):
    success = service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted successfully", "id": id}
