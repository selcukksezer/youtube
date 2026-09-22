"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Clapperboard,
  Crosshair,
  LayoutGrid,
  Loader2,
  Music2,
  Plus,
  Settings,
  Wand2,
} from "lucide-react";
import { useShellStatus } from "@/components/system-status-provider";
import { BRAND, NAV } from "@/lib/brand";
import { createAndOpenSongStudio } from "@/lib/create-song-project";
import { cn } from "@/lib/utils";

const NAV_MAIN = [
  { href: NAV.home.href, label: NAV.home.label, icon: LayoutGrid },
  { href: NAV.projects.href, label: NAV.projects.label, icon: Music2 },
] as const;

const NAV_SYSTEM = [
  { href: NAV.setup.href, label: NAV.setup.label, icon: Wand2 },
  { href: NAV.flowCalibration.href, label: NAV.flowCalibration.label, icon: Crosshair },
  { href: NAV.settings.href, label: NAV.settings.label, icon: Settings },
] as const;

function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/cocuk-sarki") {
    return pathname === "/cocuk-sarki" || pathname.startsWith("/cocuk-sarki/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useShellStatus();
  const [creating, setCreating] = React.useState(false);

  const health: { tone: "success" | "warning" | "danger"; label: string; detail: string } = !status
    ? { tone: "warning", label: "Baslatiliyor", detail: "Sistem durumu okunuyor" }
    : status.runningJobs > 0
      ? { tone: "warning", label: "Render aktif", detail: `${status.runningJobs} uretim gorevi calisiyor` }
      : !status.openaiKeyPresent
        ? { tone: "danger", label: "Yapilandirma eksik", detail: "OpenAI anahtari tanimlanmamis" }
        : status.flowSession.status === "ready"
          ? { tone: "success", label: "Sistem hazir", detail: "Flow oturumu acik" }
          : { tone: "success", label: "Sistem hazir", detail: "Tum servisler erisilebilir" };

  async function handleNewProject() {
    setCreating(true);
    try {
      await createAndOpenSongStudio(router);
    } finally {
      setCreating(false);
    }
  }

  return (
    <aside className="sticky top-0 h-screen w-[260px] shrink-0 border-r border-border/80 bg-surface/95 backdrop-blur-xl flex flex-col shadow-[inset_-1px_0_0_rgba(255,255,255,0.6)]">
      <Link
        href="/"
        className="group flex items-center gap-3 px-5 h-[68px] border-b border-border focus-ring"
        aria-label={`${BRAND.nameFull} — ana sayfa`}
      >
        <div className="relative flex h-10 w-10 items-center justify-center rounded-[12px] brand-gradient shadow-[0_2px_8px_-2px_rgba(79,70,229,0.35)] group-hover:scale-[1.02] transition-transform">
          <Music2 className="h-[19px] w-[19px] text-white" />
        </div>
        <div className="min-w-0">
          <div className="text-[14px] font-bold leading-tight tracking-[-0.03em] text-foreground">{BRAND.name}</div>
          <div className="text-[10px] font-medium text-muted-2 leading-tight tracking-wide uppercase">{BRAND.pipeline}</div>
        </div>
      </Link>

      <div className="px-3 pt-5">
        <button
          type="button"
          disabled={creating}
          onClick={handleNewProject}
          className={cn(
            "focus-ring flex w-full items-center justify-center gap-2 rounded-[11px] bg-primary px-3 py-2.5 text-[13px] font-semibold text-white",
            "shadow-[0_1px_2px_rgba(19,24,41,0.12)] hover:bg-primary-strong transition-colors",
            creating && "opacity-80"
          )}
        >
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4 stroke-[2.5]" />}
          Yeni sarki klibi
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5 space-y-6">
        <div>
          <div className="section-label px-3 mb-2">Uretim</div>
          <div className="space-y-0.5">
            {NAV_MAIN.map((item) => {
              const active = isNavActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "focus-ring group relative flex items-center gap-3 rounded-[11px] px-3 py-2.5 text-[13px] font-medium transition-colors",
                    active
                      ? "bg-primary-soft text-primary font-semibold"
                      : "text-muted hover:text-foreground hover:bg-surface-3/80"
                  )}
                >
                  {active && (
                    <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary" />
                  )}
                  <span
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-[9px] transition-colors",
                      active ? "bg-surface text-primary shadow-sm" : "text-muted-2 group-hover:text-foreground"
                    )}
                  >
                    <Icon className="h-[15px] w-[15px]" />
                  </span>
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div>
          <div className="section-label px-3 mb-2">Altyapi</div>
          <div className="space-y-0.5">
            {NAV_SYSTEM.map((item) => {
              const active = isNavActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "focus-ring flex items-center gap-3 rounded-[11px] px-3 py-2.5 text-[13px] font-medium transition-colors",
                    active ? "bg-surface-3 text-foreground font-semibold" : "text-muted hover:text-foreground hover:bg-surface-3/80"
                  )}
                >
                  <Icon className="h-[15px] w-[15px] text-muted-2" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="mx-1 rounded-[14px] bg-surface-2 p-3.5">
          <div className="flex items-center gap-2 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-muted-2">
            <Clapperboard className="h-3.5 w-3.5" />
            Akis
          </div>
          <ol className="mt-2.5 space-y-2 text-[10.5px] text-muted leading-relaxed">
            <li>1 · MP3 + sozler (Suno.com&apos;dan indirdiginiz parca)</li>
            <li>2 · Sozler kliplere bolunur, Flow goruntu uretir</li>
            <li>3 · Render: video + yuklenen MP3 birlesir</li>
          </ol>
        </div>
      </nav>

      <div className="px-3 pb-3">
        <div className="rounded-[14px] border border-border bg-surface-2/90 p-3.5">
          <div className="flex items-center gap-2">
            <span className={cn("h-2.5 w-2.5 rounded-full", health.tone === "success" && "bg-success", health.tone === "warning" && "bg-warning", health.tone === "danger" && "bg-danger")} />
            <span className="text-[12px] font-semibold">{health.label}</span>
          </div>
          <div className="mt-1 text-[10.5px] text-muted">{health.detail}</div>
          {status && (
            <div className="mt-3 flex gap-3 border-t border-border pt-3 text-[10.5px] text-muted-2 tabular-nums">
              <span>
                <span className="font-semibold text-foreground">{status.projectCount}</span> proje
              </span>
              <span>
                <span className="font-semibold text-foreground">{status.completedClips}</span> klip
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
