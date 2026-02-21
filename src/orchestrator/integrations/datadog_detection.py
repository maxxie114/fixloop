import httpx
import asyncio
import time
from typing import Dict, Any, Optional, List
import logging

from src.common.config import DD_API_KEY, DD_APP_KEY, DD_SITE, DD_SERVICE, DD_ENV

logger = logging.getLogger(__name__)

# Custom metric name for the demo checkout service
CUSTOM_ERROR_RATE_METRIC = "custom.demo_checkout.error_rate"
CUSTOM_LATENCY_METRIC = "custom.demo_checkout.p95_latency"

class DatadogClient:
    def __init__(self):
        self.api_key = DD_API_KEY
        self.app_key = DD_APP_KEY
        self.site = DD_SITE
        self.service = DD_SERVICE
        self.env = DD_ENV
        self.base_url = f"https://api.{self.site}"

    async def submit_metric(self, metric_name: str, value: float, tags: List[str] = None) -> bool:
        """Submit a custom metric to Datadog via the v2 Series API."""
        if not self.api_key or self.api_key == "your_datadog_api_key":
            logger.warning("No Datadog API key configured, cannot submit metric")
            return False

        tags = tags or [f"service:{self.service}", f"env:{self.env}"]
        now = int(time.time())

        payload = {
            "series": [
                {
                    "metric": metric_name,
                    "type": 0,  # gauge
                    "points": [
                        {"timestamp": now, "value": value}
                    ],
                    "tags": tags,
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v2/series",
                    headers={
                        "DD-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code in (200, 202):
                    logger.info(f"Submitted metric {metric_name}={value} to Datadog")
                    return True
                else:
                    logger.error(f"Failed to submit metric: {response.status_code} - {response.text[:200]}")
                    return False

        except Exception as e:
            logger.error(f"Error submitting metric to Datadog: {e}")
            return False

    async def submit_demo_metrics(self, error_rate: float, p95_latency: float):
        """Submit both error rate and latency metrics for the demo checkout service."""
        tags = [f"service:{self.service}", f"env:{self.env}"]
        await asyncio.gather(
            self.submit_metric(CUSTOM_ERROR_RATE_METRIC, error_rate, tags),
            self.submit_metric(CUSTOM_LATENCY_METRIC, p95_latency, tags),
        )

    async def get_service_metrics(self, service: str = None) -> Dict[str, Any]:
        service = service or self.service
        
        if not self.api_key or self.api_key == "your_datadog_api_key":
            logger.warning("No Datadog API key configured, using mock data")
            return self._mock_metrics(service)
        
        now = int(time.time())
        five_min_ago = now - 300
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query our custom error rate metric from Datadog
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    headers={
                        "DD-API-KEY": self.api_key,
                        "DD-APPLICATION-KEY": self.app_key
                    },
                    params={
                        "query": f"avg:{CUSTOM_ERROR_RATE_METRIC}{{service:{service},env:{self.env}}}",
                        "from": str(five_min_ago),
                        "to": str(now)
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Datadog API error: {response.status_code} - {response.text[:200]}")
                    return self._mock_metrics(service)
                
                data = response.json()
                
                # Parse Datadog timeseries response
                error_rate = 0.0
                series = data.get("series", [])
                if series and series[0].get("pointlist"):
                    points = series[0]["pointlist"]
                    # Get the most recent non-null value
                    for point in reversed(points):
                        if len(point) >= 2 and point[1] is not None:
                            error_rate = point[1]
                            break
                
                logger.info(f"Datadog returned error_rate={error_rate} for {service} (series count: {len(series)})")
                
                return {
                    "error_rate_5m": error_rate,
                    "p95_latency_ms_5m": 0.0,
                    "top_error": "Checkout endpoint returning 500" if error_rate > 0.05 else None,
                    "service": service,
                    "env": self.env
                }
                
        except Exception as e:
            logger.error(f"Error calling Datadog API: {e}")
            return self._mock_metrics(service)
    
    def _mock_metrics(self, service: str) -> Dict[str, Any]:
        return {
            "error_rate_5m": 0.0,
            "p95_latency_ms_5m": 45.0,
            "top_error": None,
            "service": service,
            "env": self.env
        }

    async def detect_incident(self, service: str = None) -> Optional[Dict[str, Any]]:
        metrics = await self.get_service_metrics(service)
        
        error_rate = metrics.get("error_rate_5m", 0.0)
        
        if error_rate > 0.05:
            return {
                "incident_detected": True,
                "error_rate": error_rate,
                "p95_latency": metrics.get("p95_latency_ms_5m", 0),
                "top_error": metrics.get("top_error", "Unknown error"),
                "monitor_id": "MON-12345"
            }
        
        return None

datadog_client = DatadogClient()
