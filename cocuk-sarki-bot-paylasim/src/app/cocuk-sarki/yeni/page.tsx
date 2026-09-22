"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { createAndOpenSongStudio } from "@/lib/create-song-project";

/** Eski /yeni linki — dogrudan bos proje + studyo acar. */
export default function NewProjectRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    void createAndOpenSongStudio(router);
  }, [router]);

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-muted">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm">Yeni sarki klibi aciliyor...</p>
    </div>
  );
}
