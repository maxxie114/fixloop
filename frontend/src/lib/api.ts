import type { SystemStatus, IncidentCard, TestRun, CopilotAnswer } from "./types";

const BASE_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function request<T>(
    path: string,
    options?: RequestInit
): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json();
}

export function getStatus(): Promise<SystemStatus> {
    return request<SystemStatus>("/api/status");
}

export function setBug(enabled: boolean): Promise<SystemStatus> {
    return request<SystemStatus>("/api/demo/bug", {
        method: "POST",
        body: JSON.stringify({ enabled }),
    });
}

export function getCurrentIncident(): Promise<IncidentCard | null> {
    return request<IncidentCard | null>("/api/incidents/current");
}

export function simulateIncident(
    mode: "INCIDENT_ON" | "INCIDENT_OFF"
): Promise<IncidentCard | null> {
    return request<IncidentCard | null>("/api/incidents/simulate", {
        method: "POST",
        body: JSON.stringify({ mode }),
    });
}

export function runTests(incident_id: string): Promise<TestRun> {
    return request<TestRun>("/api/tests/run", {
        method: "POST",
        body: JSON.stringify({ incident_id }),
    });
}

export function getTestRun(run_id: string): Promise<TestRun> {
    return request<TestRun>(`/api/tests/runs/${run_id}`);
}

export function askCopilot(
    incident_id: string | null,
    question: string
): Promise<CopilotAnswer> {
    return request<CopilotAnswer>("/api/copilot/ask", {
        method: "POST",
        body: JSON.stringify({ incident_id, question }),
    });
}
