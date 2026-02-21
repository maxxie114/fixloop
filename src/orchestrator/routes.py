from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import logging

from src.common.models import (
    SystemStatus, IncidentCard, TestRun, CopilotAnswer, 
    BugToggleRequest, SimulateRequest, RunTestsRequest, CopilotAskRequest
)
from src.orchestrator.state import state
from src.orchestrator.agent_service import agent_service
from src.orchestrator.integrations.strands_agent import strands_agent_client

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/status", response_model=SystemStatus)
async def get_status():
    return state.get_status()

@router.post("/api/demo/bug", response_model=SystemStatus)
async def toggle_bug(request: BugToggleRequest):
    try:
        return await state.toggle_bug(request.enabled)
    except Exception as e:
        logger.error(f"Error toggling bug: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/api/incidents/current", response_model=Optional[IncidentCard])
async def get_current_incident():
    return state.get_current_incident()

@router.post("/api/incidents/simulate", response_model=Optional[IncidentCard])
async def simulate_incident(request: SimulateRequest):
    try:
        success = await agent_service.simulate_incident(request.mode)
        if success:
            return state.get_current_incident()
        else:
            raise HTTPException(status_code=500, detail="Failed to simulate incident")
    except Exception as e:
        logger.error(f"Error simulating incident: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/api/tests/run", response_model=TestRun)
async def run_tests(request: RunTestsRequest):
    try:
        run_id = await agent_service.run_validation_tests(request.incident_id)
        if run_id:
            return state.get_test_run(run_id)
        else:
            raise HTTPException(status_code=404, detail="Incident not found or no plan available")
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/api/tests/runs/{run_id}", response_model=Optional[TestRun])
async def get_test_run(run_id: str):
    return state.get_test_run(run_id)

@router.post("/api/copilot/ask", response_model=CopilotAnswer)
async def ask_copilot(request: CopilotAskRequest):
    try:
        return await strands_agent_client.generate_answer(
            incident_id=request.incident_id,
            question=request.question,
            context=state.get_current_incident(),
            test_run=state.get_test_run()
        )
    except Exception as e:
        logger.error(f"Error asking copilot: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/internal/datadog/webhook")
async def datadog_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"Received Datadog webhook: {payload}")
        # In a real app, parse the payload and trigger an incident
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
