from typing import Dict, Any, List, Optional
from workhub_project.repositories.document_repo import DocumentRepository
from workhub_project.services.base import BaseService

class DocumentService(BaseService):
    def __init__(self):
        super().__init__(DocumentRepository())
