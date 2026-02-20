# AGENT.md (FRONTEND) — Recovery Validation Dashboard
Owner: Frontend Coding Agent  
Scope: Next.js app with a single ops-style page: Status Bar + Incident Feed + Test Results + Copilot Chat sidebar  
Goal: A live dashboard that talks to the backend via REST + WebSocket using the shared contract.

---

## 0) One-sentence summary
Build a dark-themed ops dashboard that shows system status, incident details, a MiniMax-generated Recovery Validation Plan, live TestSprite results, and an interactive Copilot chat that asks the backend questions.

---

## 1) Hard constraints
- Must work with backend contract exactly (fields, endpoints, WS message types).
- Must be demo-friendly: obvious status changes, smooth live updates, no refresh required.
- Tech: Next.js + Tailwind + CopilotKit for the chat UI (backend provides the actual answers).

References:
- CopilotKit: https://docs.copilotkit.ai/
- Tailwind: https://tailwindcss.com/docs
- Next.js: https://nextjs.org/docs

---

## 2) Project structure (recommended)
frontend/
  AGENT.md
  .env.local.example
  package.json
  next.config.js
  tailwind.config.ts
  src/
    app/
      layout.tsx
      page.tsx
    components/
      StatusBar.tsx
      IncidentFeed.tsx
      TestResultsPanel.tsx
      CopilotSidebar.tsx
      MetricPill.tsx
      SectionCard.tsx
    lib/
      types.ts
      api.ts
      ws.ts
      store.ts

---

## 3) Environment variables (.env.local.example)
- NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

Derive WebSocket URL from backend URL:
- if backend is http://localhost:8000 -> ws://localhost:8000/ws
- if https -> wss

---

## 4) Shared contract (MUST MATCH BACKEND EXACTLY)
Do not invent or rename fields. Use the same enums.

### 4.1 Types (implement in src/lib/types.ts)
SystemStatus:
- status: "HEALTHY" | "INCIDENT_ACTIVE" | "VALIDATING" | "RECOVERED"
- error_rate_5m: number
- p95_latency_ms_5m: number
- active_incident_id: string | null
- updated_at: string

IncidentCard:
- incident_id: string
- title: string
- detected_at: string
- datadog_summary:
  - monitor_id: string | null
  - service: string
  - signal:
    - error_rate_5m: number
    - p95_latency_ms_5m: number
    - top_error: string | null
  - evidence_links: Array<{ label: string; url: string }>
- plan:
  - plan_id: string
  - generated_at: string
  - items: Array<PlanItem>

PlanItem:
- test_id: string
- name: string
- type: "API" | "UI" | "SYNTHETIC"
- priority: number
- what_it_checks: string
- target:
  - method: "GET" | "POST" | "PUT" | "DELETE"
  - url: string
  - headers: Record<string,string>
  - body_json: any
- pass_criteria: string

TestRun:
- run_id: string
- incident_id: string
- started_at: string
- status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED"
- tests: Array<{
    test_id: string
    name: string
    status: "PENDING" | "RUNNING" | "PASS" | "FAIL"
    last_update_at: string
    details: string | null
  }>

CopilotAnswer:
- incident_id: string | null
- question: string
- answer: string
- citations: Array<{ label: string; url: string }>
- created_at: string

WebSocket message envelope:
- type: "system.status" | "incident.created" | "plan.generated" | "tests.updated" | "copilot.answer"
- payload: any (mapped below)
- ts: string

Payload mapping:
- system.status -> SystemStatus
- incident.created -> IncidentCard
- plan.generated -> { incident_id: string; plan: IncidentCard["plan"] }
- tests.updated -> TestRun
- copilot.answer -> CopilotAnswer

---

## 5) REST API client (src/lib/api.ts)
Base URL = NEXT_PUBLIC_BACKEND_URL

Implement functions:
- getStatus(): GET /api/status -> SystemStatus
- setBug(enabled: boolean): POST /api/demo/bug { enabled } -> SystemStatus
- getCurrentIncident(): GET /api/incidents/current -> IncidentCard | null
- simulateIncident(mode: "INCIDENT_ON" | "INCIDENT_OFF"): POST /api/incidents/simulate -> IncidentCard | null
- runTests(incident_id: string): POST /api/tests/run { incident_id } -> TestRun
- getTestRun(run_id: string): GET /api/tests/runs/{run_id} -> TestRun
- askCopilot(incident_id: string | null, question: string): POST /api/copilot/ask -> CopilotAnswer

Error handling:
- Show a small toast or inline error banner if requests fail.
- Do not crash the page if backend is temporarily unavailable.

---

