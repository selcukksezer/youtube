"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** Sayfa basligi blogu. */
export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="mb-6 pb-5 border-b border-border flex items-start justify-between gap-4 flex-wrap">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-soft px-2.5 py-[3px]">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-primary">{eyebrow}</span>
          </div>
        )}
        <h1 className="text-[23px] font-semibold tracking-[-0.025em] leading-tight">{title}</h1>
        {description && <p className="mt-1.5 text-[13px] text-muted max-w-3xl leading-relaxed">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}

/**
 * Numarali form bolumu — uzun formlarda (or. Yeni Proje) gorsel ritim ve
 * "neredeyim" hissi verir.
 */
export function FormSection({
  step,
  title,
  description,
  children,
  action,
}: {
  step: number | string;
  title: string;
  description?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="rounded-[16px] border border-border bg-surface card-shadow hairline-top">
      <header className="flex items-start gap-3 border-b border-border px-5 py-4">
        <span className="mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary-soft text-[11px] font-semibold tabular-nums text-primary">
          {step}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-[14px] font-semibold tracking-[-0.01em] leading-snug">{title}</h2>
          {description && <p className="mt-0.5 text-[11.5px] text-muted leading-relaxed">{description}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      <div className="px-5 py-5">{children}</div>
    </section>
  );
}

/** Form alani + etiket + yardim metni / hata mesaji sarmalayicisi. */
export function Field({
  label,
  hint,
  error,
  required,
  htmlFor,
  className,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  htmlFor?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 flex items-center gap-1 text-[11.5px] font-semibold tracking-[0.005em] text-muted"
      >
        {label}
        {required && (
          <span className="text-danger" aria-hidden>
            *
          </span>
        )}
      </label>
      {children}
      {error ? (
        <p className="mt-1.5 text-[11px] font-medium text-danger leading-relaxed">{error}</p>
      ) : (
        hint && <p className="mt-1.5 text-[11px] text-muted-2 leading-relaxed">{hint}</p>
      )}
    </div>
  );
}

/** Bos durum karti. */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[16px] border border-dashed border-border-strong bg-surface px-8 py-16 text-center card-shadow">
      {icon && (
        <div className="mb-4 flex h-13 w-13 items-center justify-center rounded-[16px] bg-surface-3 text-muted">
          {icon}
        </div>
      )}
      <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>
      {description && <p className="mt-2 max-w-md text-[12.5px] text-muted leading-relaxed">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/** Proje durumu rozetleri. */
const PROJECT_STATUS: Record<string, { label: string; variant: "default" | "primary" | "success" | "warning" | "danger" | "info" }> = {
  draft: { label: "Taslak", variant: "default" },
  story_ready: { label: "Hikaye Hazir", variant: "info" },
  clips_ready: { label: "Klipler Hazir", variant: "info" },
  prompts_ready: { label: "Promptlar Hazir", variant: "primary" },
  automating: { label: "Otomasyon Calisiyor", variant: "warning" },
  clips_done: { label: "Klipler Tamamlandi", variant: "success" },
  rendering: { label: "Birlestiriliyor", variant: "warning" },
  completed: { label: "Tamamlandi", variant: "success" },
  render_failed: { label: "Birlestirme Hatasi", variant: "danger" },
  failed: { label: "Hata", variant: "danger" },
};

export function ProjectStatusBadge({ status }: { status: string }) {
  const config = PROJECT_STATUS[status] ?? { label: status, variant: "default" as const };
  return (
    <Badge variant={config.variant} dot>
      {config.label}
    </Badge>
  );
}

/** Klip durumu rozetleri (durum makinesi adimlari). */
const CLIP_STATUS: Record<string, { label: string; variant: "default" | "primary" | "success" | "warning" | "danger" | "info" }> = {
  draft: { label: "Taslak", variant: "default" },
  pending: { label: "Kuyrukta", variant: "default" },
  preparing: { label: "Hazirlaniyor", variant: "info" },
  opening_flow: { label: "Flow Aciliyor", variant: "info" },
  waiting_for_login: { label: "Giris Bekliyor", variant: "warning" },
  selecting_project: { label: "Proje Seciliyor", variant: "info" },
  uploading_reference: { label: "Referans Yukleniyor", variant: "info" },
  configuring_model: { label: "Model Ayarlaniyor", variant: "info" },
  entering_prompt: { label: "Prompt Yaziliyor", variant: "info" },
  generating: { label: "Uretiliyor", variant: "primary" },
  waiting_for_completion: { label: "Uretim Bekleniyor", variant: "primary" },
  downloading: { label: "Indiriliyor", variant: "primary" },
  validating_download: { label: "Dogrulaniyor", variant: "info" },
  extracting_last_frame: { label: "Son Kare Cikariliyor", variant: "info" },
  completed: { label: "Tamamlandi", variant: "success" },
  retrying: { label: "Yeniden Denenecek", variant: "warning" },
  paused: { label: "Duraklatildi", variant: "warning" },
  needs_manual_action: { label: "Elle Mudahale", variant: "danger" },
  failed: { label: "Basarisiz", variant: "danger" },
};

const ACTIVE_CLIP_STATES = new Set([
  "preparing",
  "opening_flow",
  "selecting_project",
  "uploading_reference",
  "configuring_model",
  "entering_prompt",
  "generating",
  "waiting_for_completion",
  "downloading",
  "validating_download",
  "extracting_last_frame",
]);

export function ClipStatusBadge({ status }: { status: string }) {
  const config = CLIP_STATUS[status] ?? { label: status, variant: "default" as const };
  return (
    <Badge variant={config.variant} dot pulse={ACTIVE_CLIP_STATES.has(status)}>
      {config.label}
    </Badge>
  );
}

/** Kucuk istatistik karti. */
export function StatCard({
  label,
  value,
  icon,
  tone = "default",
  hint,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  tone?: "default" | "success" | "danger" | "warning" | "primary";
  hint?: string;
}) {
  return (
    <div className="group rounded-[16px] border border-border bg-surface p-5 card-shadow hover:card-shadow-hover hover:-translate-y-0.5 transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="section-label">{label}</div>
          <div className="mt-2.5 text-[28px] font-semibold tabular-nums leading-none tracking-[-0.02em]">{value}</div>
          {hint && <div className="mt-2 text-[11px] text-muted-2 leading-relaxed">{hint}</div>}
        </div>
        {icon && (
          <span
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] border",
              tone === "default" && "border-border bg-surface-3 text-muted",
              tone === "primary" && "border-primary/20 bg-primary-soft text-primary",
              tone === "success" && "border-success/20 bg-success-soft text-success",
              tone === "danger" && "border-danger/20 bg-danger-soft text-danger",
              tone === "warning" && "border-warning/20 bg-warning-soft text-warning"
            )}
          >
            {icon}
          </span>
        )}
      </div>
    </div>
  );
}

/** Sistem durumu satiri (dashboard + kurulum). */
export function CheckRow({ ok, label, detail }: { ok: boolean | null; label: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-0 last:pb-0 first:pt-0">
      <span
        className={cn(
          "mt-1 inline-block h-2 w-2 rounded-full shrink-0 ring-4",
          ok === true && "bg-success ring-success/12",
          ok === false && "bg-danger ring-danger/12",
          ok === null && "bg-muted-2 ring-border/60"
        )}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[13px] font-medium">{label}</span>
          {ok === false && <span className="text-[10px] font-semibold text-danger shrink-0">EKSIK</span>}
        </div>
        <div className="text-[11.5px] text-muted-2 truncate mt-0.5" title={detail}>
          {detail}
        </div>
      </div>
    </div>
  );
}
