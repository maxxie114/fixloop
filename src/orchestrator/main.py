import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.orchestrator.routes import router as api_router
from src.orchestrator.ws_routes import router as ws_router
from src.orchestrator.agent_service import agent_service
from src.common.config import ORCH_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Recovery Validation Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting orchestrator API...")
    await agent_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down orchestrator API...")
    await agent_service.stop()

@app.get("/")
async def root():
    return {
        "service": "Recovery Validation Orchestrator",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=ORCH_PORT)
