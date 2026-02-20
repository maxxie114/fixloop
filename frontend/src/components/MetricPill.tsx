"use client";

interface MetricPillProps {
    label: string;
    value: string;
    color?: string;
}

export default function MetricPill({ label, value, color }: MetricPillProps) {
    return (
        <div
            className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium"
            style={{
                backgroundColor: color ? `${color}15` : "rgba(255,255,255,0.06)",
                border: `1px solid ${color || "rgba(255,255,255,0.1)"}`,
                color: color || "#a1a1aa",
            }}
        >
            <span className="opacity-70">{label}</span>
            <span className="font-mono font-semibold">{value}</span>
        </div>
    );
}
