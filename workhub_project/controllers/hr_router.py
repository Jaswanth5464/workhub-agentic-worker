from fastapi import APIRouter
from workhub_project.controllers.employee_controller import router as employees_router
from workhub_project.controllers.expense_controller import router as expenses_router
from workhub_project.controllers.task_controller import router as tasks_router
from workhub_project.controllers.leave_controller import router as leaves_router
from workhub_project.controllers.document_controller import router as documents_router
from workhub_project.controllers.email_controller import router as emails_router
from workhub_project.controllers.benefit_controller import router as benefits_router

router = APIRouter()
router.include_router(employees_router, prefix="/employees", tags=["Employee"])
router.include_router(expenses_router, prefix="/expenses", tags=["Expense"])
router.include_router(tasks_router, prefix="/tasks", tags=["Task"])
router.include_router(leaves_router, prefix="/leaves", tags=["Leave"])
router.include_router(documents_router, prefix="/documents", tags=["Document"])
router.include_router(emails_router, prefix="/emails", tags=["Email"])
router.include_router(benefits_router, prefix="/benefits", tags=["Benefit"])
