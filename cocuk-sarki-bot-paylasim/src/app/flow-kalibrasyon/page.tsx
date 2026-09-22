"use client";

import * as React from "react";
import { toast } from "sonner";
import { Chrome, Crosshair } from "lucide-react";
import { postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared";
import { FlowCalibrationPanel } from "@/components/flow-calibration-panel";
import { LiveEventLog } from "@/components/live-event-log";
import { NAV } from "@/lib/brand";

export default function FlowCalibrationPage() {
  const [opening, setOpening] = React.useState(false);

  async function openFlow() {
    setOpening(true);
    try {
      await postJson("/api/flow/open");
      toast.success("Flow acildi. Chrome penceresinde proje editorune gecin, sonra oto kalibre edin.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Flow acilamadi");
    } finally {
      setOpening(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Altyapi"
        title={NAV.flowCalibration.label}
        description="Flow arayuzundeki dugme ve kutulari tanitin. Kalibrasyon otomasyon isabetini artirir; canli gunluk son hatalari gosterir."
        actions={
          <Button variant="outline" onClick={openFlow} loading={opening}>
            <Chrome className="h-4 w-4" /> Flow'u ac
          </Button>
        }
      />

      <div className="space-y-4">
        <div className="rounded-[14px] border border-border bg-surface-2/80 px-4 py-3 text-[12.5px] text-muted leading-relaxed">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <Crosshair className="h-3.5 w-3.5 text-primary" />
            Nasil kullanilir
          </div>
          <ol className="mt-2 space-y-1 list-decimal pl-4">
            <li>Flow proje editoru acik olsun (prompt kutusu gorunsun).</li>
            <li>
              <strong>Oto kalibre et</strong> ile gorunen ogeleri kaydedin.
            </li>
            <li>
              Eksik kalan zorunlu ogeler icin <strong>Tanit</strong> deyip Chrome&apos;da hedefe tiklayin.
            </li>
          </ol>
        </div>

        <FlowCalibrationPanel />
        <LiveEventLog maxHeight="max-h-[420px]" />
      </div>
    </div>
  );
}
