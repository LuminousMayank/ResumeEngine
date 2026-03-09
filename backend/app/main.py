"""
Caarya AI Job Fit Engine — FastAPI Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .api.routes import router

app = FastAPI(
    title="Caarya AI Job Fit Engine",
    description="Analyzes student resumes and matches them with Caarya job openings using AI.",
    version="0.1.0",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Caarya AI Job Fit Engine is running."}
