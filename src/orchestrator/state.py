import httpx
from datetime import datetime
from typing import Optional
import uuid
import asyncio
import logging

from src.common.models import (
    SystemStatus,
    StatusEnum,
    IncidentCard,
    DatadogSummary,
    Signal,
    EvidenceLink,
    Plan,
    PlanItem,
    TestRun,
    TestRunStatusEnum,
    TestItem,
    TestStatusEnum,
)
from src.common.ws import ws_manager
from src.common.events import Event
from src.common.config import DEMO_APP_URL

logger = logging.getLogger(__name__)


class IncidentState:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.system_status = SystemStatus(
            status=StatusEnum.HEALTHY,
            error_rate_5m=0.0,
            p95_latency_ms_5m=0.0,
            active_incident_id=None,
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        self.current_incident: Optional[IncidentCard] = None
        self.current_test_run: Optional[TestRun] = None
        self.bug_enabled = False
        self.incident_start: Optional[datetime] = None
        self.incident_end: Optional[datetime] = None

    async def set_status(
        self, status: StatusEnum, error_rate: float = None, p95_latency: float = None
    ):
        async with IncidentState._lock:
            self.system_status.status = status
            if error_rate is not None:
                self.system_status.error_rate_5m = error_rate
            if p95_latency is not None:
                self.system_status.p95_latency_ms_5m = p95_latency
            self.system_status.updated_at = datetime.utcnow().isoformat() + "Z"

            await ws_manager.broadcast(Event.system_status(self.system_status))

    async def toggle_bug(self, enabled: bool) -> SystemStatus:
        async with IncidentState._lock:
            self.bug_enabled = enabled

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    current_state = await client.get(f"{DEMO_APP_URL}/admin/bug")
                    demo_bug_enabled = (
                        current_state.json().get("enabled", False)
                        if current_state.status_code == 200
                        else enabled
                    )

                    while demo_bug_enabled != enabled:
                        response = await client.post(f"{DEMO_APP_URL}/admin/bug")
                        if response.status_code == 200:
                            demo_bug_enabled = response.json().get(
                                "enabled", not demo_bug_enabled
                            )
                        else:
                            break

                    error_rate = 100.0 if demo_bug_enabled else 0.0
                    p95_latency = 5000.0 if demo_bug_enabled else 50.0
            except Exception as e:
                logger.warning(f"Could not reach demo app: {e}, using local state")
                error_rate = 100.0 if enabled else 0.0
                p95_latency = 5000.0 if enabled else 50.0

            self.system_status.error_rate_5m = error_rate
            self.system_status.p95_latency_ms_5m = p95_latency
            self.system_status.updated_at = datetime.utcnow().isoformat() + "Z"

            # When disabling the bug, clear any active incident and reset to HEALTHY
            if not enabled and self.current_incident:
                self.current_incident = None
                self.current_test_run = None
                self.system_status.status = StatusEnum.HEALTHY
                self.system_status.active_incident_id = None

            await ws_manager.broadcast(Event.system_status(self.system_status))
            return self.system_status

    async def create_incident(
        self, title: str = None, error_rate: float = 0.0, p95_latency: float = 0.0
    ) -> IncidentCard:
        async with IncidentState._lock:
            incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
            self.incident_start = datetime.utcnow()

            signal = Signal(
                error_rate_5m=error_rate,
                p95_latency_ms_5m=p95_latency,
                top_error="Checkout endpoint returning 500" if error_rate > 0 else None,
            )

            datadog_summary = DatadogSummary(
                monitor_id="MON-12345",
                service="demo-checkout",
                signal=signal,
                evidence_links=[
                    EvidenceLink(
                        label="Datadog Dashboard",
                        url=f"https://app.datadoghq.com/dashboard/demo-checkout",
                    )
                ],
            )

            plan = Plan(
                plan_id=f"PLAN-{uuid.uuid4().hex[:8].upper()}",
                generated_at=datetime.utcnow().isoformat() + "Z",
                items=[],
            )

            self.current_incident = IncidentCard(
                incident_id=incident_id,
                title=title or f"Checkout Service Failure - {incident_id}",
                detected_at=self.incident_start.isoformat() + "Z",
                datadog_summary=datadog_summary,
                plan=plan,
            )

            self.system_status.status = StatusEnum.INCIDENT_ACTIVE
            self.system_status.active_incident_id = incident_id
            self.system_status.error_rate_5m = error_rate
            self.system_status.p95_latency_ms_5m = p95_latency
            self.system_status.updated_at = datetime.utcnow().isoformat() + "Z"

            await ws_manager.broadcast(Event.system_status(self.system_status))
            await ws_manager.broadcast(Event.incident_created(self.current_incident))

            return self.current_incident

    async def update_plan(self, plan_items: list) -> IncidentCard:
        async with IncidentState._lock:
            if self.current_incident:
                self.current_incident.plan.items = plan_items
                self.current_incident.plan.generated_at = (
                    datetime.utcnow().isoformat() + "Z"
                )

                await ws_manager.broadcast(
                    Event.plan_generated(
                        self.current_incident.incident_id, self.current_incident.plan
                    )
                )
            return self.current_incident

    async def start_tests(self, tests: list) -> TestRun:
        async with IncidentState._lock:
            run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
            self.incident_start = datetime.utcnow()

            test_items = [
                TestItem(
                    test_id=t.get("test_id", f"TEST-{i}"),
                    name=t.get("name", f"Test {i}"),
                    status=TestStatusEnum.PENDING,
                    last_update_at=datetime.utcnow().isoformat() + "Z",
                    details=None,
                )
                for i, t in enumerate(tests)
            ]

            self.current_test_run = TestRun(
                run_id=run_id,
                incident_id=self.current_incident.incident_id
                if self.current_incident
                else "",
                started_at=datetime.utcnow().isoformat() + "Z",
                status=TestRunStatusEnum.QUEUED,
                tests=test_items,
            )

            self.system_status.status = StatusEnum.VALIDATING
            self.system_status.updated_at = datetime.utcnow().isoformat() + "Z"

            await ws_manager.broadcast(Event.system_status(self.system_status))
            await ws_manager.broadcast(Event.tests_updated(self.current_test_run))

            return self.current_test_run

    async def update_test_run(self, test_run: TestRun):
        async with IncidentState._lock:
            self.current_test_run = test_run

            all_passed = all(t.status == TestStatusEnum.PASS for t in test_run.tests)
            all_completed = all(
                t.status in [TestStatusEnum.PASS, TestStatusEnum.FAIL]
                for t in test_run.tests
            )

            if all_completed:
                if all_passed:
                    self.system_status.status = StatusEnum.RECOVERED
                    self.incident_end = datetime.utcnow()
                else:
                    self.system_status.status = StatusEnum.INCIDENT_ACTIVE

            self.system_status.updated_at = datetime.utcnow().isoformat() + "Z"

            await ws_manager.broadcast(Event.system_status(self.system_status))
            await ws_manager.broadcast(Event.tests_updated(test_run))

    async def clear_incident(self):
        async with IncidentState._lock:
            self.current_incident = None
            self.current_test_run = None
            self.system_status.status = StatusEnum.HEALTHY
            self.system_status.active_incident_id = None
            self.system_status.error_rate_5m = 0.0
            self.system_status.p95_latency_ms_5m = 0.0
            self.system_status.updated_at = datetime.utcnow().isoformat() + "Z"

            await ws_manager.broadcast(Event.system_status(self.system_status))

    def get_status(self) -> SystemStatus:
        return self.system_status

    def get_current_incident(self) -> Optional[IncidentCard]:
        return self.current_incident

    def get_test_run(self, run_id: str = None) -> Optional[TestRun]:
        if run_id is None or (
            self.current_test_run and self.current_test_run.run_id == run_id
        ):
            return self.current_test_run
        return None


state = IncidentState()
