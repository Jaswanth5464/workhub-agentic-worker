from typing import Dict, Any, List, Optional
from workhub_project.repositories.expense_repo import ExpenseRepository
from workhub_project.services.base import BaseService

class ExpenseService(BaseService):
    def __init__(self):
        super().__init__(ExpenseRepository())
