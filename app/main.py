from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger
from app.api import endpoints
from app.core.gitops import gitops
from app.core.config import settings
from app.core.cortex import cortex

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Exocortex Engine...")
    logger.info(f"Configuration: Repo={settings.git_repo_url}, MinIO={settings.minio_endpoint}")
    logger.info(f"Cortex Logic Layer: Active")
    
    # Bootstrap Git/DVC
    try:
        gitops.bootstrap()
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Exocortex Engine...")

app = FastAPI(
    title="Exocortex Engine",
    description="Sovereign AI Engine for Home Assistant",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(endpoints.router, prefix="/api", tags=["data"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
