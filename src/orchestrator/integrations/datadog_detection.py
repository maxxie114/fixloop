import httpx
import asyncio
import time
from typing import Dict, Any, Optional
import logging

from src.common.config import DD_API_KEY, DD_APP_KEY, DD_SITE, DD_SERVICE, DD_ENV

logger = logging.getLogger(__name__)

class DatadogClient:
    def __init__(self):
        self.api_key = DD_API_KEY
        self.app_key = DD_APP_KEY
        self.site = DD_SITE
        self.service = DD_SERVICE
        self.env = DD_ENV
        self.base_url = f"https://api.{self.site}"
        
    async def get_service_metrics(self, service: str = None) -> Dict[str, Any]:
        service = service or self.service
        
        if not self.api_key or self.api_key == "your_datadog_api_key":
            logger.warning("No Datadog API key configured, using mock data")
            return self._mock_metrics(service)
        
        now = int(time.time())
        five_min_ago = now - 300
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query error rate
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    headers={
                        "DD-API-KEY": self.api_key,
                        "DD-APPLICATION-KEY": self.app_key
                    },
                    params={
                        "query": f"avg:trace.http.request.errors{{service:{service},env:{self.env}}}.as_rate()",
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
                
                return {
                    "error_rate_5m": error_rate,
                    "p95_latency_ms_5m": 0.0,  # Would need a separate query
                    "top_error": "HTTP 500 Internal Server Error" if error_rate > 0.05 else None,
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
