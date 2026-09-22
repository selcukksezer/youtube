"use client";

import * as React from "react";
import { toast } from "sonner";
import { CheckCircle2, Loader2, Sparkles, User } from "lucide-react";
import { mediaUrl, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CharacterData, EventData, ProjectData } from "@/components/project/types";

function parseSpecies(raw: string): string {
  if (!raw || raw === "{}") return "";
  try {
    const dna = JSON.parse(raw) as { species?: string };
    return dna.species?.trim() || "";
  } catch {
    return "";
  }
}

function isFlowReady(member: CharacterData): boolean {
  return Boolean(member.referenceImagePath && member.imageApproved);
}

export function namedCast(characters: CharacterData[]): CharacterData[] {
  return characters.filter((c) => c.name.trim());
}

export function SongCastPanel({
  project,
  reload,
  liveEvents,
  variant = "full",
}: {
  project: ProjectData;
  reload: () => Promise<unknown>;
  liveEvents?: EventData[];
  variant?: "bar" | "full";
}) {
  const cast = namedCast(project.characters);
  const missing = cast.filter((c) => !isFlowReady(c));
  const readyCount = cast.length - missing.length;
  const [busy, setBusy] = React.useState(false);

  const latestCharacterEvent = [...(liveEvents ?? [])]
    .reverse()
    .find((e) => e.step === "character");

  async function createViaFlow() {
    if (cast.length === 0) {
      toast.error("Adi gecen karakter yok. Once sozleri kliplere bolun (ustteki parca paneli).");
      return;
    }
    setBusy(true);
    try {
      const result = await postJson<{
        created: number;
        total: number;
        failed: string[];
        names: string[];
      }>(`/api/projects/${project.id}/song/create-cast-flow`);
      await reload();
      if (result.failed?.length) {
        toast.warning(
          `${result.created} karakter uretildi, ${result.failed.length} eksik otomatik tekrar denendi ama hâlâ duruyor. Butona bir kez daha basabilirsiniz — durmak zorunda degilsiniz.`
        );
      } else if (result.created > 0) {
        toast.success(`${result.created} karakter Flow'da olusturuldu (${result.total} kadro)`);
      } else {
        toast.success(`Tum ${result.total} karakter zaten Flow'da hazir`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Flow uretimi basarisiz");
    } finally {
      setBusy(false);
    }
  }

  const action = (
    <Button onClick={createViaFlow} loading={busy} disabled={busy || cast.length === 0 || missing.length === 0}>
      <Sparkles className="h-4 w-4" />
      {busy
        ? `Flow uretiyor… (${readyCount}/${cast.length})`
        : missing.length === 0 && cast.length > 0
          ? "Flow referanslari hazir"
          : `Topluca uret${missing.length ? ` (${missing.length})` : ""}`}
    </Button>
  );

  if (variant === "bar") {
    return (
      <Card className="mb-4">
        <CardContent className="py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <User className="h-4 w-4 text-primary shrink-0" />
              <span className="text-[13px] font-semibold">Karakterler</span>
              <Badge variant={missing.length === 0 && cast.length > 0 ? "success" : "warning"}>
                {readyCount}/{cast.length || 0} Flow&apos;da
              </Badge>
            </div>
            {cast.length === 0 ? (
              <p className="mt-1 text-[12px] text-muted">Sozlerde adi gecen kadro henuz yok.</p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {cast.map((member) => (
                  <Badge key={member.id} variant={isFlowReady(member) ? "success" : "warning"}>
                    {member.name}
                    {isFlowReady(member) ? " · hazir" : " · yok"}
                  </Badge>
                ))}
              </div>
            )}
            {busy && latestCharacterEvent?.message ? (
              <p className="mt-1 text-[11px] text-muted line-clamp-2">{latestCharacterEvent.message}</p>
            ) : null}
          </div>
          <div className="shrink-0">{action}</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="gap-3 sm:!flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" /> Adi gecen karakterler
            </CardTitle>
            <CardDescription>
              Sozlerde gecen kadro. Once Topluca uret (Flow&apos;a referans gorsel + @ad). Sonra otomasyon her klibe
              tum kadroyu referans olarak ekler — soyleyen once, digerleri ardindan.
            </CardDescription>
          </div>
          {action}
        </CardHeader>
      </Card>

      {cast.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="pt-6 text-sm text-muted">Henuz isimli karakter yok.</CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              Kadro — {cast.length} karakter
              <span className="text-muted font-normal text-sm ml-2">
                ({readyCount}/{cast.length} Flow&apos;da hazir)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {cast.map((member) => (
              <CastMemberCard key={member.id} member={member} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CastMemberCard({ member }: { member: CharacterData }) {
  const ready = isFlowReady(member);
  const species = parseSpecies(member.dnaCard);

  return (
    <div className="flex gap-3 rounded-lg border border-border p-3 bg-surface/50">
      <div className="h-20 w-20 shrink-0 rounded-md border border-border bg-muted/30 overflow-hidden flex items-center justify-center">
        {member.referenceImagePath ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={mediaUrl(member.referenceImagePath)} alt={member.name} className="h-full w-full object-cover" />
        ) : (
          <User className="h-7 w-7 text-muted-2" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">{member.name}</span>
          {member.role === "main" && <Badge variant="primary">Lead</Badge>}
          {ready ? (
            <Badge variant="success" className="gap-1">
              <CheckCircle2 className="h-3 w-3" /> Flow hazir
            </Badge>
          ) : (
            <Badge variant="warning" className="gap-1">
              <Loader2 className="h-3 w-3" /> Referans yok
            </Badge>
          )}
        </div>
        {species ? <p className="text-[11px] text-muted mt-1">{species}</p> : null}
        <p className="text-[10px] text-muted-2 mt-1 font-mono line-clamp-2">
          {member.flowCharacterReference || "Flow @referans henuz yok"}
        </p>
      </div>
    </div>
  );
}
