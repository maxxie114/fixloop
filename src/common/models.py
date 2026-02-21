from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

class StatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    INCIDENT_ACTIVE = "INCIDENT_ACTIVE"
    VALIDATING = "VALIDATING"
    RECOVERED = "RECOVERED"

class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"

class PlanItemType(str, Enum):
    API = "API"
    UI = "UI"
    SYNTHETIC = "SYNTHETIC"

class TestRunStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TestStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"

class SystemStatus(BaseModel):
    status: StatusEnum
    error_rate_5m: float
    p95_latency_ms_5m: float
    active_incident_id: Optional[str] = None
    updated_at: str

class Target(BaseModel):
    method: HTTPMethod
    url: str
    headers: Dict[str, str] = {}
    body_json: Optional[Dict[str, Any]] = None

class PlanItem(BaseModel):
    test_id: str
    name: str
    type: PlanItemType
    priority: int
    what_it_checks: str
    target: Target
    pass_criteria: str

class Plan(BaseModel):
    plan_id: str
    generated_at: str
    items: List[PlanItem] = []

class Signal(BaseModel):
    error_rate_5m: float
    p95_latency_ms_5m: float
    top_error: Optional[str] = None

class EvidenceLink(BaseModel):
    label: str
    url: str

class DatadogSummary(BaseModel):
    monitor_id: Optional[str] = None
    service: str
    signal: Signal
    evidence_links: List[EvidenceLink] = []

class IncidentCard(BaseModel):
    incident_id: str
    title: str
    detected_at: str
    datadog_summary: DatadogSummary
    plan: Plan

class TestItem(BaseModel):
    test_id: str
    name: str
    status: TestStatusEnum
    last_update_at: str
    details: Optional[str] = None

class TestRun(BaseModel):
    run_id: str
    incident_id: str
    started_at: str
    status: TestRunStatusEnum
    tests: List[TestItem] = []

class Citation(BaseModel):
    label: str
    url: str

class CopilotAnswer(BaseModel):
    incident_id: Optional[str]
    question: str
    answer: str
    citations: List[Citation] = []
    created_at: str

class WsMessageType(str, Enum):
    SYSTEM_STATUS = "system.status"
    INCIDENT_CREATED = "incident.created"
    PLAN_GENERATED = "plan.generated"
    TESTS_UPDATED = "tests.updated"
    COPILOT_ANSWER = "copilot.answer"

class WsMessage(BaseModel):
    type: WsMessageType
    payload: Any
    ts: str

class BugToggleRequest(BaseModel):
    enabled: bool

class SimulateRequest(BaseModel):
    mode: str

class RunTestsRequest(BaseModel):
    incident_id: str

class CopilotAskRequest(BaseModel):
    incident_id: Optional[str]
    question: str
