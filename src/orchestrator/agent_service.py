import asyncio
import uuid
from datetime import datetime
from typing import Optional
import logging

from src.common.models import StatusEnum, TestRunStatusEnum, TestStatusEnum
from src.orchestrator.state import state
from src.orchestrator.integrations.minimax_client import minimax_client
from src.orchestrator.integrations.testsprite_client import testsprite_adapter
from src.orchestrator.integrations.datadog_detection import datadog_client

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self):
        self.running = False
        self.incident_detection_task = None
        self.plan_generation_task = None
        self.test_execution_task = None

    async def start(self):
        if self.running:
            return
        
        self.running = True
        logger.info("Agent service started")
        
        self.incident_detection_task = asyncio.create_task(self._incident_detection_loop())

    async def stop(self):
        self.running = False
        
        if self.incident_detection_task:
            self.incident_detection_task.cancel()
            try:
                await self.incident_detection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Agent service stopped")

    async def _incident_detection_loop(self):
        while self.running:
            try:
                if state.system_status.status == StatusEnum.HEALTHY:
                    incident = await datadog_client.detect_incident()
                    
                    if incident and incident["incident_detected"]:
                        logger.info(f"Incident detected: {incident['error_rate']:.2f}% error rate")
                        
                        await state.create_incident(
                            title=f"Checkout Service Failure - {incident['error_rate']:.1f}% error rate",
                            error_rate=incident["error_rate"],
                            p95_latency=incident["p95_latency"]
                        )
                        
                        self.plan_generation_task = asyncio.create_task(self._generate_plan())
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in incident detection loop: {e}")
                await asyncio.sleep(5)

    async def _generate_plan(self):
        try:
            logger.info("Generating recovery validation plan...")
            
            context = {
                "error_rate": state.system_status.error_rate_5m,
                "p95_latency": state.system_status.p95_latency_ms_5m,
                "service": "demo-checkout",
                "top_error": "Checkout endpoint returning 500"
            }
            
            plan_items = await minimax_client.generate_plan(context)
            
            if state.current_incident:
                await state.update_plan(plan_items)
                logger.info(f"Plan generated with {len(plan_items)} test items")
            else:
                logger.warning("No incident found to attach plan to")
                
        except Exception as e:
            logger.error(f"Error generating plan: {e}")

    async def run_validation_tests(self, incident_id: str) -> Optional[str]:
        try:
            if not state.current_incident or state.current_incident.incident_id != incident_id:
                logger.error("Incident not found")
                return None
            
            if not state.current_incident.plan.items:
                logger.error("No plan items available for testing")
                return None
            
            logger.info("Starting validation tests...")
            
            plan_items = [item.model_dump() for item in state.current_incident.plan.items]
            test_run = await testsprite_adapter.run_tests(plan_items, incident_id)
            
            return test_run.run_id
            
        except Exception as e:
            logger.error(f"Error running validation tests: {e}")
            return None

    async def simulate_incident(self, mode: str) -> bool:
        try:
            if mode == "INCIDENT_ON":
                logger.info("Simulating incident...")
                
                await state.create_incident(
                    title="Checkout Service Failure - Simulated",
                    error_rate=100.0,
                    p95_latency=5000.0
                )
                
                self.plan_generation_task = asyncio.create_task(self._generate_plan())
                return True
                
            elif mode == "INCIDENT_OFF":
                logger.info("Clearing simulated incident...")
                await state.clear_incident()
                return True
                
            else:
                logger.error(f"Unknown simulation mode: {mode}")
                return False
                
        except Exception as e:
            logger.error(f"Error simulating incident: {e}")
            return False

agent_service = AgentService()
