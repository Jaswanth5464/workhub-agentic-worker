from typing import Dict, Any, List, Optional
from workhub_project.repositories.email_repo import EmailRepository
from workhub_project.services.base import BaseService

class EmailService(BaseService):
    def __init__(self):
        super().__init__(EmailRepository())
