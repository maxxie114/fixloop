import type { WsMessage } from "./types";

type WsCallback = (msg: WsMessage) => void;

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;

let socket: WebSocket | null = null;
let retryCount = 0;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let onMessageCb: WsCallback | null = null;
let onConnectedCb: ((connected: boolean) => void) | null = null;

function getWsUrl(): string {
    const backend =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const wsProtocol = backend.startsWith("https") ? "wss" : "ws";
    const host = backend.replace(/^https?:\/\//, "");
    return `${wsProtocol}://${host}/ws`;
}

function connect() {
    if (socket?.readyState === WebSocket.OPEN) return;

    const url = getWsUrl();
    socket = new WebSocket(url);

    socket.onopen = () => {
        retryCount = 0;
        onConnectedCb?.(true);
    };

    socket.onmessage = (event) => {
        try {
            const msg: WsMessage = JSON.parse(event.data);
            onMessageCb?.(msg);
        } catch {
            console.warn("[WS] Failed to parse message", event.data);
        }
    };

    socket.onclose = () => {
        onConnectedCb?.(false);
        scheduleReconnect();
    };

    socket.onerror = () => {
        socket?.close();
    };
}

function scheduleReconnect() {
    if (retryCount >= MAX_RETRIES) {
        console.warn("[WS] Max retries reached, giving up");
        return;
    }
    const delay = BASE_DELAY_MS * Math.pow(2, retryCount);
    retryCount++;
    retryTimer = setTimeout(connect, delay);
}

export function connectWs(
    onMessage: WsCallback,
    onConnected: (connected: boolean) => void
) {
    onMessageCb = onMessage;
    onConnectedCb = onConnected;
    connect();
}

export function disconnectWs() {
    if (retryTimer) clearTimeout(retryTimer);
    retryCount = MAX_RETRIES; // prevent reconnect
    socket?.close();
    socket = null;
    onMessageCb = null;
    onConnectedCb = null;
}
