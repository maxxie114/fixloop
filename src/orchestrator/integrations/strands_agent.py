import json
import re
import asyncio
import logging
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from strands import Agent, tool
from strands.models.openai import OpenAIModel

from src.common.config import (
    MINIMAX_API_KEY,
    MINIMAX_MODEL,
    MINIMAX_BASE_URL,
    DEMO_APP_URL,
    DD_SITE,
    DD_SERVICE,
    DD_ENV,
)
from src.orchestrator.integrations.datadog_detection import CUSTOM_ERROR_RATE_METRIC

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------------------
# Tools — the Strands agent uses these to probe the live service
# ---------------------------------------------------------------------------

@tool
def check_service_health() -> str:
    """Check if the checkout service is healthy by calling the /health endpoint."""
    try:
        r = httpx.get(f"{DEMO_APP_URL}/health", timeout=5.0)
        return f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"Health check failed: {e}"


@tool
def get_service_catalog() -> str:
    """Retrieve the product catalog from the checkout service."""
    try:
        r = httpx.get(f"{DEMO_APP_URL}/catalog", timeout=5.0)
        return f"HTTP {r.status_code}: {r.text[:500]}"
    except Exception as e:
        return f"Catalog check failed: {e}"


@tool
def test_checkout_endpoint() -> str:
    """Send a sample checkout request and return the response status and body."""
    try:
        r = httpx.post(
            f"{DEMO_APP_URL}/checkout",
            json={"items": [{"id": "1", "price": 19.99}]},
            timeout=5.0,
        )
        return f"HTTP {r.status_code}: {r.text[:500]}"
    except Exception as e:
        return f"Checkout test failed: {e}"


@tool
def get_bug_state() -> str:
    """Check whether the intentional bug is currently enabled on the service."""
    try:
        r = httpx.get(f"{DEMO_APP_URL}/admin/bug", timeout=5.0)
        return f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return f"Bug state check failed: {e}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_model() -> OpenAIModel:
    return OpenAIModel(
        client_args={
            "api_key": MINIMAX_API_KEY,
            "base_url": MINIMAX_BASE_URL,
        },
        model_id=MINIMAX_MODEL,
        params={"temperature": 0.3},
    )


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON array found in agent response: {text[:300]}")


# ---------------------------------------------------------------------------
# Sync functions executed in a thread pool (Strands Agent is synchronous)
# ---------------------------------------------------------------------------

