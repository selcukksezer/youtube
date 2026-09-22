/** Uygulama markasi — tek kaynak. */
export const BRAND = {
  name: "Kids Song MV",
  nameFull: "Kids Song MV Studio",
  tagline: "Profesyonel cocuk sarki klibi uretim platformu",
  pipeline: "Suno · Flow · FFmpeg",
  copyright: "Kids Song MV Studio",
} as const;

export const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Master parca",
    detail: "Suno.com'dan indirdiginiz MP3 + sozler. Bu parca tum klibin ses omurgasi.",
    icon: "music",
  },
  {
    step: "02",
    title: "Soz & klip eslestirme",
    detail: "Sozler sahnelere bolunur, sure ve tempo ile hizalanir.",
    icon: "lyrics",
  },
  {
    step: "03",
    title: "Karakter & Flow",
    detail: "3D karakter referansi, lip-sync goruntu klipleri — ses Flow'da kapali.",
    icon: "character",
  },
  {
    step: "04",
    title: "Render & yayin",
    detail: "Videolar + yuklenen MP3 birlestirilir; thumbnail ve metadata hazirlanir.",
    icon: "render",
  },
] as const;

export const NAV = {
  home: { href: "/", label: "Uretim Merkezi" },
  projects: { href: "/cocuk-sarki", label: "Projeler" },
  newProject: { href: "/cocuk-sarki", label: "Yeni proje" },
  setup: { href: "/setup", label: "Kurulum" },
  flowCalibration: { href: "/flow-kalibrasyon", label: "Flow Kalibrasyonu" },
  settings: { href: "/settings", label: "Ayarlar" },
} as const;
