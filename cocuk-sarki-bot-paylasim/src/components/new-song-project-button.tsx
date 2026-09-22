"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createAndOpenSongStudio } from "@/lib/create-song-project";

export function NewSongProjectButton({
  size = "sm",
  variant = "default" as const,
  className,
  label = "Yeni sarki klibi",
}: {
  size?: "sm" | "default";
  variant?: "default" | "outline";
  className?: string;
  label?: string;
}) {
  const router = useRouter();
  const [creating, setCreating] = React.useState(false);

  return (
    <Button
      size={size}
      variant={variant}
      className={className}
      disabled={creating}
      onClick={async () => {
        setCreating(true);
        try {
          await createAndOpenSongStudio(router);
        } finally {
          setCreating(false);
        }
      }}
    >
      {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      {label}
    </Button>
  );
}
