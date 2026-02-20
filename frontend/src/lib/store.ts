import { create } from "zustand";
import type {
    SystemStatus,
    IncidentCard,
    TestRun,
    WsMessage,
    ChatMessage,
    CopilotAnswer,
} from "./types";
import * as api from "./api";

interface AppState {
    // Data
    systemStatus: SystemStatus | null;
    incident: IncidentCard | null;
    testRun: TestRun | null;
    wsConnected: boolean;
    loading: { initial: boolean; action: boolean };
    error: string | null;
    chat: ChatMessage[];

    // Actions
    hydrate: () => Promise<void>;
    introduceBug: () => Promise<void>;
    fixBug: () => Promise<void>;
    startValidation: () => Promise<void>;
    ask: (question: string) => Promise<void>;
    wsSetConnected: (connected: boolean) => void;
    applyWsMessage: (msg: WsMessage) => void;
    clearError: () => void;
}

export const useStore = create<AppState>((set, get) => ({
    systemStatus: null,
    incident: null,
    testRun: null,
    wsConnected: false,
    loading: { initial: true, action: false },
    error: null,
    chat: [],

    hydrate: async () => {
        try {
            set({ loading: { initial: true, action: false }, error: null });
            const [status, incident] = await Promise.all([
                api.getStatus(),
                api.getCurrentIncident(),
            ]);
            set({ systemStatus: status, incident, loading: { initial: false, action: false } });
        } catch (e: any) {
            set({
                loading: { initial: false, action: false },
                error: e.message || "Failed to connect to backend",
            });
        }
    },

    introduceBug: async () => {
        try {
            set((s) => ({ loading: { ...s.loading, action: true }, error: null }));
            const status = await api.setBug(true);
            set((s) => ({
                systemStatus: status,
                loading: { ...s.loading, action: false },
            }));
        } catch (e: any) {
            set((s) => ({
                loading: { ...s.loading, action: false },
                error: e.message || "Failed to introduce bug",
            }));
        }
    },

    fixBug: async () => {
        try {
            set((s) => ({ loading: { ...s.loading, action: true }, error: null }));
            const status = await api.setBug(false);
            set((s) => ({
                systemStatus: status,
                loading: { ...s.loading, action: false },
            }));
        } catch (e: any) {
            set((s) => ({
                loading: { ...s.loading, action: false },
                error: e.message || "Failed to fix bug",
            }));
        }
    },

    startValidation: async () => {
        const { incident } = get();
        if (!incident) return;
        try {
            set((s) => ({ loading: { ...s.loading, action: true }, error: null }));
            const testRun = await api.runTests(incident.incident_id);
            set((s) => ({
                testRun,
                loading: { ...s.loading, action: false },
            }));
        } catch (e: any) {
            set((s) => ({
                loading: { ...s.loading, action: false },
                error: e.message || "Failed to start validation",
            }));
        }
    },

    ask: async (question: string) => {
        const { incident } = get();
        const userMsg: ChatMessage = {
            role: "user",
            content: question,
            citations: [],
            ts: new Date().toISOString(),
        };
        set((s) => ({ chat: [...s.chat, userMsg] }));

        try {
            const answer: CopilotAnswer = await api.askCopilot(
                incident?.incident_id ?? null,
                question
            );
            const assistantMsg: ChatMessage = {
                role: "assistant",
                content: answer.answer,
                citations: answer.citations,
                ts: answer.created_at,
            };
            set((s) => ({ chat: [...s.chat, assistantMsg] }));
        } catch (e: any) {
            const errorMsg: ChatMessage = {
                role: "assistant",
                content: "Sorry, I couldn't get an answer right now. Please try again.",
                citations: [],
                ts: new Date().toISOString(),
            };
            set((s) => ({ chat: [...s.chat, errorMsg] }));
        }
    },

    wsSetConnected: (connected: boolean) => set({ wsConnected: connected }),

    applyWsMessage: (msg: WsMessage) => {
        switch (msg.type) {
            case "system.status":
                set({ systemStatus: msg.payload as SystemStatus });
                break;
            case "incident.created":
                set({ incident: msg.payload as IncidentCard });
                break;
            case "plan.generated":
                set((s) => {
                    if (!s.incident) return s;
                    return {
                        incident: {
                            ...s.incident,
                            plan: msg.payload.plan,
                        },
                    };
                });
                break;
            case "tests.updated":
                set({ testRun: msg.payload as TestRun });
                break;
            case "copilot.answer": {
                const answer = msg.payload as CopilotAnswer;
                const assistantMsg: ChatMessage = {
                    role: "assistant",
                    content: answer.answer,
                    citations: answer.citations,
                    ts: answer.created_at,
                };
                set((s) => ({ chat: [...s.chat, assistantMsg] }));
                break;
            }
        }
    },

    clearError: () => set({ error: null }),
}));
