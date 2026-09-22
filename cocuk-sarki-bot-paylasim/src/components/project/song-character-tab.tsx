"use client";

import * as React from "react";
import { toast } from "sonner";
import { Music2, User, Wand2 } from "lucide-react";
import { postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectData } from "@/components/project/types";
import { namedCast, SongCastPanel } from "@/components/project/song-cast-panel";

export function SongCharacterTab({ project, reload }: { project: ProjectData; reload: () => Promise<unknown> }) {
  const [busy, setBusy] = React.useState(false);
  const [rationale, setRationale] = React.useState<string | null>(null);
  const cast = namedCast(project.characters);

  async function planCast() {
    setBusy(true);
    try {
      const result = await postJson<{ castCount: number; rationale: string; names: string[] }>(
        `/api/projects/${project.id}/song/analyze-cast`
      );
      setRationale(result.rationale);
      await reload();
      toast.success(`${result.castCount} sabit karakter planlandi: ${result.names.join(", ")}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Karakter plani olusturulamadi");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" /> Sarki kadrosu
          </CardTitle>
          <CardDescription>
            Sozlerde gecen karakterler asagida listelenir. Topluca uret, Flow&apos;u acar ve hepsini sirayla karakter
            olarak ekler.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button onClick={planCast} loading={busy} disabled={busy}>
            <Wand2 className="h-4 w-4" />
            {cast.length > 0 ? "Kadro planini yenile" : "Sarki icin sabit karakter uret"}
          </Button>
        </CardContent>
      </Card>

      {cast.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="pt-6 text-sm text-muted flex items-start gap-3">
            <Music2 className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-foreground">Henuz isimli karakter yok</p>
              <p className="mt-1 text-[13px]">
                Once uretim sayfasindaki parca panelinden sozleri kliplere bolun; kadro sozlerden otomatik cikar.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {rationale && (
        <p className="text-[12px] text-muted leading-relaxed px-1">
          <span className="font-medium text-foreground">AI gerekcesi: </span>
          {rationale}
        </p>
      )}

      <SongCastPanel project={project} reload={reload} variant="full" />
    </div>
  );
}
