from typing import Dict, Any, List, Optional
from workhub_project.repositories.benefit_repo import BenefitRepository
from workhub_project.services.base import BaseService

class BenefitService(BaseService):
    def __init__(self):
        super().__init__(BenefitRepository())
