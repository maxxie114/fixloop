# AGENT.md (BACKEND) — Recovery Validation Agent
Owner: Backend Coding Agent  
Scope: FastAPI demo app + Orchestrator API + Strands Agent workflow + MiniMax M2.5 + Datadog (MCP) + TestSprite (MCP/API)  
Goal: A working backend that the frontend can call + a shared API/schema contract that matches the frontend exactly.

---

## 0) One-sentence summary
Build a backend that (1) exposes a demo app with a bug toggle, (2) detects an incident using Datadog signals, (3) uses a Strands Agent + MiniMax M2.5 to generate a structured “Recovery Validation Plan”, (4) triggers TestSprite runs, and (5) streams real-time status to the frontend via WebSocket.

---

## 1) Hard constraints
- Must use: Strands Agent Framework, MiniMax M2.5 API, Datadog Observability (and Datadog MCP for agent queries), TestSprite integration (MCP preferred).
- The backend must implement the API + WebSocket contract defined in this file so the frontend can work without changes.
- Everything must be demo-safe: even if Datadog monitor/webhook is slow, a fallback path must exist so the demo always completes.

References:
- Strands Agent API: https://strandsagents.com/latest/documentation/docs/api-reference/python/agent/agent/
- Datadog docs: https://docs.datadoghq.com/
- Datadog MCP Server: https://docs.datadoghq.com/bits_ai/mcp_server/
- MiniMax models intro: https://platform.minimax.io/docs/guides/models-intro
- TestSprite docs: https://docs.testsprite.com/

---

## 2) Architecture overview (3 logical services)
### 2.1 demo_app (FastAPI, port 8001)
Purpose: A tiny production-like service Datadog can monitor.
Endpoints:
- GET /health -> 200 OK always
- GET /catalog -> 200 OK mock payload
- POST /checkout -> 200 OK when healthy, 500 when bug enabled
- POST /admin/bug -> toggles bug state (enabled true/false)

### 2.2 orchestrator_api (FastAPI, port 8000)
Purpose: The backend API that the frontend calls.
Responsibilities:
- Expose REST endpoints required by the frontend (status, bug toggle, incidents, tests, copilot ask)
- Maintain IncidentState (HEALTHY -> INCIDENT_ACTIVE -> VALIDATING -> RECOVERED)
- Host WebSocket /ws to stream real-time events to frontend

### 2.3 agent_worker (in-process background task OR separate process)
Purpose: Strands Agent runner + tool integrations.
Responsibilities:
- Detect incident (webhook, polling, or demo simulate)
- Query Datadog for incident context via MCP
- Call MiniMax M2.5 to generate Recovery Validation Plan (strict JSON schema)
- Trigger TestSprite to run tests and poll results
- Emit WS events as state changes occur

---

## 3) Repo structure (recommended)
backend/
  AGENT.md
  .env.example
  requirements.txt (or pyproject.toml)
  src/
    common/
      config.py
      models.py
      events.py
      ws.py
      util.py
    demo_app/
      main.py
      bug_state.py
    orchestrator/
      main.py
      state.py
      routes.py
      agent_service.py
      integrations/
        minimax_client.py
        datadog_mcp_client.py
        testsprite_client.py
        datadog_detection.py
  scripts/
    run_all.sh

---

## 4) Environment variables (.env.example)
### Backend ports/urls
- ORCH_PORT=8000
- DEMO_PORT=8001
- DEMO_APP_URL=http://localhost:8001
- ORCH_BASE_URL=http://localhost:8000

### MiniMax
- MINIMAX_API_KEY=...
- MINIMAX_MODEL=... (the exact M2.5 model identifier for your account)

### Datadog
- DD_API_KEY=...
- DD_APP_KEY=...
- DD_SITE=datadoghq.com (or your site)
- DD_SERVICE=demo-checkout
- DD_ENV=hackathon
- DATADOG_MCP_URL=... (where Datadog MCP server runs)
- DATADOG_MCP_AUTH=... (if required)

### TestSprite
Preferred (MCP):
- TESTSPRITE_MCP_URL=...
- TESTSPRITE_MCP_AUTH=... (if required)
Optional (direct API if provided):
- TESTSPRITE_API_KEY=...
- TESTSPRITE_BASE_URL=...

---

## 5) Shared API/schema contract (MUST IMPLEMENT EXACTLY)
This contract must match frontend types 1:1. Do not rename keys.

