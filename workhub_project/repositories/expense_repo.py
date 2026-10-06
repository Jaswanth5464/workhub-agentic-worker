from typing import Dict, Any, List, Optional
from workhub_project.repositories.base import BaseRepository

class ExpenseRepository(BaseRepository):
    def __init__(self):
        super().__init__("expenses")
