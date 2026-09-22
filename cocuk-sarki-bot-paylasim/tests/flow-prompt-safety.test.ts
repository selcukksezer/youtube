import { describe, expect, it } from "vitest";
import {
  compactPromptForFlow,
  ensureNoOnscreenTextLock,
  FLOW_NO_ONSCREEN_TEXT_HEAD,
  FLOW_NO_ONSCREEN_TEXT_TAIL,
  FLOW_PROMPT_MAX,
  finalizeFlowPrompt,
  stampNoOnscreenTextLock,
} from "@/lib/flow-prompt-compact";
import {
  ensureAnimatedCastLock,
  sanitizeKidsPromptForFlow,
} from "@/lib/flow-prompt-safety";

describe("Flow yayin-guvenli prompt süzgeci", () => {
  it("toddler / kiss / yüze dokun dilini mascot diline cevirir", () => {
    const raw = [
      "Not a toddler voice. Readable for toddlers.",
      "YouTube-kids music video, kid-safe, kid-eye height.",
      "She touches her nose, foam kiss at kiss, skin texture visible.",
      "Do not age-swap. Hip sway. Children's backing track.",
    ].join(" ");
    const clean = sanitizeKidsPromptForFlow(raw);
    expect(clean).not.toMatch(/toddler/i);
    expect(clean).not.toMatch(/\bkiss/i);
    expect(clean).not.toMatch(/touches her nose/i);
    expect(clean).not.toMatch(/age-swap/i);
    expect(clean).not.toMatch(/hip sway/i);
    expect(clean).not.toMatch(/kid-safe/i);
    expect(clean).toMatch(/mascot singing voice|points to her own nose|foam heart bubble|broadcast-safe/i);
  });

  it("tirnakli sozlerdeki opucuk / kiss dilini de temizler", () => {
    const raw = `Director note: foam kiss. Lyrics: "Fokur fokur, köpükle öpücük — hadi!"`;
    const clean = sanitizeKidsPromptForFlow(raw);
    expect(clean).toContain('"Fokur fokur, köpükle kalp — hadi!"');
    expect(clean).toContain("foam heart bubble");
    expect(clean).not.toContain("foam kiss");
    expect(clean).not.toMatch(/öpücük|kiss/i);
  });

  it("muzikal minor key ifadesini bozmaz", () => {
    const clean = sanitizeKidsPromptForFlow("Exactly 118 BPM, in A minor, bright mood.");
    expect(clean).toContain("A minor");
  });

  it("den1 tarzi kirli yonetmen metnini Flow'a gitmeden temizler", () => {
    const raw = [
      "3D CGI kids animation, Feature-film kids animation, kid-safe, age-safe.",
      "true lip-sync, accurate lip-sync, Mouth shapes match every spoken syllable.",
      "sweat/skin sheen, skin/ears/fur, fur/skin pattern, photographic skin texture.",
      "Photoreal humans are forbidden. Do not age-swap.",
      "kid‑choir, YouTube kids, patio kids' silhouettes, hip sway.",
      "She touches her nose. blowing a gentle foamy kiss near Kokona's cheek.",
    ].join(" ");
    const clean = sanitizeKidsPromptForFlow(raw);
    expect(clean).not.toMatch(/toddler|kiss|öpücük|lip-sync|age-swap|kid-safe|YouTube kids|hip sway/i);
    expect(clean).not.toMatch(/\bskins?\b/i);
    expect(clean).not.toMatch(/\bkids\b/i);
    expect(clean).not.toMatch(/photoreal humans/i);
    expect(clean).toMatch(/syllable-sync|foam heart|points to her own nose|broadcast-safe|surface/i);
    expect(sanitizeKidsPromptForFlow("forming kiss-heart; the kiss; kiss heart")).not.toMatch(/kiss/i);
    expect(sanitizeKidsPromptForFlow("booping her nose, fingertip on the nose")).not.toMatch(/boop|fingertip/i);
    const body = sanitizeKidsPromptForFlow(
      "Tiny steam sprite. Petite and buoyant; big head (1:2) with wispy hair; head 1:2 body. cuddly adult voice, family-friendly, never suddenly younger/older."
    );
    expect(body).not.toMatch(/petite|big head|1:2|cuddly|family-friendly|younger\/older|Tiny steam sprite/i);
    expect(body).toMatch(/Adult cartoon steam-sprite barista|adult-mascot|warm adult mascot voice/i);
  });

  it("CAST LOCK ekler ve @referansi korur", () => {
    const locked = ensureAnimatedCastLock("@Kokona Kopuk\n\n[SHOT] dance");
    expect(locked.startsWith("@Kokona Kopuk")).toBe(true);
    expect(locked).toContain("[CAST LOCK — ANIMATED MASCOT]");
    expect(locked).toMatch(/cartoon mascot/i);
    expect(locked).not.toMatch(/\bchild\b|\bminor\b|\btoddler\b/i);
  });

  it("chalkboard menu yazisini harfsiz dekoratif tahtaya cevirir", () => {
    const clean = sanitizeKidsPromptForFlow("Background: wood shelves, a chalkboard menu, sunlit window.");
    expect(clean).toContain("blank chalkboard with decorative swirls and no letters");
    expect(clean).not.toMatch(/chalkboard menu/i);
  });
});

