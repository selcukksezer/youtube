import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { SystemStatusProvider } from "@/components/system-status-provider";
import { BRAND } from "@/lib/brand";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: BRAND.nameFull,
  description: BRAND.tagline,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={inter.variable}>
      <body className="min-h-screen">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-[10px] focus:bg-surface focus:px-4 focus:py-2 focus:text-[13px] focus:font-semibold focus:text-primary focus:elevated"
        >
          Icerige gec
        </a>
        <SystemStatusProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 min-w-0 flex flex-col">
              <Topbar />
              <main id="content" className="flex-1 min-w-0 px-6 py-7 lg:px-8">
                <div className="mx-auto max-w-[1380px] rise-in">{children}</div>
              </main>
            </div>
          </div>
        </SystemStatusProvider>
        <Toaster
          theme="light"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-foreground)",
              boxShadow: "0 8px 24px rgba(20, 28, 51, 0.12)",
            },
          }}
        />
      </body>
    </html>
  );
}
