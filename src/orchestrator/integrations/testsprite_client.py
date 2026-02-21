import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import httpx
import logging

from src.common.models import TestRun, TestRunStatusEnum, TestItem, TestStatusEnum
from src.orchestrator.state import state
from src.common.config import DEMO_APP_URL

logger = logging.getLogger(__name__)


class TestSpriteAdapter:
    def __init__(self):
        self.active_runs = {}

    async def run_tests(
        self, plan_items: List[Dict[str, Any]], incident_id: str
    ) -> TestRun:
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"

        test_items = []
        for i, item in enumerate(plan_items):
            test_item = TestItem(
                test_id=item.get("test_id", f"TEST-{i + 1:03d}"),
                name=item.get("name", f"Test {i + 1}"),
                status=TestStatusEnum.PENDING,
                last_update_at=datetime.utcnow().isoformat() + "Z",
                details=None,
            )
            test_items.append(test_item)

        test_run = TestRun(
            run_id=run_id,
            incident_id=incident_id,
            started_at=datetime.utcnow().isoformat() + "Z",
            status=TestRunStatusEnum.QUEUED,
            tests=test_items,
        )

        self.active_runs[run_id] = test_run

        asyncio.create_task(self._execute_tests(run_id, plan_items))

        return test_run

    async def _execute_tests(self, run_id: str, plan_items: List[Dict[str, Any]]):
        await asyncio.sleep(0.5)

        if run_id not in self.active_runs:
            return

        test_run = self.active_runs[run_id]
        test_run.status = TestRunStatusEnum.RUNNING

        await state.update_test_run(test_run)

        bug_enabled = state.bug_enabled

        for test_item in test_run.tests:
            test_item.status = TestStatusEnum.RUNNING
            test_item.last_update_at = datetime.utcnow().isoformat() + "Z"
            await state.update_test_run(test_run)

            await asyncio.sleep(0.3)

            plan_item = None
            for item in plan_items:
                if item.get("test_id") == test_item.test_id:
                    plan_item = item
                    break

            if not plan_item:
                test_item.status = TestStatusEnum.FAIL
                test_item.details = "Test item not found in plan"
                test_item.last_update_at = datetime.utcnow().isoformat() + "Z"
                await state.update_test_run(test_run)
                continue

            result = await self._run_single_test(plan_item, bug_enabled)

            test_item.status = result["status"]
            test_item.details = result["details"]
            test_item.last_update_at = datetime.utcnow().isoformat() + "Z"
            await state.update_test_run(test_run)

        all_passed = all(t.status == TestStatusEnum.PASS for t in test_run.tests)
        test_run.status = (
            TestRunStatusEnum.COMPLETED if all_passed else TestRunStatusEnum.FAILED
        )
        await state.update_test_run(test_run)

        del self.active_runs[run_id]

    async def _run_single_test(
        self, item: Dict[str, Any], bug_enabled: bool
    ) -> Dict[str, Any]:
        target = item.get("target", {})
        method = target.get("method", "GET")
        url = target.get("url", f"{DEMO_APP_URL}{target.get('url', '/health')}")
        headers = target.get("headers", {})
        body_json = target.get("body_json")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body_json)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body_json)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    response = await client.get(url, headers=headers)

                status_code = response.status_code

                if "checkout" in url.lower():
                    if bug_enabled and method == "POST":
                        if status_code == 500:
                            return {
                                "status": TestStatusEnum.PASS,
                                "details": f"Bug is enabled, checkout returns 500 as expected (HTTP {status_code})",
                            }
                        else:
                            return {
                                "status": TestStatusEnum.FAIL,
                                "details": f"Expected 500 when bug is enabled, got {status_code}",
                            }
                    elif not bug_enabled:
                        if status_code == 200:
                            return {
                                "status": TestStatusEnum.PASS,
                                "details": f"Checkout successful (HTTP {status_code})",
                            }
                        else:
                            return {
                                "status": TestStatusEnum.FAIL,
                                "details": f"Expected 200 when bug is disabled, got {status_code}",
                            }

                if status_code < 400:
                    return {
                        "status": TestStatusEnum.PASS,
                        "details": f"HTTP {status_code} - {response.text[:100] if response.text else 'OK'}",
                    }

                pass_criteria = item.get("pass_criteria", "").lower()
                if "404" in pass_criteria and status_code == 404:
                    return {
                        "status": TestStatusEnum.PASS,
                        "details": f"HTTP {status_code} - {response.text[:100] if response.text else 'Not Found'}",
                    }
                if "400" in pass_criteria and status_code == 400:
                    return {
                        "status": TestStatusEnum.PASS,
                        "details": f"HTTP {status_code} - {response.text[:100] if response.text else 'Bad Request'}",
                    }

                return {
                    "status": TestStatusEnum.FAIL,
                    "details": f"HTTP {status_code} - {response.text[:100] if response.text else 'Error'}",
                }

        except httpx.TimeoutException:
            return {"status": TestStatusEnum.FAIL, "details": "Request timed out"}
        except Exception as e:
            return {"status": TestStatusEnum.FAIL, "details": f"Error: {str(e)[:100]}"}

    async def poll_status(self, run_id: str) -> TestRun:
        return self.active_runs.get(run_id) or state.get_test_run(run_id)


testsprite_adapter = TestSpriteAdapter()