def _run_plan_agent(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    agent = Agent(
        model=_build_model(),
        tools=[check_service_health, get_service_catalog, test_checkout_endpoint, get_bug_state],
        system_prompt=(
            "You are an expert SRE. Use the provided tools to probe the service, "
            "understand its current state, then output a recovery validation plan "
            "as a JSON array only — no markdown, no prose."
        ),
    )

    prompt = f"""The checkout service at {DEMO_APP_URL} is experiencing an incident:
- Error rate: {context.get('error_rate', 100.0):.1f}%
- P95 latency: {context.get('p95_latency', 5000.0):.0f}ms
- Top error: {context.get('top_error', 'Checkout endpoint returning 500')}

Use your tools to inspect the service, then produce a JSON array of exactly 5 test items:
[
  {{
    "test_id": "TEST-001",
    "name": "Health Check",
    "type": "API",
    "priority": 1,
    "what_it_checks": "Service health endpoint returns OK",
    "target": {{"method": "GET", "url": "{DEMO_APP_URL}/health", "headers": {{}}, "body_json": null}},
    "pass_criteria": "Returns 200 OK"
  }},
  ...
]

Output ONLY the JSON array."""

    result = agent(prompt)
    return _extract_json_array(str(result))


def _run_answer_agent(question: str, context: Any, test_run: Any) -> str:
    agent = Agent(
        model=_build_model(),
        tools=[check_service_health, test_checkout_endpoint, get_bug_state],
        system_prompt=(
            "You are an expert SRE assistant. Use tools to check live service state when helpful. "
            "Give concise, technical answers."
        ),
    )

    ctx = ""
    if context:
        try:
            ctx = (
                f"Incident: {context.title} | "
                f"Error rate: {context.datadog_summary.signal.error_rate_5m:.1f}% | "
                f"P95: {context.datadog_summary.signal.p95_latency_ms_5m:.0f}ms"
            )
        except Exception:
            ctx = "Incident context available."

    tr = ""
    if test_run:
        try:
            passed = sum(1 for t in test_run.tests if t.status.value == "PASS")
            tr = f" | Tests: {passed}/{len(test_run.tests)} passed"
        except Exception:
            pass

    result = agent(f"{ctx}{tr}\n\nQuestion: {question}")
    return str(result)


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------

class StrandsAgentClient:
    """Async wrapper around Strands Agent for plan generation and SRE copilot."""

    async def generate_plan(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not MINIMAX_API_KEY:
            logger.warning("No MINIMAX_API_KEY — using fallback plan")
            return self._fallback_plan()
        try:
            loop = asyncio.get_event_loop()
            plan = await loop.run_in_executor(_executor, _run_plan_agent, context)
            logger.info(f"Strands agent generated {len(plan)} plan items")
            return plan
        except Exception as e:
            logger.error(f"Strands plan generation failed: {e}")
            return self._fallback_plan()

    async def generate_answer(
        self,
        incident_id: Optional[str],
        question: str,
        context: Any = None,
        test_run: Any = None,
    ) -> Any:
        from src.common.models import CopilotAnswer, Citation

        if not MINIMAX_API_KEY:
            return self._default_answer(question, incident_id)
        try:
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                _executor, lambda: _run_answer_agent(question, context, test_run)
            )
            return CopilotAnswer(
                incident_id=incident_id,
                question=question,
                answer=answer,
                citations=[
                    Citation(
                        label="Datadog Metric Explorer",
                        url=(
                            f"https://app.{DD_SITE}/metric/explorer"
                            f"?query=avg%3A{CUSTOM_ERROR_RATE_METRIC}"
                            f"%7Bservice%3A{DD_SERVICE}%2Cenv%3A{DD_ENV}%7D&live=true"
                        ),
                    )
                ],
                created_at=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            logger.error(f"Strands answer generation failed: {e}")
            return self._default_answer(question, incident_id)

    def _fallback_plan(self) -> List[Dict[str, Any]]:
        return [
            {
                "test_id": "TEST-001",
                "name": "Health Check",
                "type": "API",
                "priority": 1,
                "what_it_checks": "Service health endpoint returns OK",
                "target": {"method": "GET", "url": f"{DEMO_APP_URL}/health", "headers": {}, "body_json": None},
                "pass_criteria": "Returns 200 OK with status: ok",
            },
            {
                "test_id": "TEST-002",
                "name": "Catalog Endpoint",
                "type": "API",
                "priority": 2,
                "what_it_checks": "Product catalog endpoint works",
                "target": {"method": "GET", "url": f"{DEMO_APP_URL}/catalog", "headers": {}, "body_json": None},
                "pass_criteria": "Returns 200 OK with products array",
            },
            {
                "test_id": "TEST-003",
                "name": "Checkout Success",
                "type": "API",
                "priority": 3,
                "what_it_checks": "Checkout endpoint succeeds when bug is disabled",
                "target": {"method": "POST", "url": f"{DEMO_APP_URL}/checkout", "headers": {}, "body_json": {"items": [{"id": "1", "price": 19.99}]}},
                "pass_criteria": "Returns 200 OK with order_id",
            },
            {
                "test_id": "TEST-004",
                "name": "Empty Cart Handling",
                "type": "API",
                "priority": 4,
                "what_it_checks": "Checkout handles empty cart gracefully",
                "target": {"method": "POST", "url": f"{DEMO_APP_URL}/checkout", "headers": {}, "body_json": {"items": []}},
                "pass_criteria": "Returns 200 OK even with empty items",
            },
            {
                "test_id": "TEST-005",
                "name": "Checkout Failure Mode",
                "type": "API",
                "priority": 5,
                "what_it_checks": "Checkout returns 500 when bug is enabled",
                "target": {"method": "POST", "url": f"{DEMO_APP_URL}/checkout", "headers": {}, "body_json": {"items": [{"id": "1", "price": 19.99}]}},
                "pass_criteria": "Returns 500 when bug is enabled, 200 when bug is disabled",
            },
        ]

    def _default_answer(self, question: str, incident_id: Optional[str]) -> Any:
        from src.common.models import CopilotAnswer, Citation

        return CopilotAnswer(
            incident_id=incident_id,
            question=question,
            answer="I recommend checking the service logs and running the validation tests to confirm recovery status.",
            citations=[Citation(label="Service Documentation", url="https://docs.example.com/service")],
            created_at=datetime.utcnow().isoformat() + "Z",
        )


strands_agent_client = StrandsAgentClient()
