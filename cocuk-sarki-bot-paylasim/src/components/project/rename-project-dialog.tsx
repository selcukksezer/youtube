"use client";

import * as React from "react";
import { toast } from "sonner";
import { patchJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function RenameProjectDialog({
  open,
  projectId,
  currentName,
  onOpenChange,
  onRenamed,
}: {
  open: boolean;
  projectId: string;
  currentName: string;
  onOpenChange: (open: boolean) => void;
  onRenamed: (name: string) => void;
}) {
  const [name, setName] = React.useState(currentName);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (open) setName(currentName);
  }, [open, currentName]);

  async function save() {
    const next = name.trim();
    if (!next) {
      toast.error("Proje adi bos olamaz");
      return;
    }
    if (next.length > 120) {
      toast.error("Proje adi en fazla 120 karakter");
      return;
    }
    setSaving(true);
    try {
      await patchJson(`/api/projects/${projectId}`, { name: next });
      onRenamed(next);
      onOpenChange(false);
      toast.success("Proje adi guncellendi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Projeyi yeniden adlandir</DialogTitle>
          <DialogDescription>Liste ve uretim basliginda bu isim gorunur. Klasor adi degismez.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="project-rename">Proje adi</Label>
          <Input
            id="project-rename"
            value={name}
            maxLength={120}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void save();
              }
            }}
            placeholder="or. Kopuk Bulutu Sarkisi"
          />
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgec
          </Button>
          <Button loading={saving} onClick={() => void save()} disabled={!name.trim() || name.trim() === currentName}>
            Kaydet
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
