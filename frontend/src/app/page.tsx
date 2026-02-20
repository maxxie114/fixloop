"use client";

import { useEffect } from "react";
import { useStore } from "@/lib/store";
import { connectWs, disconnectWs } from "@/lib/ws";
import StatusBar from "@/components/StatusBar";
import IncidentFeed from "@/components/IncidentFeed";
import TestResultsPanel from "@/components/TestResultsPanel";
import ChatSidebar from "@/components/ChatSidebar";

export default function DashboardPage() {
  const { hydrate, wsSetConnected, applyWsMessage } = useStore();

  useEffect(() => {
    hydrate();
    connectWs(applyWsMessage, wsSetConnected);
    return () => disconnectWs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        <StatusBar />

        <div className="flex-1 grid grid-cols-2 gap-4 p-4 overflow-hidden">
          <div className="overflow-y-auto pr-1 custom-scrollbar">
            <IncidentFeed />
          </div>
          <div className="overflow-y-auto pl-1 custom-scrollbar">
            <TestResultsPanel />
          </div>
        </div>
      </div>

      {/* Chat sidebar — always visible */}
      <div className="w-[340px] shrink-0">
        <ChatSidebar />
      </div>
    </div>
  );
}