### 5.1 Enums
SystemStatus.status:
- HEALTHY
- INCIDENT_ACTIVE
- VALIDATING
- RECOVERED

TestRun.status:
- QUEUED
- RUNNING
- COMPLETED
- FAILED

TestRun.tests[].status:
- PENDING
- RUNNING
- PASS
- FAIL

PlanItem.type:
- API
- UI
- SYNTHETIC

HTTP method:
- GET
- POST
- PUT
- DELETE

### 5.2 JSON Schemas (field names and nesting must match)

SystemStatus:
- status: string (enum above)
- error_rate_5m: number
- p95_latency_ms_5m: number
- active_incident_id: string or null
- updated_at: ISO-8601 string

IncidentCard:
- incident_id: string
- title: string
- detected_at: ISO-8601 string
- datadog_summary:
  - monitor_id: string or null
  - service: string
  - signal:
    - error_rate_5m: number
    - p95_latency_ms_5m: number
    - top_error: string or null
  - evidence_links: array of
    - label: string
    - url: string
- plan:
  - plan_id: string
  - generated_at: ISO-8601 string
  - items: array of PlanItem
    - test_id: string
    - name: string
    - type: string (enum API/UI/SYNTHETIC)
    - priority: number (1 = highest)
    - what_it_checks: string
    - target:
      - method: string (GET/POST/PUT/DELETE)
      - url: string
      - headers: object string->string
      - body_json: object (any)
    - pass_criteria: string

TestRun:
- run_id: string
- incident_id: string
- started_at: ISO-8601 string
- status: string (enum)
- tests: array of
  - test_id: string
  - name: string
  - status: string (enum)
  - last_update_at: ISO-8601 string
  - details: string or null

CopilotAnswer:
- incident_id: string or null
- question: string
- answer: string
- citations: array of
  - label: string
  - url: string
- created_at: ISO-8601 string

### 5.3 REST endpoints (orchestrator_api on port 8000)
1) GET /api/status
Response: SystemStatus

2) POST /api/demo/bug
Request body:
- enabled: boolean
Response: SystemStatus
Behavior:
- calls demo_app POST /admin/bug
- emits WS event type "system.status"

3) GET /api/incidents/current
Response: IncidentCard or null

4) POST /api/incidents/simulate
Request body:
- mode: "INCIDENT_ON" or "INCIDENT_OFF"
Response: IncidentCard or null
Purpose:
- Demo fallback if Datadog detection is delayed

5) POST /api/tests/run
Request body:
- incident_id: string
Response: TestRun
Behavior:
- triggers TestSprite run using current plan for the incident
- emits WS "tests.updated" as statuses change

6) GET /api/tests/runs/{run_id}
Response: TestRun

7) POST /api/copilot/ask
Request body:
- incident_id: string or null
- question: string
Response: CopilotAnswer
Behavior:
- answer using MiniMax M2.5 + current incident context + test results

### 5.4 WebSocket endpoint
GET /ws

Message envelope:
- type: string (one of: system.status, incident.created, plan.generated, tests.updated, copilot.answer)
- payload: object (see below)
- ts: ISO-8601 string

Payload mapping:
- system.status -> SystemStatus
- incident.created -> IncidentCard (plan.items may initially be empty if plan not generated yet)
- plan.generated -> object:
  - incident_id: string
  - plan: IncidentCard.plan
- tests.updated -> TestRun
- copilot.answer -> CopilotAnswer

---

## 6) IncidentState machine (implement in orchestrator/state.py)
States:
- HEALTHY: no incident active
- INCIDENT_ACTIVE: incident detected, plan generation pending or in progress
- VALIDATING: tests are running / rerunning
- RECOVERED: all tests pass AND signals return to normal (or demo acceptance rule met)

Store the following in memory (in a singleton state object):
- system_status: SystemStatus
- current_incident: IncidentCard or null
- current_test_run: TestRun or null
- bug_enabled: boolean
- timestamps: incident_start, incident_end

Rules:
- When incident starts: set active_incident_id, emit incident.created
- When plan generated: update incident.plan, emit plan.generated
- When tests start: set status VALIDATING, emit system.status + tests.updated
- When all tests pass after a fix: set status RECOVERED, incident_end, emit system.status + tests.updated

---

## 7) Datadog detection (must exist + a reliable fallback)
### 7.1 Preferred: monitor + webhook
- Create a Datadog monitor on 5xx error rate for service demo-checkout.
- Configure webhook to orchestrator endpoint:
  - POST /internal/datadog/webhook  (this can be internal; frontend does not call it)
