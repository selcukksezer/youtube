"use client";

import * as React from "react";
import { toast } from "sonner";
import { KeyRound, Music2, Save, ShieldCheck, Trash2 } from "lucide-react";
import { api, del, postJson, putJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared";
import { FlowCalibrationPanel } from "@/components/flow-calibration-panel";
import { BRAND } from "@/lib/brand";

interface SettingsData {
  openaiModel: string;
  flowUrl: string;
  chromeProfileDir: string;
  downloadDir: string;
  ffmpegPath: string;
  ffprobePath: string;
  maxRetries: number;
  waitBetweenGenerationsMs: number;
  generationTimeoutMs: number;
  pollIntervalMs: number;
  defaultFlowModel: string;
  defaultClipSeconds: number;
  defaultAspectRatio: string;
  headless: boolean;
  slowMoMs: number;
  maxParallelProjects: number;
  wpmSlow: number;
  wpmNormal: number;
  wpmFast: number;
  modelSupportMatrix: string;
  sunoApiBaseUrl: string;
  sunoDefaultModel: string;
}

interface KeyInfo {
  present: boolean;
  source: string;
  masked: string;
  storageMode: string;
}

interface SunoKeyInfo {
  present: boolean;
  baseUrl: string;
  defaultModel: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = React.useState<SettingsData | null>(null);
  const [keyInfo, setKeyInfo] = React.useState<KeyInfo | null>(null);
  const [apiKey, setApiKey] = React.useState("");
  const [storageMode, setStorageMode] = React.useState<"memory" | "encrypted">("memory");
  const [saving, setSaving] = React.useState(false);
  const [savingKey, setSavingKey] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const [sunoKey, setSunoKey] = React.useState<SunoKeyInfo | null>(null);
  const [sunoApiKey, setSunoApiKey] = React.useState("");

  React.useEffect(() => {
    api<{ settings: SettingsData; openaiKey: KeyInfo; sunoKey: SunoKeyInfo }>("/api/settings").then((data) => {
      setSettings(data.settings);
      setKeyInfo(data.openaiKey);
      setSunoKey(data.sunoKey);
      setStorageMode((data.openaiKey.storageMode as "memory" | "encrypted") ?? "memory");
    });
  }, []);

  function update<K extends keyof SettingsData>(key: K, value: SettingsData[K]) {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
    setDirty(true);
  }

  async function saveSettings() {
    if (!settings) return;
    setSaving(true);
    try {
      try {
        JSON.parse(settings.modelSupportMatrix || "{}");
      } catch {
        toast.error("Model destek matrisi gecerli JSON degil");
        return;
      }
      const payload: Record<string, unknown> = { ...settings };
      if (sunoApiKey.trim()) payload.sunoApiKey = sunoApiKey.trim();

      const result = await putJson<{ settings: SettingsData; sunoKey: SunoKeyInfo }>("/api/settings", payload);
      setSunoKey(result.sunoKey);
      setSunoApiKey("");
      setDirty(false);
      toast.success("Ayarlar kaydedildi");
    } finally {
      setSaving(false);
    }
  }

  async function clearSunoKey() {
    const result = await putJson<{ sunoKey: SunoKeyInfo }>("/api/settings", { sunoApiKey: "" });
    setSunoKey(result.sunoKey);
    toast.success("Suno anahtari silindi");
  }

  async function saveKey() {
    if (!apiKey.trim()) {
      toast.error("API anahtari girin");
      return;
    }
    setSavingKey(true);
    try {
      const info = await postJson<KeyInfo>("/api/settings/openai", { apiKey: apiKey.trim(), storageMode });
      setKeyInfo(info);
      setApiKey("");
      toast.success(storageMode === "encrypted" ? "Anahtar sifrelenerek kaydedildi" : "Anahtar bu oturum icin bellekte tutuluyor");
    } finally {
      setSavingKey(false);
    }
  }

  async function clearKey() {
    const info = await del<KeyInfo>("/api/settings/openai");
    setKeyInfo(info);
    toast.success("Anahtar silindi");
  }

  if (!settings) {
    return (
      <div>
        <PageHeader title="Ayarlar" />
        <div className="space-y-4">
          <Skeleton className="h-48" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="pb-16">
      <PageHeader
        eyebrow={BRAND.name}
        title="Ayarlar"
        description="OpenAI, Suno, Flow, Playwright ve FFmpeg yapilandirmasi"
        actions={
          <Button onClick={saveSettings} loading={saving} disabled={!dirty}>
            <Save className="h-4 w-4" /> Kaydet
          </Button>
        }
      />

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-primary" />
              <CardTitle>OpenAI API Anahtari</CardTitle>
            </div>
            <CardDescription>
              Anahtar istemciye asla gonderilmez. Varsayilan olarak yalnizca bu oturumda bellekte tutulur; isterseniz AES-256-GCM ile
              sifrelenerek yerel veritabanina kaydedilir.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              {keyInfo?.present ? (
                <>
                  <Badge variant="success">
                    <ShieldCheck className="h-3 w-3" /> Anahtar ayarli: {keyInfo.masked}
                  </Badge>
                  <Badge>
                    Kaynak: {keyInfo.source === "sifreli-db" ? "Sifreli veritabani" : keyInfo.source === "bellek" ? "Bellek (oturum)" : keyInfo.source === "env" ? ".env dosyasi" : keyInfo.source}
                  </Badge>
                  <Button variant="danger" size="sm" onClick={clearKey}>
                    <Trash2 className="h-3.5 w-3.5" /> Anahtari Sil
                  </Button>
                </>
              ) : (
                <Badge variant="danger">Anahtar ayarlanmamis</Badge>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_220px_auto] gap-3 items-end">
              <div>
                <Label htmlFor="apiKey">Yeni anahtar</Label>
                <Input id="apiKey" type="password" placeholder="sk-..." value={apiKey} onChange={(e) => setApiKey(e.target.value)} autoComplete="off" />
              </div>
              <div>
                <Label>Saklama modu</Label>
                <Select value={storageMode} onValueChange={(v) => setStorageMode(v as "memory" | "encrypted")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="memory">Yalnizca bellekte (oturum)</SelectItem>
                    <SelectItem value="encrypted">Sifreli sakla (AES-256-GCM)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={saveKey} loading={savingKey}>
                Anahtari Kaydet
              </Button>
            </div>
            <div>
              <Label htmlFor="openaiModel">Varsayilan OpenAI modeli</Label>
              <Input
                id="openaiModel"
                className="max-w-xs"
                value={settings.openaiModel}
                onChange={(e) => update("openaiModel", e.target.value)}
                placeholder="gpt-5"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Music2 className="h-4 w-4 text-primary" />
              <CardTitle>Suno API — Master Parca</CardTitle>
            </div>
            <CardDescription>
              Ucretli Suno saglayicisi (kie.ai, sunoapi.org vb.) ile master parca uretimi. Anahtar sifreli saklanir; istemciye geri gelmez.
              Alternatif: Stüdyo&apos;dan Suno.com&apos;dan indirilen MP3 yukleyebilirsiniz.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              {sunoKey?.present ? (
                <>
                  <Badge variant="success">
                    <ShieldCheck className="h-3 w-3" /> Suno anahtari ayarli
                  </Badge>
                  <Badge>{sunoKey.baseUrl}</Badge>
                  <Badge variant="info">Model: {sunoKey.defaultModel}</Badge>
                  <Button variant="danger" size="sm" onClick={clearSunoKey}>
                    <Trash2 className="h-3.5 w-3.5" /> Anahtari Sil
                  </Button>
                </>
              ) : (
                <Badge variant="danger">Suno anahtari ayarlanmamis — yalnizca manuel MP3 yukleme kullanilabilir</Badge>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Suno API anahtari</Label>
                <Input
                  type="password"
                  value={sunoApiKey}
                  placeholder={sunoKey?.present ? "Kayitli — degistirmek icin yeni anahtar yazin" : "Saglayici API key"}
                  onChange={(e) => {
                    setSunoApiKey(e.target.value);
                    setDirty(true);
                  }}
                />
              </div>
              <div>
                <Label>API base URL</Label>
                <Input
                  value={settings.sunoApiBaseUrl}
                  onChange={(e) => update("sunoApiBaseUrl", e.target.value)}
                  placeholder="https://api.kie.ai"
                />
              </div>
              <div>
                <Label>Varsayilan model</Label>
                <Input
                  value={settings.sunoDefaultModel}
                  onChange={(e) => update("sunoDefaultModel", e.target.value)}
                  placeholder="V4_5"
                />
              </div>
            </div>
            <p className="text-[11px] text-muted leading-relaxed">
              Anahtar ve URL degisikliklerini kaydetmek icin ustteki <strong>Kaydet</strong> dugmesine basin.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Google Flow ve Playwright</CardTitle>
            <CardDescription>
              Google sifreniz hicbir yerde saklanmaz. Ilk calistirmada acilan Chrome penceresinde hesabiniza bir kez elle giris yaparsiniz;
              oturum profil klasorunde saklanir.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <Label htmlFor="flowUrl">Google Flow URL</Label>
              <Input id="flowUrl" value={settings.flowUrl} onChange={(e) => update("flowUrl", e.target.value)} />
              <p className="text-[10.5px] text-muted-2 mt-1 leading-relaxed">
                Onerilen: dogrudan PROJE adresinizi yazin (or. .../tools/flow/project/XXXX). Ana sayfa adresinde prompt kutusu bulunmadigi
                icin otomasyon her seferinde projeyi elle acmanizi bekler.
              </p>
            </div>
            <div>
              <Label htmlFor="chromeProfileDir">Chrome profil klasoru</Label>
              <Input id="chromeProfileDir" value={settings.chromeProfileDir} onChange={(e) => update("chromeProfileDir", e.target.value)} />
            </div>
            <div>
              <Label htmlFor="downloadDir">Indirme klasoru</Label>
              <Input id="downloadDir" value={settings.downloadDir} onChange={(e) => update("downloadDir", e.target.value)} />
            </div>
            <div className="flex items-center justify-between rounded-[10px] border border-border bg-surface-2 px-4 py-3">
              <div>
                <div className="text-[13px] font-medium">Headless mod</div>
                <div className="text-[11px] text-muted">Ilk surumde kapali onerilir (tarayiciyi gorursunuz)</div>
              </div>
              <Switch checked={settings.headless} onCheckedChange={(v) => update("headless", v)} />
            </div>
            <div>
              <Label htmlFor="slowMo">SlowMo (ms)</Label>
              <Input id="slowMo" type="number" value={settings.slowMoMs} onChange={(e) => update("slowMoMs", Number(e.target.value))} />
            </div>
            <div>
              <Label htmlFor="maxParallel">Paralel proje sayisi</Label>
              <Input
                id="maxParallel"
                type="number"
                min={1}
                max={6}
                value={settings.maxParallelProjects}
                onChange={(e) => update("maxParallelProjects", Number(e.target.value))}
              />
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                Ayni anda kac projenin otomasyonu calisabilir. Her proje ayni Chrome penceresinde KENDI sekmesinde
                calisir (tek Google oturumu). Her projenin &quot;Flow proje linki&quot; dolu olmalidir; aksi halde
                sekmeler ayni Flow projesine dusebilir. Yuksek deger makineyi ve Google tarafindaki uretim kotasini
                zorlar — 2-4 arasi onerilir.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Otomasyon Zamanlamalari</CardTitle>
            <CardDescription>Uretim bekleme sureleri ve yeniden deneme davranisi</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <Label>Maks. yeniden deneme</Label>
              <Input type="number" value={settings.maxRetries} onChange={(e) => update("maxRetries", Number(e.target.value))} />
            </div>
            <div>
              <Label>Uretimler arasi bekleme (ms)</Label>
              <Input
                type="number"
                value={settings.waitBetweenGenerationsMs}
                onChange={(e) => update("waitBetweenGenerationsMs", Number(e.target.value))}
              />
            </div>
            <div>
              <Label>Uretim zaman asimi (ms)</Label>
              <Input type="number" value={settings.generationTimeoutMs} onChange={(e) => update("generationTimeoutMs", Number(e.target.value))} />
            </div>
            <div>
              <Label>Kontrol araligi (ms)</Label>
              <Input type="number" value={settings.pollIntervalMs} onChange={(e) => update("pollIntervalMs", Number(e.target.value))} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Varsayilan Uretim Ayarlari</CardTitle>
            <CardDescription>Yeni projelerde kullanilacak Flow varsayilanlari ve konusma hizlari</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <Label>Varsayilan Flow modeli</Label>
              <Input value={settings.defaultFlowModel} onChange={(e) => update("defaultFlowModel", e.target.value)} />
            </div>
            <div>
              <Label>Varsayilan klip suresi (sn)</Label>
              <Select value={String(settings.defaultClipSeconds)} onValueChange={(v) => update("defaultClipSeconds", Number(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[4, 6, 8, 10].map((s) => (
                    <SelectItem key={s} value={String(s)}>
                      {s} saniye
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Varsayilan en-boy orani</Label>
              <Select value={settings.defaultAspectRatio} onValueChange={(v) => update("defaultAspectRatio", v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="16:9">16:9 (yatay)</SelectItem>
                  <SelectItem value="9:16">9:16 (dikey)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Yavas konusma (kelime/dk)</Label>
              <Input type="number" value={settings.wpmSlow} onChange={(e) => update("wpmSlow", Number(e.target.value))} />
            </div>
            <div>
              <Label>Normal konusma (kelime/dk)</Label>
              <Input type="number" value={settings.wpmNormal} onChange={(e) => update("wpmNormal", Number(e.target.value))} />
            </div>
            <div>
              <Label>Hizli konusma (kelime/dk)</Label>
              <Input type="number" value={settings.wpmFast} onChange={(e) => update("wpmFast", Number(e.target.value))} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>FFmpeg</CardTitle>
            <CardDescription>PATH'te ise yalnizca "ffmpeg" / "ffprobe" yazmak yeterlidir</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>FFmpeg yolu</Label>
              <Input value={settings.ffmpegPath} onChange={(e) => update("ffmpegPath", e.target.value)} />
            </div>
            <div>
              <Label>ffprobe yolu</Label>
              <Input value={settings.ffprobePath} onChange={(e) => update("ffprobePath", e.target.value)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model Destek Matrisi</CardTitle>
            <CardDescription>
              Hangi Flow modelinin hangi sure/oran/ozellikleri destekledigi. Otomasyon baslamadan once bu matrisle dogrulama yapilir.
              JSON bicimi: {"{"}"Model Adi": {"{"}"durations": [4,6,8], "aspectRatios": ["16:9","9:16"], "supportsReference": true,
              "supportsAudio": true, "supportsStartFrame": true{"}"}{"}"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              className="font-mono text-xs min-h-[180px]"
              value={settings.modelSupportMatrix}
              onChange={(e) => update("modelSupportMatrix", e.target.value)}
              spellCheck={false}
            />
          </CardContent>
        </Card>

        <FlowCalibrationPanel />
      </div>

      {dirty && (
        <div className="fixed bottom-6 right-6 z-40">
          <Button onClick={saveSettings} loading={saving} size="lg" className="shadow-2xl">
            <Save className="h-4 w-4" /> Degisiklikleri Kaydet
          </Button>
        </div>
      )}
    </div>
  );
}
