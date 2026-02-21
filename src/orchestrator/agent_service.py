import asyncio
import uuid
from datetime import datetime
from typing import Optional
import logging

from src.common.models import StatusEnum, TestRunStatusEnum, TestStatusEnum
from src.orchestrator.state import state
from src.orchestrator.integrations.strands_agent import strands_agent_client
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
                    # Check 1: Local state (from demo app bug toggle)
                    local_error_rate = state.system_status.error_rate_5m
                    
                    # Check 2: Datadog metrics (may return empty if no APM data)
                    # We implement a suppression window: if bug was recently fixed, ignore Datadog for 60s
                    # to allow for metric ingestion latency.
                    dd_incident = None
                    time_since_toggle = (datetime.utcnow() - state.last_bug_toggle_time).total_seconds()
                    
                    if state.bug_enabled or time_since_toggle > 60:
                        dd_incident = await datadog_client.detect_incident()
                    else:
                        logger.info(f"Suppressing Datadog detection (toggle was {time_since_toggle:.1f}s ago)")
                    
                    # Trigger incident if either local state or Datadog shows issues
                    if local_error_rate > 0.05 or (dd_incident and dd_incident["incident_detected"]):
                        error_rate = local_error_rate if local_error_rate > 0.05 else dd_incident.get("error_rate", 100.0)
                        p95_latency = state.system_status.p95_latency_ms_5m if local_error_rate > 0.05 else dd_incident.get("p95_latency", 5000.0)
                        
                        logger.info(f"Incident detected: {error_rate:.2f}% error rate (source: {'local' if local_error_rate > 0.05 else 'datadog'})")
                        
                        await state.create_incident(
                            title=f"Checkout Service Failure - {error_rate:.1f}% error rate",
                            error_rate=error_rate,
                            p95_latency=p95_latency
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
            
            plan_items = await strands_agent_client.generate_plan(context)
            
            if state.current_incident:
                await state.update_plan(plan_items)
                logger.info(f"Plan generated with {len(plan_items)} test items")
            else:
                logger.warning("No incident found to attach plan to")
                
        except Exception as e:
            logger.error(f"Error generating plan: {e}")

    async def run_validation_tests(self, incident_id: str) -> Optional[str]:
        try:
            # Use the current active incident (don't require exact ID match)
            if not state.current_incident:
                logger.error("No active incident")
                return None
            
            if not state.current_incident.plan.items:
                logger.error("No plan items available for testing")
                return None
            
            logger.info(f"Starting validation tests for {state.current_incident.incident_id}...")
            
            plan_items = [item.model_dump() if hasattr(item, 'model_dump') else item for item in state.current_incident.plan.items]
            test_run = await testsprite_adapter.run_tests(plan_items, state.current_incident.incident_id)
            
            # Store the test run in state so the route and frontend can access it
            state.current_test_run = test_run
            
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
