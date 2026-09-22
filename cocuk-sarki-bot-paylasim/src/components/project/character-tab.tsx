"use client";

import * as React from "react";
import { toast } from "sonner";
import { CheckCircle2, Clapperboard, ImagePlus, Save, Sparkles, Upload, User } from "lucide-react";
import { api, mediaUrl, patchJson, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import type { CharacterData, ProjectData } from "@/components/project/types";

const FIELDS: Array<{ key: keyof CharacterData; label: string; placeholder?: string }> = [
  { key: "name", label: "Karakter adi", placeholder: "Yildiz" },
  { key: "nationalityLook", label: "Milliyet / gorunum", placeholder: "Turkish" },
  { key: "hair", label: "Sac", placeholder: "short brown hair" },
  { key: "faceFeatures", label: "Yuz ozellikleri" },
  { key: "makeup", label: "Makyaj" },
  { key: "wardrobe", label: "Kiyafet / kostum" },
  { key: "bodyFraming", label: "Vucut kadraji" },
  { key: "gestureLevel", label: "Dans / jest seviyesi" },
  { key: "voiceCharacter", label: "Ses karakteri" },
  { key: "emotionTone", label: "Duygu tonu" },
  { key: "environment", label: "Ortam" },
  { key: "lighting", label: "Isik" },
  { key: "cameraAngle", label: "Kamera acisi" },
  { key: "lensLook", label: "Lens gorunumu" },
  { key: "background", label: "Arka plan" },
  { key: "flowCharacterReference", label: "Flow karakter referansi (@ad)", placeholder: "@Yildiz" },
];

export function CharacterTab({ project, reload }: { project: ProjectData; reload: () => Promise<ProjectData> }) {
  const [character, setCharacter] = React.useState<CharacterData | null>(
    project.characters.find((c) => c.role === "main") ?? null
  );
  const [form, setForm] = React.useState<Record<string, string | number>>({});
  const [busy, setBusy] = React.useState<string | null>(null);
  const [imagePromptDraft, setImagePromptDraft] = React.useState("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const loadCharacter = React.useCallback(async () => {
    const data = await api<{ main: CharacterData; sides: CharacterData[] }>(`/api/projects/${project.id}/character`, { silent: true });
    setCharacter(data.main);
    setImagePromptDraft(data.main.imagePrompt);
  }, [project.id]);

  React.useEffect(() => {
    loadCharacter().catch(() => {});
  }, [loadCharacter]);

  React.useEffect(() => {
    if (character) {
      const initial: Record<string, string | number> = {};
      for (const field of FIELDS) initial[field.key] = (character[field.key] as string) ?? "";
      initial.age = character.age;
      initial.negativePrompt = character.negativePrompt;
      setForm(initial);
    }
  }, [character]);

  if (!character) return null;

  const dirty =
    FIELDS.some((f) => form[f.key] !== undefined && form[f.key] !== (character[f.key] as string)) ||
    (form.age !== undefined && form.age !== character.age) ||
    (form.negativePrompt !== undefined && form.negativePrompt !== character.negativePrompt);

  async function save() {
    setBusy("save");
    try {
      const age = Number(form.age) || 20;
      if (age < 18) {
        toast.error("Karakter yasi 18'in altina ayarlanamaz");
        return;
      }
      await patchJson(`/api/projects/${project.id}/character`, { ...form, age });
      await loadCharacter();
      await reload();
      toast.success("Karakter profili ve kilidi guncellendi");
    } finally {
      setBusy(null);
    }
  }

  async function uploadImage(file: File) {
    setBusy("upload");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`/api/projects/${project.id}/upload-character`, { method: "POST", body: formData });
      const result = (await response.json()) as { ok: boolean; error?: string };
      if (!result.ok) throw new Error(result.error ?? "Yukleme basarisiz");
      await loadCharacter();
      toast.success("Referans gorseli yuklendi ve onaylandi");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Yukleme basarisiz");
    } finally {
      setBusy(null);
    }
  }

  async function generateImage(source: "openai" | "flow") {
    setBusy(source === "flow" ? "generate-flow" : "generate");
    try {
      await postJson(`/api/projects/${project.id}/generate-character`, {
        source,
        ...(imagePromptDraft.trim() ? { customPrompt: imagePromptDraft } : {}),
      });
      await loadCharacter();
      toast.success("Gorsel uretildi — onaylamadan otomasyon baslamaz");
    } finally {
      setBusy(null);
    }
  }

  async function approve() {
    setBusy("approve");
    try {
      await postJson(`/api/projects/${project.id}/character`);
      await loadCharacter();
      toast.success("Gorsel onaylandi");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {!project.useReference && (
        <Card className="border-warning/40 bg-warning-soft/40">
          <CardContent className="p-3 text-[12px] text-warning leading-relaxed">
            <span className="font-semibold">Referans kullanimi kapali.</span> Proje ayarlarindaki &quot;Referans kullan&quot;
            anahtari kapali oldugu icin buradaki gorsel Flow&apos;a yuklenmez.
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-3 text-[12px] text-muted leading-relaxed">
          <div className="text-[12.5px] font-semibold text-foreground">Sarki yildizi karakteri</div>
          <p className="mt-1">
            Ana karakter referansi tum kliplerde ayni yuz ve kostumu kilitler. Flow ile veya OpenAI ile gorsel uretin,
            onaylayin, ardindan otomasyonu baslatin.
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[340px_1fr] gap-4">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <CardTitle>Sarki Yildizi Referansi</CardTitle>
                {character.name && <Badge variant="primary">{character.name}</Badge>}
              </div>
              <CardDescription>
                3D Pixar tarzi sarki karakteri. On+arka turnaround sheet onerilir; tum kliplerde bu gorsel Flow&apos;a yuklenir.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {character.referenceImagePath ? (
                <div className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={mediaUrl(character.referenceImagePath)}
                    alt="Karakter referansi"
                    className="w-full rounded-[10px] border border-border object-cover"
                  />
                  <div className="absolute top-2 right-2">
                    {character.imageApproved ? (
                      <Badge variant="success">
                        <CheckCircle2 className="h-3 w-3" /> Onayli
                      </Badge>
                    ) : (
                      <Badge variant="warning">Onay bekliyor</Badge>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex h-44 items-center justify-center rounded-[10px] border border-dashed border-border-strong text-muted-2">
                  <User className="h-10 w-10" />
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.webp"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadImage(file);
                  e.target.value = "";
                }}
              />
              <div className="flex flex-col gap-2">
                <Button variant="secondary" onClick={() => fileInputRef.current?.click()} loading={busy === "upload"}>
                  <Upload className="h-4 w-4" /> Kendi Gorselimi Yukle
                </Button>
                <Button variant="outline" onClick={() => generateImage("flow")} loading={busy === "generate-flow"} disabled={busy !== null}>
                  <Clapperboard className="h-4 w-4" /> Flow ile Olustur (onerilen)
                </Button>
                <Button variant="outline" onClick={() => generateImage("openai")} loading={busy === "generate"} disabled={busy !== null}>
                  <ImagePlus className="h-4 w-4" /> OpenAI ile Olustur
                </Button>
                {character.referenceImagePath && !character.imageApproved && (
                  <Button variant="success" onClick={approve} loading={busy === "approve"}>
                    <CheckCircle2 className="h-4 w-4" /> Onayla
                  </Button>
                )}
              </div>
              <div>
                <Label>Gorsel uretim promptu</Label>
                <Textarea
                  className="text-[11px] font-mono min-h-[100px]"
                  value={imagePromptDraft}
                  onChange={(e) => setImagePromptDraft(e.target.value)}
                  placeholder="Bos birakirsaniz karakter tanimindan otomatik uretilir"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Karakter Kilidi</CardTitle>
              <CardDescription>Bu metinler her klipte aynen kullanilir</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-[11px] font-mono text-muted break-words">
              <div>
                <span className="text-primary">[GORUNUM]</span> {character.baseAppearancePrompt || "—"}
              </div>
              <div>
                <span className="text-primary">[KIYAFET]</span> {character.baseWardrobePrompt || "—"}
              </div>
              <div>
                <span className="text-primary">[ORTAM]</span> {character.baseEnvironmentPrompt || "—"}
              </div>
              <div>
                <span className="text-primary">[KAMERA]</span> {character.baseCameraPrompt || "—"}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Karakter Profili</CardTitle>
                <CardDescription>Degistirdikten sonra kaydedin; promptlar yenilenmelidir</CardDescription>
              </div>
              <Button onClick={save} loading={busy === "save"} disabled={!dirty}>
                <Save className="h-4 w-4" /> Kaydet
              </Button>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label>Yas (en az 18)</Label>
              <Input
                type="number"
                min={18}
                value={Number(form.age ?? character.age)}
                onChange={(e) => setForm((prev) => ({ ...prev, age: Number(e.target.value) }))}
              />
            </div>
            {FIELDS.map((field) => (
              <div key={field.key}>
                <Label>{field.label}</Label>
                <Input
                  value={String(form[field.key] ?? "")}
                  placeholder={field.placeholder}
                  onChange={(e) => setForm((prev) => ({ ...prev, [field.key]: e.target.value }))}
                />
              </div>
            ))}
            <div className="md:col-span-2">
              <Label>Negatif talimatlar</Label>
              <Textarea
                value={String(form.negativePrompt ?? "")}
                onChange={(e) => setForm((prev) => ({ ...prev, negativePrompt: e.target.value }))}
              />
            </div>
            {character.dnaCard && character.dnaCard !== "{}" && (
              <div className="md:col-span-2 rounded-[10px] border border-primary/30 bg-primary-soft/30 p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-primary mb-2">
                  <Sparkles className="h-3.5 w-3.5" /> DNA Karti
                </div>
                <pre className="text-[11px] text-muted whitespace-pre-wrap break-words font-mono">
                  {JSON.stringify(JSON.parse(character.dnaCard), null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
