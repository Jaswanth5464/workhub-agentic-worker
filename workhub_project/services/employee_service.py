from typing import Dict, Any, List, Optional
from workhub_project.repositories.employee_repo import EmployeeRepository
from workhub_project.services.base import BaseService

class EmployeeService(BaseService):
    def __init__(self):
        super().__init__(EmployeeRepository())
