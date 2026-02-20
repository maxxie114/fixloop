"use client";

import { useStore } from "@/lib/store";
import SectionCard from "./SectionCard";
import type { TestItemStatus } from "@/lib/types";

const STATUS_ICON: Record<TestItemStatus, { icon: string; classes: string }> = {
    PENDING: { icon: "⏳", classes: "animate-pulse" },
    RUNNING: { icon: "⏳", classes: "animate-pulse" },
    PASS: { icon: "✅", classes: "" },
    FAIL: { icon: "❌", classes: "" },
};

const STATUS_BG: Record<TestItemStatus, string> = {
    PENDING: "border-[#1a1a1a]",
    RUNNING: "border-yellow-600/30 bg-yellow-900/5",
    PASS: "border-emerald-600/30 bg-emerald-900/5",
    FAIL: "border-red-600/30 bg-red-900/5",
};

const OVERALL_STATUS_COLORS: Record<string, { text: string; bg: string; border: string }> = {
    QUEUED: { text: "text-zinc-400", bg: "bg-zinc-800/50", border: "border-zinc-700/50" },
    RUNNING: { text: "text-yellow-400", bg: "bg-yellow-900/20", border: "border-yellow-700/30" },
    COMPLETED: { text: "text-emerald-400", bg: "bg-emerald-900/20", border: "border-emerald-700/30" },
    FAILED: { text: "text-red-400", bg: "bg-red-900/20", border: "border-red-700/30" },
};

export default function TestResultsPanel() {
    const testRun = useStore((s) => s.testRun);
    const loading = useStore((s) => s.loading);
    const startValidation = useStore((s) => s.startValidation);
    const incident = useStore((s) => s.incident);

    if (!testRun) {
        return (
            <SectionCard
                title="Test Results"
                headerRight={
                    incident ? (
                        <button
                            onClick={startValidation}
                            disabled={loading.action}
                            className="rounded-lg bg-blue-600/20 border border-blue-600/40 px-3 py-1.5 text-[11px] font-semibold text-blue-400 hover:bg-blue-600/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            Run Validation
                        </button>
                    ) : null
                }
            >
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
                            d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
                        />
                    </svg>
                    <p className="text-sm font-medium">No validation run yet</p>
                    <p className="text-xs mt-1 text-zinc-700">
                        Tests will run after an incident is detected
                    </p>
                </div>
            </SectionCard>
        );
    }

    const overallConfig = OVERALL_STATUS_COLORS[testRun.status] || OVERALL_STATUS_COLORS.QUEUED;
    const passed = testRun.tests.filter((t) => t.status === "PASS").length;
    const total = testRun.tests.length;

    return (
        <SectionCard
            title="Test Results"
            headerRight={
                <div className="flex items-center gap-3">
                    <span
                        className={`rounded px-2 py-0.5 text-[10px] font-semibold ${overallConfig.text} ${overallConfig.bg} border ${overallConfig.border}`}
                    >
                        {testRun.status}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-600">
                        {testRun.run_id}
                    </span>
                </div>
            }
        >
            <div className="space-y-2">
                {testRun.tests.map((test) => {
                    const statusInfo = STATUS_ICON[test.status];
                    const bg = STATUS_BG[test.status];
                    return (
                        <div
                            key={test.test_id}
                            className={`flex items-center gap-3 rounded-lg border p-3 transition-all duration-300 ${bg}`}
                        >
                            <span className={`text-base shrink-0 ${statusInfo.classes}`}>
                                {statusInfo.icon}
                            </span>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-white font-medium truncate">
                                    {test.name}
                                </p>
                                {test.details && (
                                    <p className="text-xs text-zinc-500 mt-0.5 truncate">
                                        {test.details}
                                    </p>
                                )}
                            </div>
                            <span className="text-[10px] font-mono text-zinc-600 shrink-0">
                                {new Date(test.last_update_at).toLocaleTimeString()}
                            </span>
                        </div>
                    );
                })}

                {/* Summary row */}
                {(testRun.status === "COMPLETED" || testRun.status === "FAILED") && (
                    <div className="mt-3 pt-3 border-t border-[#222] flex items-center justify-between">
                        <span className="text-sm text-zinc-400">
                            <span
                                className={`font-semibold ${passed === total ? "text-emerald-400" : "text-red-400"
                                    }`}
                            >
                                {passed}/{total}
                            </span>{" "}
                            tests passing
                        </span>
                        <span className="text-[10px] font-mono text-zinc-600">
                            Started{" "}
                            {new Date(testRun.started_at).toLocaleTimeString()}
                        </span>
                    </div>
                )}
            </div>
        </SectionCard>
    );
}
