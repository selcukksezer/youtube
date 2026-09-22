"use client";

import * as React from "react";
import { api } from "@/lib/client-api";

/**
 * Kabuk (sidebar + ust bar) icin paylasilan sistem durumu.
 * Tek bir SSE baglantisi ve tek fetch ile beslenir; boylece her bilesen
 * ayri ayri sunucuyu yoklamaz (otomasyon sirasinda gereksiz yuk olusmaz).
 * Canli olay gunlugu de bu TEK baglantidan beslenir — her sayfa kendi
 * EventSource'unu acarsa hem ekstra soket hem ekstra dev-derleme olusur.
 */

export interface ShellStatus {
  projectCount: number;
  runningJobs: number;
  completedClips: number;
  failedClips: number;
  browserOpen: boolean;
  openaiKeyPresent: boolean;
  flowSession: { status: string; detail: string };
}

export interface LiveEventRow {
  id: number;
  projectId?: string | null;
  level: string;
  step: string;
  message: string;
  createdAt: string;
}

const EVENTS_LIMIT = 150;

const StatusContext = React.createContext<{
  status: ShellStatus | null;
  /** SSE olaylarinda artar; sayfalar bunu izleyerek kendi verisini yenileyebilir. */
  tick: number;
  refresh: () => void;
  events: LiveEventRow[];
  eventsConnected: boolean;
}>({
  status: null,
  tick: 0,
  refresh: () => {},
  events: [],
  eventsConnected: false,
});

export function useShellStatus() {
  return React.useContext(StatusContext);
}

export function SystemStatusProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<ShellStatus | null>(null);
  const [tick, setTick] = React.useState(0);
  const [events, setEvents] = React.useState<LiveEventRow[]>([]);
  const [eventsConnected, setEventsConnected] = React.useState(false);
  const inFlight = React.useRef(false);

  const refresh = React.useCallback(() => {
    // Ayni anda tek istek: olay patlamasinda kuyruk olusmasin
    if (inFlight.current) return;
    inFlight.current = true;
    api<ShellStatus>("/api/system/status", { silent: true })
      .then(setStatus)
      .catch(() => {})
      .finally(() => {
        inFlight.current = false;
      });
  }, []);

  React.useEffect(() => {
    refresh();
    const source = new EventSource("/api/events");
    // Otomasyon sirasinda job/project olaylari saniyede birkac kez gelebilir;
    // her biri icin ayri fetch atmak sunucuyu ve sayfa gecislerini yavaslatir.
    // Kuyruklayarak 1.2 sn'de bir tek yenilemeye indirger.
    let timer: ReturnType<typeof setTimeout> | null = null;
    const bump = () => {
      if (timer) return;
      timer = setTimeout(() => {
        timer = null;
        setTick((n) => n + 1);
        refresh();
      }, 1_200);
    };
    source.addEventListener("job", bump);
    source.addEventListener("system", bump);
    source.addEventListener("project", bump);
    source.addEventListener("snapshot", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { events?: LiveEventRow[] };
      if (Array.isArray(data.events)) setEvents(data.events.slice(-EVENTS_LIMIT));
      setEventsConnected(true);
    });
    source.addEventListener("event", (e) => {
      const event = JSON.parse((e as MessageEvent).data) as LiveEventRow;
      if (!event?.id || !event.message) return;
      setEvents((prev) => {
        if (prev.some((row) => row.id === event.id)) return prev;
        return [...prev.slice(-(EVENTS_LIMIT - 1)), event];
      });
    });
    source.onopen = () => setEventsConnected(true);
    source.onerror = () => {
      // Tarayici otomatik yeniden baglanir; burada ekstra islem yok
      setEventsConnected(false);
    };
    return () => {
      if (timer) clearTimeout(timer);
      source.close();
    };
  }, [refresh]);

  const value = React.useMemo(
    () => ({ status, tick, refresh, events, eventsConnected }),
    [status, tick, refresh, events, eventsConnected]
  );
  return <StatusContext.Provider value={value}>{children}</StatusContext.Provider>;
}
