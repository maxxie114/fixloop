"use client";

import { useStore } from "@/lib/store";
import { useState, useRef, useEffect } from "react";

const SUGGESTED_PROMPTS = [
    "What caused this incident?",
    "Is it safe to recover now?",
    "Which test is failing and why?",
    "What does the recovery plan check?",
];

export default function ChatSidebar() {
    const { chat, ask } = useStore();
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [chat]);

    const handleSend = async (question?: string) => {
        const q = question || input.trim();
        if (!q || sending) return;
        setInput("");
        setSending(true);
        await ask(q);
        setSending(false);
    };

    return (
        <div className="flex flex-col h-full bg-[#0d0d0d] border-l border-[#222]">
            {/* Header */}
            <div className="px-4 py-3 border-b border-[#222]">
                <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                    <svg
                        className="h-4 w-4 text-purple-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="2"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
                        />
                    </svg>
                    Ask FixLoop
                </h2>
            </div>

            {/* Messages area */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {chat.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full gap-4">
                        <div className="text-center">
                            <p className="text-sm text-zinc-500 mb-1">Ask about the incident</p>
                            <p className="text-xs text-zinc-700">
                                Powered by MiniMax M2.5
                            </p>
                        </div>
                        <div className="flex flex-col gap-2 w-full">
                            {SUGGESTED_PROMPTS.map((prompt) => (
                                <button
                                    key={prompt}
                                    onClick={() => handleSend(prompt)}
                                    disabled={sending}
                                    className="text-left text-xs text-zinc-400 bg-[#161616] hover:bg-[#1c1c1c] border border-[#222] hover:border-[#333] rounded-lg px-3 py-2.5 transition-all disabled:opacity-40"
                                >
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    chat.map((msg, i) => (
                        <div
                            key={i}
                            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"
                                }`}
                        >
                            <div
                                className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm ${msg.role === "user"
                                    ? "bg-purple-600/20 border border-purple-600/30 text-purple-100"
                                    : "bg-[#161616] border border-[#222] text-zinc-300"
                                    }`}
                            >
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                                {msg.citations.length > 0 && (
                                    <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-[#2a2a2a]">
                                        {msg.citations.map((cite, j) => (
                                            <a
                                                key={j}
                                                href={cite.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-[10px] text-purple-400 hover:text-purple-300 underline underline-offset-2 transition-colors"
                                            >
                                                {cite.label} ↗
                                            </a>
                                        ))}
                                    </div>
                                )}
                                <p className="text-[10px] text-zinc-700 mt-1.5 font-mono">
                                    {new Date(msg.ts).toLocaleTimeString()}
                                </p>
                            </div>
                        </div>
                    ))
                )}
                {sending && (
                    <div className="flex justify-start">
                        <div className="bg-[#161616] border border-[#222] rounded-xl px-3.5 py-2.5 text-sm text-zinc-500">
                            <span className="inline-flex gap-1">
                                <span className="animate-bounce" style={{ animationDelay: "0ms" }}>●</span>
                                <span className="animate-bounce" style={{ animationDelay: "150ms" }}>●</span>
                                <span className="animate-bounce" style={{ animationDelay: "300ms" }}>●</span>
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <div className="p-3 border-t border-[#222]">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Ask about the incident…"
                        disabled={sending}
                        className="flex-1 bg-[#161616] border border-[#222] focus:border-purple-600/50 rounded-lg px-3 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-colors disabled:opacity-40"
                    />
                    <button
                        onClick={() => handleSend()}
                        disabled={!input.trim() || sending}
                        className="rounded-lg bg-purple-600/20 border border-purple-600/40 px-3.5 py-2.5 text-purple-400 hover:bg-purple-600/30 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                        <svg
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth="2"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                            />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
