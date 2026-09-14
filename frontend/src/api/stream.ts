import { useEffect, useRef, useState } from "react";
import { usingMocks } from "./client";
import { startMockStream } from "./mock";
import type { StreamMessage } from "./types";

export type StreamStatus = "connecting" | "open" | "down";

const MAX_BACKOFF_S = 30; // openapi.yaml x-websocket.reconnect: 2^n sn, en fazla 30

/** WS /api/v1/stream aboneligi. Koparsa ustel geri cekilmeyle yeniden baglanir. */
export function useStream(onMessage: (message: StreamMessage) => void): StreamStatus {
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const handler = useRef(onMessage);

  useEffect(() => {
    handler.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (usingMocks) {
      setStatus("open");
      return startMockStream((m) => handler.current(m));
    }

    let socket: WebSocket | null = null;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    const connect = () => {
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${location.host}/api/v1/stream`);
      socket.onopen = () => {
        attempt = 0;
        setStatus("open");
      };
      socket.onmessage = (event) => {
        try {
          handler.current(JSON.parse(event.data as string) as StreamMessage);
        } catch (error) {
          console.warn("Akıştan çözümlenemeyen mesaj atlandı", error);
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        setStatus("down");
        const delayS = Math.min(MAX_BACKOFF_S, 2 ** attempt);
        attempt += 1;
        timer = setTimeout(connect, delayS * 1000);
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, []);

  return status;
}
