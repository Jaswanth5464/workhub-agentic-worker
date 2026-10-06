from typing import Dict, Any, List, Optional
from workhub_project.repositories.task_repo import TaskRepository
from workhub_project.services.base import BaseService

class TaskService(BaseService):
    def __init__(self):
        super().__init__(TaskRepository())
