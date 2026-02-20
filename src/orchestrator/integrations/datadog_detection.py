import httpx
import asyncio
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
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    headers={
                        "DD-API-KEY": self.api_key,
                        "DD-APPLICATION-KEY": self.app_key
                    },
                    params={
                        "query": f"avg:trace.http.request.errors{{service:{service},env:{self.env}}}.as_rate()",
                        "from": "now-5m"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Datadog API error: {response.status_code}")
                    return self._mock_metrics(service)
                
                return response.json()
                
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
