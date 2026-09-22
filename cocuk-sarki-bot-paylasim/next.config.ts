import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["playwright", "playwright-core", "@prisma/client", "prisma", "pino"],
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Proje klasoru altindaki medya dosyalarini (video/gorsel) API uzerinden akitiyoruz;
  // buyuk dosya yanitlari icin govde siniri kaldirilmali.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' http://127.0.0.1:8000 http://localhost:8000",
          },
        ],
      },
    ];
  },
  async redirects() {
    return [
      { source: "/projects", destination: "/cocuk-sarki", permanent: true },
      { source: "/projects/:path*", destination: "/cocuk-sarki/:path*", permanent: true },
      { source: "/anlatici", destination: "/cocuk-sarki", permanent: true },
      { source: "/anlatici/:path*", destination: "/cocuk-sarki", permanent: true },
      { source: "/calibration", destination: "/setup", permanent: true },
    ];
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "20mb",
    },
  },
  /**
   * Varsayilan (25 sn / 2 sayfa) dev modunda bu uygulamadaki onlarca sayfa+API
   * rotasi icin COK dusuk: her sekme gecisi / paralel istek grubu, az kullanilan
   * bir rotayi bellekten atip sonraki istekte sifirdan derletiyordu (saniyeler
   * suren "Compiling..." gecisleri = "sayfa gecisleri cok yavas" hissi).
   * Rotalar bir kez derlenince uzun sure sicak tutulur, tekrar derleme olmaz.
   */
  onDemandEntries: {
    maxInactiveAge: 60 * 60 * 1000,
    pagesBufferLength: 40,
  },
  /**
   * Dev modunda proje olusturma / otomasyon dosya yazimi Next'in file watcher'ini
   * tetikleyip sunucuyu yeniden baslatiyordu (projects/, sqlite, logs, chrome profili).
   * NOT: Bu yuzden Turbopack'e gecilmedi — Turbopack'te bu yok sayma secenegi yok,
   * otomasyon calisirken surekli dosya yazan bu proje icin webpack + bu liste kaliyor.
   */
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        ...config.watchOptions,
        ignored: [
          "**/projects/**",
          "**/chrome-profile/**",
          "**/logs/**",
          "**/*.db",
          "**/*.db-journal",
          "**/*.db-wal",
          "**/*.db-shm",
          "**/node_modules/**",
          "**/.git/**",
        ],
      };
    }
    return config;
  },
};

export default nextConfig;
