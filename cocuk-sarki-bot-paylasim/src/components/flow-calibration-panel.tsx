"use client";

import * as React from "react";
import { toast } from "sonner";
import { Crosshair, MousePointerClick, RefreshCw, Trash2, Wand2 } from "lucide-react";
import { api, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface SelectorStateRow {
  key: string;
  description: string;
  required: boolean;
  strategy: string;
  value: string;
  roleName: string;
  candidateCount: number;
  fallbackCount: number;
  lastTestOk: boolean | null;
  lastTestAt: string | null;
  priority: number;
}

interface AutoCalibrateResponse {
  results: Array<{ key: string; found: boolean; saved: boolean; skipped?: boolean; priority?: number }>;
  pageUrl: string;
}

function priorityBadge(priority: number): { label: string; variant: "danger" | "warning" | "default" } {
  if (priority <= 0) return { label: "P0 kritik", variant: "danger" };
  if (priority === 1) return { label: "P1 ayar", variant: "warning" };
  if (priority === 2) return { label: "P2", variant: "default" };
  return { label: "P3", variant: "default" };
}

interface SelectorTestResponse {
  results: Array<{ key: string; found: boolean; required: boolean; matchedSource: string | null }>;
  pageUrl: string;
}

/** Flow Playwright secici kalibrasyonu — ayarlar ve sol menu sayfasi ortak. */
export function FlowCalibrationPanel() {
  const [rows, setRows] = React.useState<SelectorStateRow[] | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    const data = await api<SelectorStateRow[]>("/api/flow/selectors", { silent: true });
    setRows(data);
  }, []);

  React.useEffect(() => {
    reload().catch(() => setRows([]));
  }, [reload]);

  async function autoCalibrate() {
    setBusy("auto");
    try {
      const data = await postJson<AutoCalibrateResponse>("/api/flow/selectors/auto");
      const found = data.results.filter((r) => r.found).length;
      const saved = data.results.filter((r) => r.saved).length;
      const skipped = data.results.filter((r) => r.skipped).length;
      const p0miss = data.results.filter((r) => r.priority === 0 && !r.found).map((r) => r.key);
      if (p0miss.length > 0) {
        toast.warning(
          `Kritik eksik: ${p0miss.join(", ")}. Flow proje editoru (prompt cubugu) acik mi? ${found} bulundu, ${saved} kaydedildi.`
        );
      } else {
        toast.success(
          `Oto kalibrasyon: ${found} bulundu, ${saved} kaydedildi${skipped ? `, ${skipped} atlandi (ekranda olmasi beklenmez)` : ""}`
        );
      }
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Oto kalibrasyon basarisiz");
    } finally {
      setBusy(null);
    }
  }

  async function testAll() {
    setBusy("test");
    try {
      const data = await postJson<SelectorTestResponse>("/api/flow/selectors/test");
      const found = data.results.filter((r) => r.found).length;
      const requiredMissing = data.results.filter((r) => r.required && !r.found).length;
      if (requiredMissing > 0) toast.warning(`${found}/${data.results.length} bulundu — ${requiredMissing} zorunlu secici bu ekranda yok`);
      else toast.success(`${found}/${data.results.length} secici bulundu`);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Test basarisiz");
    } finally {
      setBusy(null);
    }
  }

  async function teach(key: string) {
    setBusy(`teach:${key}`);
    toast.info("Chrome'daki Flow penceresinde hedef ogeye 60 saniye icinde tiklayin…", { duration: 8000 });
    try {
      const result = await postJson<{ primary: { strategy: string; value: string; roleName: string } }>(
        "/api/flow/selectors/calibrate",
        { key }
      );
      toast.success(`Kaydedildi: ${key} → ${result.primary.strategy}${result.primary.roleName ? ` (${result.primary.roleName})` : ""}`);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Kalibrasyon basarisiz");
    } finally {
      setBusy(null);
    }
  }

  async function reset(key: string) {
    setBusy(`reset:${key}`);
    try {
      await postJson("/api/flow/selectors/calibrate", { key, reset: true });
      toast.success(`${key} sifirlandi — yerlesik yedekler kullanilacak`);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sifirlama basarisiz");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <Crosshair className="h-4 w-4 text-primary" />
              <CardTitle>Flow Secici Kalibrasyonu</CardTitle>
            </div>
            <CardDescription>
              Once <strong>P0</strong> (prompt + Generate) ve <strong>P1</strong> (cikti turu, sure, oran, model, ses)
              kalibre edilir — Generate&apos;e basilmaz. Oto kalibre, kayitli Flow proje editorune gider ve ayarlar
              panelini acip kapatir. P2/P3 (ilerleme, hata, karakter) ekranda yoksa atlanir; bunlar icin{" "}
              <strong>Tanit</strong> kullanin.
            </CardDescription>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button onClick={autoCalibrate} loading={busy === "auto"} disabled={busy !== null}>
              <Wand2 className="h-4 w-4" /> Oto kalibre et
            </Button>
            <Button variant="secondary" onClick={testAll} loading={busy === "test"} disabled={busy !== null}>
              <RefreshCw className="h-4 w-4" /> Tumunu test et
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {rows === null ? (
          <Skeleton className="h-40" />
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted">Secici listesi yuklenemedi.</p>
        ) : (
          <div className="divide-y divide-border rounded-[10px] border border-border overflow-hidden">
            {rows.map((row) => {
              const calibrated = Boolean(row.value.trim()) || row.candidateCount > 0;
              return (
                <div key={row.key} className="flex items-center gap-3 px-3 py-2 bg-surface/60">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[12.5px] font-medium">{row.description || row.key}</span>
                      <Badge variant={priorityBadge(row.priority).variant}>{priorityBadge(row.priority).label}</Badge>
                      {row.required && <Badge variant="warning">zorunlu</Badge>}
                      {calibrated ? (
                        <Badge variant="success">Tanitildi</Badge>
                      ) : row.fallbackCount > 0 ? (
                        <Badge>Yerlesik yedek ({row.fallbackCount})</Badge>
                      ) : (
                        <Badge variant="danger">Eksik</Badge>
                      )}
                      {row.lastTestOk !== null && (
                        <Badge variant={row.lastTestOk ? "success" : "danger"}>
                          {row.lastTestOk ? "Son test: bulundu" : "Son test: yok"}
                        </Badge>
                      )}
                    </div>
                    <div className="mt-0.5 text-[10.5px] text-muted-2 font-mono truncate">
                      {row.key}
                      {row.value ? ` · ${row.strategy}${row.roleName ? `(${row.roleName})` : `: ${row.value.slice(0, 60)}`}` : ""}
                    </div>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <Button size="sm" variant="outline" onClick={() => teach(row.key)} loading={busy === `teach:${row.key}`} disabled={busy !== null}>
                      <MousePointerClick className="h-3.5 w-3.5" /> Tanit
                    </Button>
                    {calibrated && (
                      <Button size="sm" variant="ghost" onClick={() => reset(row.key)} loading={busy === `reset:${row.key}`} disabled={busy !== null}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
