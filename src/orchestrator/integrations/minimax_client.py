import httpx
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.common.config import MINIMAX_API_KEY, MINIMAX_MODEL, DEMO_APP_URL

logger = logging.getLogger(__name__)


class MiniMaxClient:
    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.model = MINIMAX_MODEL
        self.base_url = "https://api.minimax.chat/v1"

    async def generate_plan(self, context: Dict[str, Any]) -> List[Any]:
        from src.common.models import PlanItem

        try:
            if not self.api_key or self.api_key == "your_minimax_api_key_here":
                logger.warning("No MiniMax API key, using default plan")
                return self._fallback_plan()

            prompt = f"""Generate a Recovery Validation Plan as a JSON array with exactly 5 test items.
            
The demo checkout service is at {DEMO_APP_URL} with these endpoints:
- GET /health - health check
- GET /catalog - product catalog
- POST /checkout - checkout endpoint (currently failing with 500 when bug is enabled)

Output ONLY valid JSON. No markdown, no prose. The JSON must be an array of objects with this exact structure:
[
  {{
    "test_id": "TEST-001",
    "name": "Health Check",
    "type": "API",
    "priority": 1,
    "what_it_checks": "Service is healthy",
    "target": {{"method": "GET", "url": "{DEMO_APP_URL}/health", "headers": {{}}, "body_json": null}},
    "pass_criteria": "Returns 200 OK"
  }},
  ...
]

Include tests for:
1. Health endpoint
2. Catalog endpoint  
3. Checkout endpoint (should fail when bug is on)
4. Error handling test
5. Negative test case

Return ONLY the JSON array. No explanation."""

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/text/chatcompletion_v2",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert SRE assistant that generates valid JSON only.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"MiniMax API error: {response.status_code}")
                    return self._fallback_plan()

                data = response.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                import json
                import re
                from src.common.models import PlanItem

                json_match = re.search(r"\[[\s\S]*\]", content)
                if json_match:
                    plan_items_data = json.loads(json_match.group())
                    plan_items = [PlanItem(**item) for item in plan_items_data]
                    return plan_items
                else:
                    logger.warning("Failed to parse JSON from MiniMax response")
                    return self._fallback_plan()

        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            return self._fallback_plan()

    def _fallback_plan(self) -> List[Any]:
        from src.common.models import PlanItem, PlanItemType, Target

        return [
            PlanItem(
                test_id="TEST-001",
                name="Health Check",
                type=PlanItemType.API,
                priority=1,
                what_it_checks="Service health endpoint returns OK",
                target=Target(
                    method="GET",
                    url=f"{DEMO_APP_URL}/health",
                    headers={},
                    body_json=None,
                ),
                pass_criteria="Returns 200 OK with status: ok",
            ),
            PlanItem(
                test_id="TEST-002",
                name="Catalog Endpoint",
                type=PlanItemType.API,
                priority=2,
                what_it_checks="Product catalog endpoint works",
                target=Target(
                    method="GET",
                    url=f"{DEMO_APP_URL}/catalog",
                    headers={},
                    body_json=None,
                ),
                pass_criteria="Returns 200 OK with products array",
            ),
            PlanItem(
                test_id="TEST-003",
                name="Checkout Success",
                type=PlanItemType.API,
                priority=3,
                what_it_checks="Checkout endpoint succeeds when bug is disabled",
                target=Target(
                    method="POST",
                    url=f"{DEMO_APP_URL}/checkout",
                    headers={},
                    body_json={"items": [{"id": "1", "price": 19.99}]},
                ),
                pass_criteria="Returns 200 OK with order_id",
            ),
            PlanItem(
                test_id="TEST-004",
                name="Error Handling",
                type=PlanItemType.API,
                priority=4,
                what_it_checks="Checkout properly handles error scenarios",
                target=Target(
                    method="POST",
                    url=f"{DEMO_APP_URL}/checkout",
                    headers={},
                    body_json={"items": []},
                ),
                pass_criteria="Returns 200 OK even with empty items",
            ),
            PlanItem(
                test_id="TEST-005",
                name="Checkout With Bug",
                type=PlanItemType.API,
                priority=5,
                what_it_checks="Checkout fails gracefully when bug is enabled",
                target=Target(
                    method="POST",
                    url=f"{DEMO_APP_URL}/checkout",
                    headers={},
                    body_json={"items": [{"id": "1", "price": 19.99}]},
                ),
                pass_criteria="Returns 500 when bug is enabled, 200 when bug is disabled",
            ),
        ]

    async def generate_answer(
        self,
        incident_id: Optional[str],
        question: str,
        context: Any = None,
        test_run: Any = None,
    ) -> Any:
        from src.common.models import CopilotAnswer, Citation

        try:
            if not self.api_key or self.api_key == "your_minimax_api_key_here":
                logger.warning("No MiniMax API key, using default answer")
                return self._default_answer(question, incident_id)

            context_info = ""
            if context:
                try:
                    context_info = f"""
Current Incident:
- Incident ID: {context.incident_id}
- Title: {context.title}
- Detected: {context.detected_at}
- Error Rate: {context.datadog_summary.signal.error_rate_5m:.2f}%
- P95 Latency: {context.datadog_summary.signal.p95_latency_ms_5m:.0f}ms
- Top Error: {context.datadog_summary.signal.top_error or "None"}

Recovery Plan:
- Plan ID: {context.plan.plan_id}
- Generated: {context.plan.generated_at}
- Tests: {len(context.plan.items)}
"""
                except:
                    context_info = "Incident context available but details are missing."

            test_info = ""
            if test_run:
                try:
                    passed = sum(1 for t in test_run.tests if t.status.value == "PASS")
                    total = len(test_run.tests)
                    test_info = f"""
Test Results:
- Run ID: {test_run.run_id}
- Status: {test_run.status.value}
- Tests: {passed}/{total} passed
"""
                except:
                    test_info = "Test results available but details are missing."

            prompt = f"""You are an expert SRE assistant. Answer this question about the current incident:

{context_info}
{test_info}

Question: {question}

Provide a helpful, technical answer based on the incident context and test results. If there are failing tests, explain what they mean and suggest next steps. Keep your answer concise but informative."""

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/text/chatcompletion_v2",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert SRE assistant helping with incident recovery.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"MiniMax API error: {response.status_code}")
                    return self._default_answer(question, incident_id)

                data = response.json()
                logger.info(f"MiniMax response: {data}")
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                if not content:
                    logger.warning("Empty content from MiniMax API")
                    return self._default_answer(question, incident_id)

                return CopilotAnswer(
                    incident_id=incident_id,
                    question=question,
                    answer=content
                    or "I couldn't generate an answer. Please check the incident details.",
                    citations=[
                        Citation(
                            label="Datadog Dashboard",
                            url="https://app.datadoghq.com/dashboard/demo-checkout",
                        )
                    ],
                    created_at=datetime.utcnow().isoformat() + "Z",
                )

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return self._default_answer(question, incident_id)

    def _default_answer(self, question: str, incident_id: Optional[str]) -> Any:
        from src.common.models import CopilotAnswer, Citation

        return CopilotAnswer(
            incident_id=incident_id,
            question=question,
            answer="Based on the current incident context, I recommend checking the service logs and monitoring dashboards for more details. The test results should indicate whether the issue has been resolved.",
            citations=[
                Citation(
                    label="Service Documentation",
                    url="https://docs.example.com/service",
                )
            ],
            created_at=datetime.utcnow().isoformat() + "Z",
        )


minimax_client = MiniMaxClient()
