# AGENT.md (FRONTEND) — Recovery Validation Dashboard
Owner: Frontend Coding Agent
Scope: Next.js app with a single ops-style page: Status Bar + Incident Feed + Test Results + Chat Sidebar
Goal: A live dashboard that talks to the backend via REST + WebSocket using the shared contract.

---

## 0) One-sentence summary
Build a dark-themed ops dashboard that shows system status, incident details, a MiniMax-generated Recovery Validation Plan, live TestSprite results, and a chat sidebar that sends questions to the backend /api/copilot/ask endpoint.

---

## 1) Hard constraints
- Must work with backend contract exactly (fields, endpoints, WS message types).
- Must be demo-friendly: obvious status changes, smooth live updates, no refresh required.
- Tech: Next.js + Tailwind CSS only. No CopilotKit. No external UI libraries.
- Chat sidebar calls POST /api/copilot/ask on the backend. Frontend does NOT call MiniMax directly.

References:
- Tailwind: https://tailwindcss.com/docs
- Next.js: https://nextjs.org/docs

---

## 2) Project structure (recommended)
```
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
      ChatSidebar.tsx
      MetricPill.tsx
      SectionCard.tsx
    lib/
      types.ts
      api.ts
      ws.ts
      store.ts
```

---

## 3) Environment variables (.env.local.example)
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```
Derive WebSocket URL from backend URL:
- if backend is http://localhost:8000 -> ws://localhost:8000/ws
- if https -> wss

---

## 4) Shared contract (MUST MATCH BACKEND EXACTLY)
Do not invent or rename fields. Use the same enums.

### 4.1 Types (implement in src/lib/types.ts)

```typescript
type StatusEnum = "HEALTHY" | "INCIDENT_ACTIVE" | "VALIDATING" | "RECOVERED"

type SystemStatus = {
  status: StatusEnum
  error_rate_5m: number
  p95_latency_ms_5m: number
  active_incident_id: string | null
  updated_at: string
}

type PlanItem = {
  test_id: string
  name: string
  type: "API" | "UI" | "SYNTHETIC"
  priority: number
  what_it_checks: string
  target: {
    method: "GET" | "POST" | "PUT" | "DELETE"
    url: string
    headers: Record<string, string>
    body_json: any
  }
  pass_criteria: string
}

type IncidentCard = {
  incident_id: string
  title: string
  detected_at: string
  datadog_summary: {
    monitor_id: string | null
    service: string
    signal: {
      error_rate_5m: number
      p95_latency_ms_5m: number
      top_error: string | null
    }
    evidence_links: Array<{ label: string; url: string }>
  }
  plan: {
    plan_id: string
    generated_at: string
    items: PlanItem[]
  }
}

type TestRun = {
  run_id: string
  incident_id: string
  started_at: string
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED"
  tests: Array<{
    test_id: string
    name: string
    status: "PENDING" | "RUNNING" | "PASS" | "FAIL"
    last_update_at: string
    details: string | null
  }>
}

type CopilotAnswer = {
  incident_id: string | null
  question: string
  answer: string
  citations: Array<{ label: string; url: string }>
  created_at: string
}

type WsMessage = {
  type: "system.status" | "incident.created" | "plan.generated" | "tests.updated" | "copilot.answer"
  payload: any
  ts: string
}
```

---

## 5) REST API client (src/lib/api.ts)

Base URL = NEXT_PUBLIC_BACKEND_URL

Implement these functions:

```typescript
getStatus(): GET /api/status -> SystemStatus
setBug(enabled: boolean): POST /api/demo/bug { enabled } -> SystemStatus
getCurrentIncident(): GET /api/incidents/current -> IncidentCard | null
simulateIncident(mode: "INCIDENT_ON" | "INCIDENT_OFF"): POST /api/incidents/simulate -> IncidentCard | null
runTests(incident_id: string): POST /api/tests/run { incident_id } -> TestRun
getTestRun(run_id: string): GET /api/tests/runs/{run_id} -> TestRun
askCopilot(incident_id: string | null, question: string): POST /api/copilot/ask -> CopilotAnswer
```

Error handling:
- Show a small inline error banner if requests fail.
- Do not crash the page if backend is temporarily unavailable.

---

## 6) WebSocket client (src/lib/ws.ts)

Responsibilities:
- Connect to /ws
- Parse JSON messages
- Dispatch into global store
- Reconnect with exponential backoff (max 5 attempts)
- Maintain wsConnected boolean for StatusBar

On message types:
- system.status -> update systemStatus in store
- incident.created -> set incident in store
- plan.generated -> patch incident.plan in store
- tests.updated -> set testRun in store
- copilot.answer -> append message to chat in store

---

## 7) Global store (src/lib/store.ts)

Use Zustand or React context + useReducer.

State:
```typescript
{
  systemStatus: SystemStatus | null
  incident: IncidentCard | null
  testRun: TestRun | null
  wsConnected: boolean
  loading: { initial: boolean; action: boolean }
  error: string | null
  chat: Array<{ role: "user" | "assistant"; content: string; citations: any[]; ts: string }>
}
```

Actions:
- hydrate() — call getStatus + getCurrentIncident on mount
- introduceBug() — call setBug(true)
- fixBug() — call setBug(false)
- startValidation() — if incident exists, call runTests(incident_id)
- ask(question) — push user message, call askCopilot, push assistant answer
- wsSetConnected(bool)
- applyWsMessage(msg)

---

## 8) UI layout (src/app/page.tsx)

Single page, 3 main regions:

```
+--------------------------------------------------+
|                  STATUS BAR                      |
+--------------------------------------------------+
|                          |                       |
|   INCIDENT FEED          |  TEST RESULTS PANEL   |
|   (left, scrollable)     |  (right, scrollable)  |
|                          |                       |
+--------------------------------------------------+
         CHAT SIDEBAR (fixed right drawer)