describe("Flow prompt kisaltmasi yazi yasagini dusurmez", () => {
  it("uzun promptta bas ve son kilitleri korur, diyalogu atmaz", () => {
    const huge = [
      "[STYLE] " + "pixar look ".repeat(400),
      "[SHOT] " + "cafe dance ".repeat(400),
      "[SCENE CONTINUITY] same cafe, next seconds.",
      "[AUDIO] The character SINGS these original lyrics in Turkish.",
      'SINGS lyrics in Turkish: "Ayak tap tap, burun tık tık, el şap şap!"',
      "[ON-SCREEN TEXT] HARD BAN — NO TEXT IN FRAME",
      "[RESTRICTIONS] no horror",
      "[FINAL HARD LOCK — ON-SCREEN TEXT] old lock",
    ].join("\n\n");
    const { text, truncated } = compactPromptForFlow(huge, "Turkish", 2000);
    expect(truncated).toBe(true);
    expect(text.length).toBeLessThanOrEqual(2000);
    expect(text).toContain(FLOW_NO_ONSCREEN_TEXT_HEAD);
    expect(text.endsWith(FLOW_NO_ONSCREEN_TEXT_TAIL) || text.includes(FLOW_NO_ONSCREEN_TEXT_TAIL)).toBe(true);
    expect(text).toContain("Ayak tap tap");
    expect(text).toMatch(/\[SPEECH LANGUAGE LOCK/);
  });

  it("kilit yoksa kisa prompta da bas+son yasak ekler", () => {
    const locked = ensureNoOnscreenTextLock("[SHOT] dance\n\n[AUDIO] sings");
    expect(locked.startsWith(FLOW_NO_ONSCREEN_TEXT_HEAD)).toBe(true);
    expect(locked).toContain(FLOW_NO_ONSCREEN_TEXT_TAIL);
    expect(locked).toContain("[SABIT KURAL — ALTYAZI YOK]");
    expect(locked).toContain("[SABIT KURAL SONU — ALTYAZI YOK]");
  });

  it("ozel sablon damgasiz olsa bile ayni kilit yapisir", () => {
    const a = ensureNoOnscreenTextLock("clip 1 custom template only");
    const b = ensureNoOnscreenTextLock("clip 1000 totally different body");
    expect(a).toContain(FLOW_NO_ONSCREEN_TEXT_HEAD);
    expect(b).toContain(FLOW_NO_ONSCREEN_TEXT_HEAD);
    expect(a.slice(0, FLOW_NO_ONSCREEN_TEXT_HEAD.length)).toBe(b.slice(0, FLOW_NO_ONSCREEN_TEXT_HEAD.length));
  });

  it("ortadaki kuyruk damgasi AUDIO/diyalogu yemez", () => {
    const quote = "Cam buğusuna parmağımla hiçbir şey yazmadım.";
    const messy = [
      "@Deniz",
      FLOW_NO_ONSCREEN_TEXT_HEAD,
      "[SHOT] fogged taxi glass, rain outside",
      FLOW_NO_ONSCREEN_TEXT_TAIL,
      "[AUDIO]",
      "A female narrator voice-over says exactly, off screen:",
      `"${quote}"`,
      "[RESTRICTIONS] Nobody on screen moves their lips.",
    ].join("\n\n");
    const stamped = stampNoOnscreenTextLock(messy);
    expect(stamped).toContain(quote);
    expect(stamped).toContain("[AUDIO]");
    expect(stamped).toContain("Nobody on screen moves their lips");
    const { text } = compactPromptForFlow(stamped, "Turkish", 1800);
    expect(text).toContain(quote);
    expect(text.indexOf(quote)).toBeLessThan(700);
  });

  it("kesitte gomulu kuyruk olsa bile compact tirnakli sozu basa koyar", () => {
    const quote = "Deniz, anahtarlığın dişlerine bastım, telefon avucumda titredi.";
    const hugeShot = "[SHOT] " + "wet street taxi rain ".repeat(400);
    const full = [
      "@Kerem",
      hugeShot,
      FLOW_NO_ONSCREEN_TEXT_TAIL,
      "[AUDIO]",
      "A female narrator voice-over says exactly, off screen:",
      `"${quote}"`,
      "[RESTRICTIONS] no subtitles",
    ].join("\n\n");
    const { text, truncated } = compactPromptForFlow(full, "Turkish", 2000);
    expect(truncated).toBe(true);
    expect(text).toContain(quote);
    expect(text).toMatch(/\[SPOKEN LINE/);
    const shotAt = text.indexOf("[SHOT]");
    expect(text.indexOf(quote)).toBeLessThan(shotAt === -1 ? text.length : shotAt);
  });

  it("finalizeFlowPrompt kayitta da 8000 hard limit uygular", () => {
    const bloated = [
      "@Luluma",
      "[ANIMATED SONG FILM]",
      "[CAST — LOCKED EVERY FRAME] lead",
      "[STYLE] " + "cinematic photoreal world lock words ".repeat(200),
      "[PERFORMANCE — SHOT PLAN]",
      'SONG LINE THIS CLIP: "Ormanda dostlar var"',
      "SET (locked for the WHOLE song): deep forest canopy.",
      "ACTION TIMELINE:\n" + "1s dance beat bounce ".repeat(300),
      "[LIP SYNC] mime the master",
      "[AUDIO] no VO",
    ].join("\n\n");
    const { text, truncated } = finalizeFlowPrompt(bloated, "Türkçe", FLOW_PROMPT_MAX);
    expect(truncated).toBe(true);
    expect(text.length).toBeLessThanOrEqual(FLOW_PROMPT_MAX);
    expect(text).toContain("Ormanda dostlar var");
    expect(text).toContain(FLOW_NO_ONSCREEN_TEXT_HEAD);
    expect(text).toContain(FLOW_NO_ONSCREEN_TEXT_TAIL);
  });

  it("ust/alt yazı yasagi 8000 icinde bas+son damgada net yazilir", () => {
    const { text } = finalizeFlowPrompt(
      '[PERFORMANCE — SHOT PLAN]\nSONG LINE: "Merhaba"\n[AUDIO] song only',
      "Türkçe",
      FLOW_PROMPT_MAX
    );
    expect(text.length).toBeLessThanOrEqual(FLOW_PROMPT_MAX);
    expect(text).toMatch(/NO text at the TOP/i);
    expect(text).toMatch(/NO text at the BOTTOM/i);
    expect(text).toMatch(/TOP band clean/i);
    expect(text).toMatch(/BOTTOM band clean/i);
    expect(text).toMatch(/üst yazı|alt yazı/i);
  });
});