## 6) WebSocket client (src/lib/ws.ts)
Responsibilities:
- Connect to /ws
- Parse JSON messages
- Dispatch into global store reducer
- Reconnect with exponential backoff (max 5 attempts)
- Maintain wsConnected boolean for StatusBar

On message types:
- system.status: update systemStatus
- incident.created: set incident
- plan.generated: patch incident.plan
- tests.updated: set testRun
- copilot.answer: append message to chat

---

## 7) Global store (src/lib/store.ts)
Use Zustand or a React context + reducer.

State:
- systemStatus: SystemStatus | null
- incident: IncidentCard | null
- testRun: TestRun | null
- wsConnected: boolean
- loading: { initial: boolean; action: boolean }
- errors: string | null
- chat: Array<{ role: "user" | "assistant"; content: string; ts: string }>

Actions:
- hydrate():
  - call getStatus + getCurrentIncident
  - set initial loading false
- introduceBug():
  - call setBug(true)
- fixBug():
  - call setBug(false)
- startValidation():
  - if incident exists -> call runTests(incident_id)
- ask(question):
  - push user message
  - call askCopilot(incident_id, question)
  - push assistant answer
- wsSetConnected(bool)
- applyWsMessage(msg)

---

## 8) UI layout (src/app/page.tsx)
Single page with 4 sections.

Top: Status Bar
Body: two columns
- Left: Incident Feed
- Right: Test Results Panel
Right side: Copilot chat drawer/side panel

On mount:
- hydrate()
- connect websocket

---

## 9) Component specs

### 9.1 StatusBar (components/StatusBar.tsx)
Shows:
- Status badge:
  - HEALTHY -> 🟢 Healthy
  - INCIDENT_ACTIVE -> 🔴 Incident Active
  - VALIDATING -> 🟡 Validating
  - RECOVERED -> 🔵 Recovered
- MetricPills:
  - error_rate_5m
  - p95_latency_ms_5m
- Buttons:
  - Introduce Bug -> introduceBug()
  - Fix Bug -> fixBug()
Optional:
- A small “Simulate Incident” dropdown hidden behind an icon:
  - simulateIncident("INCIDENT_ON"/"INCIDENT_OFF")

Disable rules:
- If loading action, disable all
- If already incident active, Introduce Bug can remain enabled (it’s okay), but Fix Bug should be the main CTA.
- Show wsConnected indicator (green dot = connected, gray = reconnecting)

### 9.2 IncidentFeed (components/IncidentFeed.tsx)
If no incident:
- “No active incident” placeholder

If incident:
- Card header: title + detected_at + incident_id (monospace)
- Datadog summary section:
  - error rate, p95, top_error
  - evidence links as clickable anchors
- Plan section:
  - show plan_id + generated_at
  - list items sorted by priority ascending
  - each item: "#. name — what_it_checks" plus a small type badge

Edge cases:
- If incident exists but plan.items empty:
  - show “Generating Recovery Validation Plan…”

### 9.3 TestResultsPanel (components/TestResultsPanel.tsx)
If no testRun:
- placeholder “No validation run yet”

If testRun:
- show run_id + started_at + run status
- list tests (rows):
  - status icon: ⏳ (PENDING/RUNNING), ✅ (PASS), ❌ (FAIL)
  - test name
  - details (small, optional)
- update live from WS

### 9.4 CopilotSidebar (components/CopilotSidebar.tsx)
Use CopilotKit UI components OR implement a simple chat panel styled like an ops assistant.

Behavior:
- Input at bottom, messages scroll
- On send:
  - call store.ask(question)
- Suggested prompts:
  - “What caused this incident?”
  - “Is it safe now?”
  - “Which test is failing and why?”
- Render citations (if provided) under the answer as links.

Important:
- The backend is the “real brain”. The frontend should not call MiniMax directly.

---

## 10) Styling guidance
- Dark theme: background near-black, cards slightly lighter with border
- Use consistent spacing and monospaced IDs
- Subtle animations: status badge transitions, test row updates

---

## 11) End-to-end demo flow (what UI must support)
1) Load page: shows 🟢 Healthy
2) Click Introduce Bug: status updates as backend emits WS system.status and incident.created
3) Incident Feed shows plan list of 5 tests
4) Test panel shows tests failing (red)
5) Click Fix Bug: backend reruns tests; UI updates live to all green
6) Status shows RECOVERED with summary message visible in Incident Feed or StatusBar subtext

---

## 12) Acceptance checklist
- Page loads with no console errors
- Can talk to backend via REST
- WebSocket updates apply without reload
- Buttons work and do not desync state
- Incident and plan render correctly with exact schema fields
- Test rows update in real time
- Copilot chat sends questions and displays answers + citations

End of FRONTEND AGENT.md
