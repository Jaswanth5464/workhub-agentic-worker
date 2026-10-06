import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from workhub_project.controllers.hr_router import router as hr_router

app = FastAPI(
    title="WorkHub HR API",
    description="Backend API for the WorkHub Frontend Dashboard",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hr_router, prefix="/api/hr", tags=["HR API"])
