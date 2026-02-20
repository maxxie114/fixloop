"use client";

import { useStore } from "@/lib/store";
import SectionCard from "./SectionCard";

const TYPE_COLORS: Record<string, string> = {
    API: "#8b5cf6",
    UI: "#06b6d4",
    SYNTHETIC: "#f59e0b",
};

export default function IncidentFeed() {
    const incident = useStore((s) => s.incident);
    const loading = useStore((s) => s.loading);

    if (loading.initial) {
        return (
            <SectionCard title="Incident Feed">
                <div className="flex items-center justify-center py-16">
                    <div className="flex items-center gap-3 text-zinc-500 text-sm">
                        <svg
                            className="animate-spin h-4 w-4"
                            viewBox="0 0 24 24"
                            fill="none"
                        >
                            <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                            />
                        </svg>
                        Loading…
                    </div>
                </div>
            </SectionCard>
        );
    }

    if (!incident) {
        return (
            <SectionCard title="Incident Feed">
                <div className="flex flex-col items-center justify-center py-16 text-zinc-600">
                    <svg
                        className="h-10 w-10 mb-3 opacity-40"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="1.5"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <p className="text-sm font-medium">No active incident</p>
                    <p className="text-xs mt-1 text-zinc-700">
                        System is operating normally
                    </p>
                </div>
            </SectionCard>
        );
    }

    const { incident_id, title, detected_at, datadog_summary, plan } = incident;
    const hasPlan = plan?.items && plan.items.length > 0;
    const sortedItems = hasPlan
        ? [...plan.items].sort((a, b) => a.priority - b.priority)
        : [];

    return (
        <SectionCard title="Incident Feed">
            <div className="space-y-5">
                {/* Incident header */}
                <div>
                    <div className="flex items-start justify-between gap-3">
                        <h3 className="text-white font-semibold text-base leading-snug">
                            {title}
                        </h3>
                        <span className="shrink-0 rounded bg-red-600/20 border border-red-600/30 px-2 py-0.5 text-[10px] font-mono text-red-400">
                            {incident_id}
                        </span>
                    </div>
                    <p className="text-xs text-zinc-500 mt-1 font-mono">
                        Detected {new Date(detected_at).toLocaleTimeString()}
                    </p>
                </div>

                {/* Datadog summary */}
                <div className="rounded-lg bg-[#0a0a0a] border border-[#1a1a1a] p-4 space-y-3">
                    <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                        Datadog Signal
                    </h4>
                    <div className="grid grid-cols-3 gap-3">
                        <div>
                            <p className="text-[10px] text-zinc-600 uppercase">Error Rate</p>
                            <p className="text-sm font-mono text-red-400 font-semibold">
                                {datadog_summary.signal.error_rate_5m.toFixed(1)}%
                            </p>
                        </div>
                        <div>
                            <p className="text-[10px] text-zinc-600 uppercase">P95 Latency</p>
                            <p className="text-sm font-mono text-yellow-400 font-semibold">
                                {Math.round(datadog_summary.signal.p95_latency_ms_5m)}ms
                            </p>
                        </div>
                        <div>
                            <p className="text-[10px] text-zinc-600 uppercase">Service</p>
                            <p className="text-sm font-mono text-zinc-300">
                                {datadog_summary.service}
                            </p>
                        </div>
                    </div>
                    {datadog_summary.signal.top_error && (
                        <div className="mt-2">
                            <p className="text-[10px] text-zinc-600 uppercase">Top Error</p>
                            <p className="text-xs font-mono text-red-300/80 bg-red-900/10 rounded px-2 py-1 mt-1">
                                {datadog_summary.signal.top_error}
                            </p>
                        </div>
                    )}
                    {datadog_summary.evidence_links.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                            {datadog_summary.evidence_links.map((link, i) => (
                                <a
                                    key={i}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[11px] text-purple-400 hover:text-purple-300 underline underline-offset-2 transition-colors"
                                >
                                    {link.label} ↗
                                </a>
                            ))}
                        </div>
                    )}
                </div>

                {/* Plan */}
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                            Recovery Validation Plan
                        </h4>
                        {hasPlan && (
                            <span className="text-[10px] font-mono text-zinc-600">
                                {plan.plan_id}
                            </span>
                        )}
                    </div>

                    {!hasPlan ? (
                        <div className="flex items-center gap-3 py-6 justify-center text-zinc-500">
                            <svg
                                className="animate-spin h-4 w-4"
                                viewBox="0 0 24 24"
                                fill="none"
                            >
                                <circle
                                    className="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                />
                                <path
                                    className="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                                />
                            </svg>
                            <span className="text-sm">
                                Generating Recovery Validation Plan…
                            </span>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {sortedItems.map((item) => (
                                <div
                                    key={item.test_id}
                                    className="flex items-start gap-3 rounded-lg bg-[#0a0a0a] border border-[#1a1a1a] p-3 hover:border-[#2a2a2a] transition-colors"
                                >
                                    <span className="shrink-0 text-xs font-bold text-zinc-500 w-5 text-right mt-0.5">
                                        {item.priority}.
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm text-white font-medium truncate">
                                                {item.name}
                                            </span>
                                            <span
                                                className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                                                style={{
                                                    backgroundColor: `${TYPE_COLORS[item.type]}20`,
                                                    color: TYPE_COLORS[item.type],
                                                    border: `1px solid ${TYPE_COLORS[item.type]}40`,
                                                }}
                                            >
                                                {item.type}
                                            </span>
                                        </div>
                                        <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                                            {item.what_it_checks}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </SectionCard>
    );
}
