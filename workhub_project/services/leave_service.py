from typing import Dict, Any, List, Optional
from workhub_project.repositories.leave_repo import LeaveRepository
from workhub_project.services.base import BaseService

class LeaveService(BaseService):
    def __init__(self):
        super().__init__(LeaveRepository())
