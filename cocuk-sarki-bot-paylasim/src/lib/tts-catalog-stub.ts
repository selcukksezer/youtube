export type TtsProvider = "google" | "azure" | "elevenlabs" | "piper";

export const TTS_PROVIDER_INFO: Record<TtsProvider, { label: string; description: string }> = {
  google: { label: "Google", description: "" },
  azure: { label: "Azure", description: "" },
  elevenlabs: { label: "ElevenLabs", description: "" },
  piper: { label: "Piper", description: "" },
};
