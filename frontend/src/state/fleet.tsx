import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { errorText } from "../api/errors";
import { useStream, type StreamStatus } from "../api/stream";
import type { FleetKpi, PanelSummary, StreamMessage } from "../api/types";

const REST_REFRESH_MS = 30_000; // WebSocket kopsa bile liste bayatlamaz
const ALARM_RELOAD_DEBOUNCE_MS = 1_000; // alarm seli sirasinda listeyi saniyede bir kez yenile

export interface FleetState {
  panels: PanelSummary[];
  loaded: boolean;
  error: string | null;
  kpi: FleetKpi | null;
  stream: StreamStatus;
  lastSync: number | null;
  /** pano_id -> son canli guncelleme zamani; detay ekrani bunu izleyip yeniden yukler. */
  touched: Record<string, number>;
}

const FleetContext = createContext<FleetState | null>(null);

export function FleetProvider({ children }: { children: ReactNode }) {
  const [panels, setPanels] = useState<PanelSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kpi, setKpi] = useState<FleetKpi | null>(null);
  const [lastSync, setLastSync] = useState<number | null>(null);
  const [touched, setTouched] = useState<Record<string, number>>({});
  const alarmReload = useRef<ReturnType<typeof setTimeout>>();

  const reload = useCallback(async () => {
    try {
      setPanels(await api.panels());
      setError(null);
      setLastSync(Date.now());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoaded(true);
    }
    try {
      setKpi(await api.fleetKpi());
    } catch {
      // /fleet/kpi her backend surumunde yok; ust bilgi o durumda panolardan hesaplanir.
      setKpi(null);
    }
  }, []);

  useEffect(() => {
    void reload();
    const timer = setInterval(() => void reload(), REST_REFRESH_MS);
    return () => {
      clearInterval(timer);
      clearTimeout(alarmReload.current);
    };
  }, [reload]);

  const onMessage = useCallback(
    (message: StreamMessage) => {
      const now = Date.now();
      switch (message.type) {
        case "tel": {
          const summary = message.payload;
          setPanels((prev) => {
            const index = prev.findIndex((p) => p.pano_id === summary.pano_id);
            if (index < 0) return [...prev, summary];
            const next = prev.slice();
            next[index] = summary;
            return next;
          });
          setTouched((t) => ({ ...t, [summary.pano_id]: now }));
          setLastSync(now);
          break;
        }
        case "alarm":
          setTouched((t) => ({ ...t, [message.payload.pano_id]: now }));
          clearTimeout(alarmReload.current);
          alarmReload.current = setTimeout(() => void reload(), ALARM_RELOAD_DEBOUNCE_MS);
          break;
        case "kpi":
          setKpi(message.payload);
          break;
        case "hello":
          break;
      }
    },
    [reload],
  );

  const stream = useStream(onMessage);

  const value = useMemo<FleetState>(
    () => ({ panels, loaded, error, kpi, stream, lastSync, touched }),
    [panels, loaded, error, kpi, stream, lastSync, touched],
  );

  return <FleetContext.Provider value={value}>{children}</FleetContext.Provider>;
}

export function useFleet(): FleetState {
  const context = useContext(FleetContext);
  if (!context) throw new Error("useFleet, FleetProvider içinde kullanılmalı");
  return context;
}
