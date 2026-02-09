import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi import Request
from api import api_router
from config.settings import API_HOST, API_PORT
from database.connection import create_db_and_tables
from database.seed import seed_database
from database.seed_scoring_prompts import seed_scoring_prompts
from utils.logger import get_logger
from api.document.websocket_manager import ws_manager
from api.scoring.websocket_manager import scoring_ws_manager
from api.connector.websocket_manager import connector_ws_manager

# Initialize logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown"""
    logger.info("Starting application...")
    create_db_and_tables()
    logger.info("Database tables created/verified")
    # seed_database()
    logger.info("Database seeded with roles and permissions")
    # seed_scoring_prompts()
    logger.info("Scoring prompts seeded into database")
    # Start WebSocket Redis listeners for multi-worker support
    await ws_manager.start_listener()
    await scoring_ws_manager.start_listener()
    await connector_ws_manager.start_listener()
    yield
    # Stop WebSocket Redis listeners
    await ws_manager.stop_listener()
    await scoring_ws_manager.stop_listener()
    await connector_ws_manager.stop_listener()
    logger.info("Shutting down application...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="BDE",
    version="1.0.0",
    description="BDE Backend API",
    lifespan=lifespan
)

# Include API routes
app.include_router(api_router, prefix="/api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "https://bde-webapp-dev.azurewebsites.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the build path for Vite (frontend/dist)
BUILD_PATH = "frontend/dist"

# Mount assets folder (Vite output)
app.mount("/assets", StaticFiles(directory=f"{BUILD_PATH}/assets"), name="assets")

# Serve index.html manually via Jinja2Templates
templates = Jinja2Templates(directory=BUILD_PATH)


# after all other routes
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_catch_all(request: Request, full_path: str):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