- On webhook:
  - parse incident details (monitor_id, alert title, triggered time)
  - mark INCIDENT_ACTIVE if not already

### 7.2 Fallback: polling
- Every 3–5 seconds:
  - query Datadog (MCP preferred) for:
    - error_rate_5m
    - p95_latency_ms_5m
    - top error signature
- If error rate above threshold (e.g., > 5% in last 1m/5m): trigger incident.

### 7.3 Absolute fallback: /api/incidents/simulate
- If mode=INCIDENT_ON: create an incident immediately and run the same agent pipeline.
- Still query Datadog for numbers if possible; but do not block the demo.

---

## 8) Strands Agent workflow (agent_worker)
### 8.1 Tools to implement (as Python callables)
- tool_datadog_context(service, window_minutes) -> object:
  - returns error_rate_5m, p95_latency_ms_5m, top_error, evidence_links
  - uses Datadog MCP where possible
- tool_generate_plan(context, demo_base_url) -> plan JSON:
  - calls MiniMax M2.5 with strict JSON schema requirement
- tool_testsprite_run(plan_items) -> run_id and initial test statuses
- tool_testsprite_poll(run_id) -> updated statuses
- tool_emit_event(type, payload) -> sends to WS broadcast queue

### 8.2 MiniMax prompting (strict JSON)
Objective: Generate exactly 5 tests in the schema.
Prompt strategy:
- Provide a “JSON schema contract” in the prompt text (copy the PlanItem structure)
- Require:
  - Exactly 5 items
  - priority 1..5
  - include at least:
    - /health
    - /checkout
    - /catalog
    - a negative test on checkout error handling
    - a basic “auth/mock” or similar
- Output must be valid JSON only. No prose.

Retry strategy:
- If JSON parse fails:
  - re-prompt with “Output JSON only. No markdown.”
  - apply 1–2 retries max

### 8.3 Pipeline logic (pseudo flow)
On incident detected:
1) Emit system.status (INCIDENT_ACTIVE)
2) Fetch Datadog context -> build IncidentCard with empty plan initially
3) Emit incident.created
4) Generate plan via MiniMax -> attach to incident
5) Emit plan.generated
6) Start TestSprite run -> create TestRun
7) Emit tests.updated
8) Poll TestSprite until completed (or for a fixed demo duration)
9) If bug fixed and tests pass -> mark RECOVERED, emit system.status + tests.updated

On Fix Bug action:
- Orchestrator should:
  - toggle demo bug off
  - rerun tests automatically if incident active (or provide UI button later)
  - update status based on passing tests

---

## 9) TestSprite integration requirements
Preferred: TestSprite MCP
- Implement a client that can:
  - submit test plan items
  - obtain per-test running/pass/fail statuses
- If MCP client is too slow to implement, provide a fallback “mock adapter” that simulates:
  - on bug enabled -> checkout test fails
  - on bug disabled -> all pass
But keep interfaces identical so real TestSprite can be swapped in.

---

## 10) Implementation steps (in order, minimal demo first)
1) Build demo_app with bug toggle and endpoints
2) Add basic logging + timing middleware (so Datadog can capture errors)
3) Build orchestrator_api REST endpoints (status/bug/incidents/tests/copilot)
4) Build WebSocket manager + event broadcasting
5) Implement in-memory IncidentState
6) Stub agent_worker with simulate incident path working end-to-end
7) Add MiniMax client and plan generation (strict JSON)
8) Add TestSprite adapter (MCP or mock) and stream results
9) Add Datadog MCP querying for real incident context (best-effort)
10) Add webhook receiver and/or polling
11) Add /api/copilot/ask using MiniMax: answer based on incident + plan + tests

---

## 11) Acceptance criteria (demo success checklist)
- Backend runs two FastAPI servers (demo_app:8001, orchestrator:8000)
- POST /api/demo/bug enabled=true makes POST /checkout return 500
- Incident triggers (monitor/webhook OR polling OR simulate)
- IncidentCard appears with plan of exactly 5 tests
- TestRun shows tests failing when bug is on, passing when bug is off
- WS events update frontend in real-time
- /api/copilot/ask answers questions using current state

---

## 12) Notes for speed
- Keep state in memory; no database.
- Prefer simple polling loops + timeouts to avoid complex async edges.
- If Datadog monitor takes too long, rely on simulate endpoint for the demo, but still emit Datadog telemetry from demo_app so observability is real.

End of BACKEND AGENT.md