```

On mount:
- hydrate()
- connect websocket

---

## 9) Component specs

### 9.1 StatusBar (components/StatusBar.tsx)

Shows:
- Status badge with color + label:
  - HEALTHY -> 🟢 green dot + "Healthy"
  - INCIDENT_ACTIVE -> 🔴 pulsing red dot + "Incident Active"
  - VALIDATING -> 🟡 yellow dot + "Validating"
  - RECOVERED -> 🔵 blue dot + "Recovered"
- MetricPills:
  - error_rate_5m (e.g. "Error Rate: 0.1%")
  - p95_latency_ms_5m (e.g. "P95: 142ms")
- Buttons:
  - "Introduce Bug" -> introduceBug()
  - "Fix Bug" -> fixBug()
- WS connection indicator: small dot top-right (green = connected, gray = reconnecting)

Disable rules:
- Disable all buttons while loading.action is true

---

### 9.2 IncidentFeed (components/IncidentFeed.tsx)

If no incident:
- Show "No active incident" placeholder centered in the panel

If incident exists:
- Card header: title + detected_at + incident_id in monospace
- Datadog summary section:
  - error_rate_5m, p95_latency_ms_5m, top_error
  - evidence_links as clickable anchor tags (open in new tab)
- Plan section:
  - show plan_id + generated_at timestamp
  - list items sorted by priority ascending
  - each item: "{priority}. {name} — {what_it_checks}" + small type badge (API / UI / SYNTHETIC)

Edge case:
- If incident exists but plan.items is empty -> show "Generating Recovery Validation Plan…" with a subtle loading indicator

---

### 9.3 TestResultsPanel (components/TestResultsPanel.tsx)

If no testRun:
- Show "No validation run yet" placeholder

If testRun exists:
- Header: run_id (monospace) + started_at + overall status badge
- Test rows:
  - ⏳ for PENDING or RUNNING (with subtle pulse animation)
  - ✅ for PASS (green background tint)
  - ❌ for FAIL (red background tint)
  - test name + details (small text, optional)
- Updates live from WS without re-mount
- Summary row at bottom when status is COMPLETED:
  - "{passed}/{total} tests passing"

---

### 9.4 ChatSidebar (components/ChatSidebar.tsx)

A fixed right-side drawer. Toggle open/close with a button in the corner.

Behavior:
- Messages scroll from top, input pinned at bottom
- On send: call store.ask(question)
- Show user messages right-aligned, assistant messages left-aligned
- Under each assistant message: render citations as small clickable links if provided
- Suggested prompt chips shown when chat is empty:
  - "What caused this incident?"
  - "Is it safe to recover now?"
  - "Which test is failing and why?"
  - "What does the recovery plan check?"

Important:
- The frontend does NOT call MiniMax directly
- All answers come from POST /api/copilot/ask on the backend
- Simply POST { incident_id, question } and render the CopilotAnswer

---

## 10) Styling guidance

- Background: #0a0a0a or similar near-black
- Cards: slightly lighter (#111) with subtle border (#222)
- Accent colors: red for incidents, green for healthy/pass, yellow for validating, blue for recovered
- Monospace font for IDs, run IDs, timestamps
- Subtle transitions on status badge changes (200ms ease)
- Test row updates should flash briefly to draw the eye

---

## 11) End-to-end demo flow (what UI must support)

1. Load page -> shows 🟢 Healthy, no incident
2. Click "Introduce Bug" -> StatusBar updates to 🔴 Incident Active
3. Incident Feed populates with card + "Generating plan…"
4. Plan appears with 5 tests listed
5. Test panel shows tests running then failing (red)
6. Click "Fix Bug" -> backend reruns tests
7. Test panel updates live to all green ✅
8. StatusBar transitions to 🔵 Recovered
9. Chat sidebar available throughout for judge Q&A

---

## 12) Acceptance checklist

- [ ] Page loads with no console errors
- [ ] REST calls work (status, bug toggle, incidents, tests, copilot ask)
- [ ] WebSocket connects and updates apply without page reload
- [ ] Introduce Bug and Fix Bug buttons update state visibly
- [ ] Incident card renders with exact schema fields
- [ ] Plan items appear sorted by priority
- [ ] Test rows update in real time (PENDING -> RUNNING -> PASS/FAIL)
- [ ] Chat sends question to /api/copilot/ask and displays answer + citations
- [ ] No CopilotKit dependency anywhere

End of FRONTEND AGENT.md