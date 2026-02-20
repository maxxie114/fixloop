// FixLoop shared types — matches BACKEND contract exactly

export type StatusEnum = "HEALTHY" | "INCIDENT_ACTIVE" | "VALIDATING" | "RECOVERED";

export type SystemStatus = {
  status: StatusEnum;
  error_rate_5m: number;
  p95_latency_ms_5m: number;
  active_incident_id: string | null;
  updated_at: string;
};

export type PlanItem = {
  test_id: string;
  name: string;
  type: "API" | "UI" | "SYNTHETIC";
  priority: number;
  what_it_checks: string;
  target: {
    method: "GET" | "POST" | "PUT" | "DELETE";
    url: string;
    headers: Record<string, string>;
    body_json: any;
  };
  pass_criteria: string;
};

export type IncidentCard = {
  incident_id: string;
  title: string;
  detected_at: string;
  datadog_summary: {
    monitor_id: string | null;
    service: string;
    signal: {
      error_rate_5m: number;
      p95_latency_ms_5m: number;
      top_error: string | null;
    };
    evidence_links: Array<{ label: string; url: string }>;
  };
  plan: {
    plan_id: string;
    generated_at: string;
    items: PlanItem[];
  };
};

export type TestRunStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type TestItemStatus = "PENDING" | "RUNNING" | "PASS" | "FAIL";

export type TestRun = {
  run_id: string;
  incident_id: string;
  started_at: string;
  status: TestRunStatus;
  tests: Array<{
    test_id: string;
    name: string;
    status: TestItemStatus;
    last_update_at: string;
    details: string | null;
  }>;
};

export type CopilotAnswer = {
  incident_id: string | null;
  question: string;
  answer: string;
  citations: Array<{ label: string; url: string }>;
  created_at: string;
};

export type WsMessageType =
  | "system.status"
  | "incident.created"
  | "plan.generated"
  | "tests.updated"
  | "copilot.answer";

export type WsMessage = {
  type: WsMessageType;
  payload: any;
  ts: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations: Array<{ label: string; url: string }>;
  ts: string;
};
