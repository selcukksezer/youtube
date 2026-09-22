"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { postJson } from "@/lib/client-api";
import { projectProductionHref } from "@/lib/templates";

/** Yeni bos proje olusturup uretim sayfasina yonlendirir (MP3 + soz → klip). */
export async function createAndOpenSongStudio(router: ReturnType<typeof useRouter>): Promise<void> {
  try {
    const project = await postJson<{ id: string }>("/api/projects/quick");
    router.push(projectProductionHref({ id: project.id, templateType: "kids_song" }));
  } catch {
    toast.error("Proje olusturulamadi");
  }
}
