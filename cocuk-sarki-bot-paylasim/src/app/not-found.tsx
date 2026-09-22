import Link from "next/link";
import { Compass, LayoutGrid, Music2 } from "lucide-react";
import { BRAND, NAV } from "@/lib/brand";

/** Bilinmeyen adres: kabuk icinde sakin, yonlendirici 404. */
export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="w-full max-w-lg rounded-[18px] border border-border bg-surface px-8 py-10 text-center card-shadow hairline-top">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-b from-primary-soft to-surface-3 text-primary ring-8 ring-surface-2">
          <Compass className="h-6 w-6" />
        </div>
        <div className="section-label">404</div>
        <h1 className="mt-1.5 text-[20px] font-semibold tracking-[-0.02em]">Sayfa bulunamadi</h1>
        <p className="mx-auto mt-2 max-w-sm text-[12.5px] text-muted leading-relaxed">
          Aradiginiz adres tasinmis veya kaldirilmis olabilir. {BRAND.name} uretim merkezine donebilirsiniz.
        </p>
        <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
          <Link
            href={NAV.home.href}
            className="focus-ring inline-flex h-9 items-center gap-2 rounded-[10px] brand-gradient px-4 text-sm font-medium text-white shadow-[0_1px_2px_rgba(67,56,202,0.28),0_6px_16px_-6px_rgba(79,70,229,0.5),inset_0_1px_0_rgba(255,255,255,0.22)]"
          >
            <LayoutGrid className="h-4 w-4" />
            Uretim Merkezi
          </Link>
          <Link
            href={NAV.projects.href}
            className="focus-ring inline-flex h-9 items-center gap-2 rounded-[10px] border border-border bg-surface px-4 text-sm font-medium text-foreground hover:bg-surface-2 hover:border-border-strong"
          >
            <Music2 className="h-4 w-4" />
            Projeler
          </Link>
        </div>
      </div>
    </div>
  );
}
