from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from contextlib import asynccontextmanager
import uvicorn  # type: ignore
import logging
from api.github_routes import router as github_router
from api.chatbot_routes import router as chatbot_router
from api.embedding_routes import router as embedding_router
from api.report_routes import router as report_router
from api.jira_routes import router as jira_router
from api.user_story_routes import router as user_story_router

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):  # unused param by design
    logger.info("Starting up Dobb.ai Backend API...")
    yield
    logger.info("Shutting down Dobb.ai Backend API...")

app = FastAPI(
    title="Dobb.ai Backend API",
    description="A FastAPI server for Dobb.ai with GitHub MCP integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(github_router)
app.include_router(chatbot_router)
app.include_router(embedding_router)
app.include_router(report_router)
app.include_router(jira_router)
app.include_router(user_story_router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Dobb.ai Backend API",
        "status": "running",
        "features": [
            "GitHub MCP Integration",
            "Jira MCP Integration",
        ],
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
