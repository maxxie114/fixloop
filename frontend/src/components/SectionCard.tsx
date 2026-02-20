"use client";

import { ReactNode } from "react";

interface SectionCardProps {
    title: string;
    children: ReactNode;
    className?: string;
    headerRight?: ReactNode;
}

export default function SectionCard({
    title,
    children,
    className = "",
    headerRight,
}: SectionCardProps) {
    return (
        <div
            className={`rounded-xl border border-[#222] bg-[#111] overflow-hidden flex flex-col h-full ${className}`}
        >
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#222]">
                <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
                    {title}
                </h2>
                {headerRight}
            </div>
            <div className="p-5 flex-1">{children}</div>
        </div>
    );
}
