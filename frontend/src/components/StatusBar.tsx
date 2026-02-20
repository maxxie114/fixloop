"use client";

import { useStore } from "@/lib/store";
import MetricPill from "./MetricPill";
import type { StatusEnum } from "@/lib/types";

const STATUS_CONFIG: Record<
    StatusEnum,
    { label: string; color: string; pulse: boolean }
> = {
    HEALTHY: { label: "Healthy", color: "#22c55e", pulse: false },
    INCIDENT_ACTIVE: { label: "Incident Active", color: "#ef4444", pulse: true },
    VALIDATING: { label: "Validating", color: "#eab308", pulse: true },
    RECOVERED: { label: "Recovered", color: "#3b82f6", pulse: false },
};

export default function StatusBar() {
    const { systemStatus, wsConnected, loading, error, clearError, introduceBug, fixBug } =
        useStore();

    const status = systemStatus?.status || "HEALTHY";
    const config = STATUS_CONFIG[status];

    return (
        <div className="relative border-b border-[#222] bg-[#0d0d0d]">
            {/* Error banner */}
            {error && (
                <div className="flex items-center justify-between bg-red-900/30 border-b border-red-800/50 px-5 py-2 text-xs text-red-300">
                    <span>⚠ {error}</span>
                    <button
                        onClick={clearError}
                        className="ml-4 text-red-400 hover:text-red-200 transition-colors"
                    >
                        ✕
                    </button>
                </div>
            )}

            <div className="flex items-center justify-between px-6 py-4">
                {/* Left: Logo + Status */}
                <div className="flex items-center gap-5">
                    <h1 className="text-lg font-bold text-white tracking-tight">
                        <span className="text-zinc-500">Fix</span>Loop
                    </h1>

                    <div className="h-5 w-px bg-[#333]" />

                    <div className="flex items-center gap-2.5">
                        <span
                            className="relative flex h-2.5 w-2.5"
                            aria-label={config.label}
                        >
                            {config.pulse && (
                                <span
                                    className="absolute inset-0 rounded-full animate-ping opacity-50"
                                    style={{ backgroundColor: config.color }}
                                />
                            )}
                            <span
                                className="relative inline-flex h-2.5 w-2.5 rounded-full"
                                style={{ backgroundColor: config.color }}
                            />
                        </span>
                        <span
                            className="text-sm font-medium transition-colors duration-200"
                            style={{ color: config.color }}
                        >
                            {config.label}
                        </span>
                    </div>
                </div>

                {/* Center: Metrics */}
                <div className="flex items-center gap-3">
                    <MetricPill
                        label="Error Rate"
                        value={
                            systemStatus
                                ? `${systemStatus.error_rate_5m.toFixed(1)}%`
                                : "—"
                        }
                        color={
                            systemStatus && systemStatus.error_rate_5m > 5
                                ? "#ef4444"
                                : undefined
                        }
                    />
                    <MetricPill
                        label="P95"
                        value={
                            systemStatus
                                ? `${Math.round(systemStatus.p95_latency_ms_5m)}ms`
                                : "—"
                        }
                        color={
                            systemStatus && systemStatus.p95_latency_ms_5m > 500
                                ? "#eab308"
                                : undefined
                        }
                    />
                </div>

                {/* Right: Actions + WS indicator */}
                <div className="flex items-center gap-3">
                    <button
                        onClick={introduceBug}
                        disabled={loading.action}
                        className="rounded-lg bg-red-600/20 border border-red-600/40 px-4 py-2 text-xs font-semibold text-red-400 hover:bg-red-600/30 hover:border-red-500/60 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        Introduce Bug
                    </button>
                    <button
                        onClick={fixBug}
                        disabled={loading.action}
                        className="rounded-lg bg-emerald-600/20 border border-emerald-600/40 px-4 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-600/30 hover:border-emerald-500/60 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        Fix Bug
                    </button>

                    {/* WS connection dot */}
                    <div className="ml-2 relative group">
                        <span
                            className="inline-flex h-2 w-2 rounded-full transition-colors duration-300"
                            style={{
                                backgroundColor: wsConnected ? "#22c55e" : "#71717a",
                            }}
                        />
                        <span className="absolute -bottom-7 right-0 hidden group-hover:block whitespace-nowrap rounded bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400 border border-[#333]">
                            WS {wsConnected ? "Connected" : "Disconnected"}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
