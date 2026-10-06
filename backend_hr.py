import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from workhub_project.controllers.hr_router import router as hr_router
from workhub_project.controllers.browser_controller import router as browser_router
from workhub_project.controllers.edge_case_controller import router as edge_case_router
from workhub_project.database.db_utils import init_db

# Initialize database schema and audit log table
init_db()

app = FastAPI(
    title="WorkHub HR & Browser Automation API",
    description="Backend API and Browser Automation Control Service for WorkHub Web",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hr_router, prefix="/api/hr", tags=["HR API"])
app.include_router(browser_router, prefix="/browser", tags=["Browser Automation API"])
app.include_router(edge_case_router, prefix="/api/edge-cases", tags=["Edge Case Simulator"])

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "workhub_project", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


