from typing import Dict, Any, List, Optional
from workhub_project.repositories.base import BaseRepository

class BaseService:
    """
    Generic Service layer pattern.
    Encapsulates business logic before delegating to the repository.
    """
    def __init__(self, repository: BaseRepository):
        self.repository = repository

    def get_all(self, limit: int = 1000, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.repository.get_all(limit=limit, filters=filters)

    def search(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repository.search(query=query, filters=filters, limit=limit)

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.repository.get_by_id(record_id)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Perform any business validation here if necessary
        return self.repository.create(data)

    def update(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # Perform any business validation here if necessary
        return self.repository.update(record_id, data)
        
    def delete(self, record_id: str) -> bool:
        return self.repository.delete(record_id)
