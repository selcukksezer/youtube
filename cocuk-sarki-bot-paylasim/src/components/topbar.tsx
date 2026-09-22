"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ChevronRight, CircleHelp, Chrome, KeyRound, Music2 } from "lucide-react";
import { useShellStatus } from "@/components/system-status-provider";
import { BRAND, NAV } from "@/lib/brand";
import { cn } from "@/lib/utils";

const SECTION_TITLES: Array<{ match: (path: string) => boolean; label: string }> = [
  { match: (p) => p === "/", label: NAV.home.label },
  { match: (p) => p.includes("/render"), label: "Uretim" },
  { match: (p) => p.startsWith("/cocuk-sarki/"), label: "Proje" },
  { match: (p) => p === "/cocuk-sarki", label: NAV.projects.label },
  { match: (p) => p.startsWith("/setup"), label: NAV.setup.label },
  { match: (p) => p.startsWith("/flow-kalibrasyon"), label: NAV.flowCalibration.label },
  { match: (p) => p.startsWith("/settings"), label: NAV.settings.label },
];

export function Topbar() {
  const pathname = usePathname();
  const { status } = useShellStatus();
  const section = SECTION_TITLES.find((entry) => entry.match(pathname))?.label ?? "Panel";

  const flowTone =
    !status || !status.browserOpen ? "idle" : status.flowSession.status === "ready" ? "ok" : "warn";

  return (
    <header className="sticky top-0 z-30 h-[68px] shrink-0 border-b border-border/80 bg-surface/90 backdrop-blur-xl">
      <div className="flex h-full items-center justify-between gap-4 px-6 lg:px-8">
        <nav className="flex items-center gap-2 text-[13px] min-w-0" aria-label="Konum">
          <Link
            href="/"
            className="focus-ring hidden sm:inline-flex items-center gap-1.5 rounded-md px-1 py-0.5 text-muted-2 hover:text-foreground transition-colors"
          >
            <Music2 className="h-3.5 w-3.5 text-primary/70" />
            <span className="font-semibold tracking-tight">{BRAND.name}</span>
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-muted-2 shrink-0 hidden sm:block" />
          <span className="font-semibold truncate tracking-tight" aria-current="page">
            {section}
          </span>
        </nav>

        <div className="flex items-center gap-2 shrink-0">
          {status && status.runningJobs > 0 && (
            <span className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning-soft/80 px-3 py-1 text-[11px] font-semibold text-warning">
              <Activity className="h-3 w-3" />
              {status.runningJobs} uretim
            </span>
          )}
          <StatusChip
            icon={<Chrome className="h-3 w-3" />}
            label={
              !status || !status.browserOpen
                ? "Flow bekliyor"
                : status.flowSession.status === "ready"
                  ? "Flow bagli"
                  : "Flow: mudahale"
            }
            tone={flowTone}
          />
          <StatusChip
            icon={<KeyRound className="h-3 w-3" />}
            label={status?.openaiKeyPresent ? "OpenAI OK" : "OpenAI eksik"}
            tone={status?.openaiKeyPresent ? "ok" : "err"}
          />
          <span className="h-5 w-px bg-border mx-0.5" />
          <Link
            href={NAV.setup.href}
            className="focus-ring flex h-9 w-9 items-center justify-center rounded-[10px] text-muted hover:text-foreground hover:bg-surface-3 transition-colors"
            title="Kurulum rehberi"
            aria-label="Kurulum"
          >
            <CircleHelp className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}

function StatusChip({ icon, label, tone }: { icon: React.ReactNode; label: string; tone: "ok" | "warn" | "err" | "idle" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        tone === "ok" && "border-success/20 bg-success-soft/80 text-success",
        tone === "warn" && "border-warning/20 bg-warning-soft/80 text-warning",
        tone === "err" && "border-danger/20 bg-danger-soft/80 text-danger",
        tone === "idle" && "border-border bg-surface-3/70 text-muted"
      )}
    >
      {icon}
      <span className="hidden lg:inline">{label}</span>
    </span>
  );
}
