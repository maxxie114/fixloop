import os
from dotenv import load_dotenv

load_dotenv()

ORCH_PORT = int(os.getenv("ORCH_PORT", "8000"))
DEMO_PORT = int(os.getenv("DEMO_PORT", "8001"))
DEMO_APP_URL = os.getenv("DEMO_APP_URL", "http://localhost:8001")
ORCH_BASE_URL = os.getenv("ORCH_BASE_URL", "http://localhost:8000")

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")

DD_API_KEY = os.getenv("DD_API_KEY", "")
DD_APP_KEY = os.getenv("DD_APP_KEY", "")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_SERVICE = os.getenv("DD_SERVICE", "demo-checkout")
DD_ENV = os.getenv("DD_ENV", "hackathon")
DATADOG_MCP_URL = os.getenv("DATADOG_MCP_URL", "")
DATADOG_MCP_AUTH = os.getenv("DATADOG_MCP_AUTH", "")

TESTSPRITE_MCP_URL = os.getenv("TESTSPRITE_MCP_URL", "")
TESTSPRITE_MCP_AUTH = os.getenv("TESTSPRITE_MCP_AUTH", "")
TESTSPRITE_API_KEY = os.getenv("TESTSPRITE_API_KEY", "")
TESTSPRITE_BASE_URL = os.getenv("TESTSPRITE_BASE_URL", "")
