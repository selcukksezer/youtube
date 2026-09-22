"use client";

import * as React from "react";
import { Activity } from "lucide-react";
import { useShellStatus, type LiveEventRow } from "@/components/system-status-provider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export type { LiveEventRow };

function eventKey(event: LiveEventRow): string {
  return `${event.id}-${event.createdAt}`;
}

function timeLabel(createdAt: string): string {
  const parts = formatDate(createdAt).split(" ");
  return parts[1] || parts[0] || "";
}

function badgeVariant(level: string): "danger" | "warning" | "default" {
  if (level === "error") return "danger";
  if (level === "warning") return "warning";
  return "default";
}

/**
 * Global canli olay gunlugu. Kendi SSE baglantisini ACMAZ — kabuktaki tek
 * paylasilan baglantidan (SystemStatusProvider) beslenir; ayni sayfada iki
 * kez kullanilsa da ek soket/derleme olusmaz.
 */
export function LiveEventLog({
  title = "Canli Olay Gunlugu",
  description = "Otomasyon, kalibrasyon ve Flow adimlari anlik akar",
  maxHeight = "max-h-[480px]",
  take = 80,
}: {
  title?: string;
  description?: string;
  maxHeight?: string;
  take?: number;
}) {
  const { events: allEvents, eventsConnected } = useShellStatus();
  const endRef = React.useRef<HTMLDivElement>(null);
  const events = React.useMemo(() => allEvents.slice(-take), [allEvents, take]);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [events.length]);

  const errors = events.filter((e) => e.level === "error").length;
  const warnings = events.filter((e) => e.level === "warning").length;

  return (
    <Card>
      <CardHeader className="!flex-row items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <CardTitle>{title}</CardTitle>
          </div>
          <CardDescription>{description}</CardDescription>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={eventsConnected ? "success" : "warning"}>{eventsConnected ? "Canli" : "Baglaniyor"}</Badge>
          {errors > 0 && <Badge variant="danger">{errors} hata</Badge>}
          {warnings > 0 && <Badge variant="warning">{warnings} uyari</Badge>}
        </div>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-xs text-muted py-6 text-center">Henuz olay yok</p>
        ) : (
          <div className={`space-y-1 font-mono text-[10.5px] ${maxHeight} overflow-y-auto`}>
            {events.map((event) => (
              <div key={eventKey(event)} className="flex gap-1.5 items-start py-1 border-b border-border/40 last:border-0">
                <span className="text-muted-2 shrink-0 tabular-nums">{timeLabel(event.createdAt)}</span>
                <Badge variant={badgeVariant(event.level)} className="shrink-0 text-[9px] px-1.5">
                  {event.step || event.level}
                </Badge>
                <span className="text-muted break-all leading-relaxed">{event.message}</span>
              </div>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
