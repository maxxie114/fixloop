from datetime import datetime
from typing import Dict, List, Any
import json

class Event:
    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def system_status(status: "SystemStatus") -> Dict[str, Any]:
        return {
            "type": "system.status",
            "payload": status.model_dump(),
            "ts": Event.now_iso()
        }

    @staticmethod
    def incident_created(incident: "IncidentCard") -> Dict[str, Any]:
        return {
            "type": "incident.created",
            "payload": incident.model_dump(),
            "ts": Event.now_iso()
        }

    @staticmethod
    def plan_generated(incident_id: str, plan: "Plan") -> Dict[str, Any]:
        return {
            "type": "plan.generated",
            "payload": {
                "incident_id": incident_id,
                "plan": plan.model_dump()
            },
            "ts": Event.now_iso()
        }

    @staticmethod
    def tests_updated(test_run: "TestRun") -> Dict[str, Any]:
        return {
            "type": "tests.updated",
            "payload": test_run.model_dump(),
            "ts": Event.now_iso()
        }

    @staticmethod
    def copilot_answer(answer: "CopilotAnswer") -> Dict[str, Any]:
        return {
            "type": "copilot.answer",
            "payload": answer.model_dump(),
            "ts": Event.now_iso()
        }

from src.common.models import SystemStatus, IncidentCard, Plan, TestRun, CopilotAnswer
