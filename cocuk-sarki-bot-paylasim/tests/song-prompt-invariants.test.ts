import { describe, expect, it } from "vitest";
import { composeShotPrompt } from "@/server/services/song";
import { buildClipPrompt } from "@/server/services/prompt-builder";
import { compactPromptForFlow, stampNoOnscreenTextLock, finalizeFlowPrompt, FLOW_PROMPT_MAX } from "@/lib/flow-prompt-compact";
import { detectHeroSubject, detectSongWorld } from "@/lib/song-lyric-visual";
import { resolveSongVarietyPack } from "@/lib/song-variety";

/**
 * DEGISMEZ KURALLAR: konu / sozler / klip sayisi ne olursa olsun her sarki
 * klibinde ayni sabit ayarlar uretilmeli. Bu test farkli temalardaki farkli
 * sozlerle ayni garantileri dogrular — "gelecekteki tum projelerde de gecerli mi"
 * sorusunun regresyon kalkani.
 */

const SONGS = [
  {
    ad: "orman",
    sozler: [
      "Ormanda dostlar var, kelebekler uçar",
      "Ormanda tavşan zıplar, kuşlar söyler",
      "Ormanda dostlar var, hadi say bir bir",
    ],
    beklenenDunya: "forest",
  },
  {
    ad: "domates",
    sozler: [
      "Dom dom domates, hey hey domates",
      "Kırmızı domates hopla, domates zıpla",
      "Domates dans eder, alkışla domates",
    ],
    beklenenHero: "tomato",
  },
  {
    ad: "deniz",
    sozler: [
      "Denizde balıklar yüzer, dalgalar gelir",
      "Kumsalda oynarız, deniz kabuğu bulduk",
      "Denizde balık dostlar, hadi yüz",
    ],
    beklenenDunya: "sea",
  },
  {
    ad: "uzay",
    sozler: [
      "Uzayda roket uçar, yıldızlar parlar",
      "Gezegenler döner, roket hızlı gider",
      "Uzayda roket dostum, hadi bin",
    ],
    beklenenDunya: "space",
  },
];

function sahneKlibi(sozler: string, index: number) {
  return {
    index,
    section: index === 1 ? "intro" : "verse",
    lyrics: sozler,
    syllableCount: 12,
    sceneDescription: "sahne",
    imagePrompt: "mascot performs in the set with friends around",
    choreography: "clap and spin on the beat",
    voiceTone: "bright",
    emotion: "neseli",
    mustShowProps: "",
    lyricSyncAction: "",
    hookNote: "",
    curiosityScore: 5,
    singerName: "Pofu",
    environment: "",
  } as Parameters<typeof composeShotPrompt>[0];
}

function projeBaglami(
  clipIndex: number,
  sozler: string,
  imagePrompt: string,
  clipSeconds: number,
  visualStyleOverride?: string
) {
  return {
    project: {
      templateType: "kids_song",
      speechLanguage: "Türkçe",
      promptTemplate: "",
      useFlowCharacter: true,
      aspectRatio: "16:9",
      visualStyle: visualStyleOverride ?? "pixar3d",
      allowSubtitles: false,
      emotionCurve: "",
      clipSeconds,
      useReference: true,
    },
    character: {
      name: "Pofu",
      baseAppearancePrompt: "round yellow mascot with soft fur",
      baseWardrobePrompt: "blue vest",
      baseEnvironmentPrompt: "",
      baseCameraPrompt: "",
      baseVoicePrompt: "warm",
      negativePrompt: "",
      flowCharacterReference: "@Pofu",
    },
    supportingCast: [
      {
        name: "Mini",
        role: "support",
        storyRole: "support",
        baseAppearancePrompt: "small green friend",
        baseWardrobePrompt: "",
        flowCharacterReference: "@Mini",
      },
    ],
    clip: {
      dialogue: sozler,
      index: clipIndex,
      sceneDescription: "sahne",
      voiceTone: "bright",
      emotionLabel: "neseli",
      imagePrompt,
    },
    isFirstClip: clipIndex === 1,
  } as unknown as Parameters<typeof buildClipPrompt>[0];
}

/** Her klipte bulunmasi ZORUNLU sabit bloklar. */
const ZORUNLU: Array<[string, RegExp]> = [
  ["yazi yasagi (bas)", /\[SABIT KURAL — ALTYAZI YOK\]/],
  ["yazi yasagi (son)", /\[SABIT KURAL SONU — ALTYAZI YOK\]/],
  ["ust bant yasagi", /NO text at the TOP/i],
  ["alt bant yasagi", /NO text at the BOTTOM/i],
  ["film basligi", /\[ANIMATED SONG FILM/],
  ["kadro kilidi", /\[CAST — LOCKED EVERY FRAME\]/],
  ["stil", /\[STYLE\]/],
  ["shot plan", /\[PERFORMANCE — SHOT PLAN\]/],
  ["dudak senkronu", /\[LIP SYNC\]/],
  ["audio kurali", /\[AUDIO\]/],
  ["soz satiri", /SONG LINE THIS CLIP/],
  ["sahneleme", /STAGE EVERY SUNG WORD/],
  ["zaman cizelgesi", /ACTION TIMELINE 0-/],
  ["kadro sadakati", /100% on-model/i],
];

describe("Sabit ayarlar her sarkida ve her klipte aynidir", () => {
  for (const song of SONGS) {
    const tumSozler = song.sozler.join("\n");
    const dunya = detectSongWorld(tumSozler);
    const hero = detectHeroSubject(tumSozler, song.ad);

    it(`${song.ad}: her klip tum sabit bloklari tasir (1., orta ve son klip)`, () => {
      const clipSeconds = 8;
      const indexler = [1, 2, song.sozler.length];
      for (const index of indexler) {
        const sozler = song.sozler[Math.min(index, song.sozler.length) - 1]!;
        const shot = composeShotPrompt(sahneKlibi(sozler, index), clipSeconds, undefined, dunya, hero);
        const prompt = stampNoOnscreenTextLock(buildClipPrompt(projeBaglami(index, sozler, shot, clipSeconds)));

        for (const [etiket, re] of ZORUNLU) {
          expect(re.test(prompt), `${song.ad} klip ${index}: ${etiket} eksik`).toBe(true);
        }
        // Soz birebir promptta, ve YALNIZCA bir kez tirnakli
        expect(prompt).toContain(sozler);
        expect((prompt.match(/"/g) || []).length).toBeLessThanOrEqual(4);
        // Flow'a yazilirken de dusmez
        const { text } = compactPromptForFlow(prompt, "Türkçe", FLOW_PROMPT_MAX);
        expect(text).toContain(sozler);
        expect(text).toMatch(/\[SABIT KURAL — ALTYAZI YOK\]/);
        expect(text).toContain("[CAST — LOCKED EVERY FRAME]");
      }
    });

    it(`${song.ad}: 100 kliplik uretimde de bloklar birebir ayni kalir`, () => {
      const sozler = song.sozler[0]!;
      const ilk = composeShotPrompt(sahneKlibi(sozler, 1), 8, undefined, dunya, hero);
      const yuzuncu = composeShotPrompt(sahneKlibi(sozler, 100), 8, undefined, dunya, hero);
      const p1 = stampNoOnscreenTextLock(buildClipPrompt(projeBaglami(1, sozler, ilk, 8)));
      const p100 = stampNoOnscreenTextLock(buildClipPrompt(projeBaglami(100, sozler, yuzuncu, 8)));

      for (const [etiket, re] of ZORUNLU) {
        expect(re.test(p1), `klip 1: ${etiket}`).toBe(true);
        expect(re.test(p100), `klip 100: ${etiket}`).toBe(true);
      }
      // Yazi yasagi metni birebir ayni (klip 1 == klip 100)
      const yasak = (s: string) => s.match(/\[SABIT KURAL — ALTYAZI YOK\][\s\S]*?(?=\n\n)/)?.[0];
      expect(yasak(p1)).toBe(yasak(p100));
      // Klip 100 sureklilik kurali tasir, klip 1 cold open
      expect(p100).toMatch(/match-on-action/i);
      expect(p1).toMatch(/Cold open/i);
      // Klipler arasi kopma yasagi + dudak senkronu her ikisinde de var
      expect(p100).toMatch(/FORBIDDEN AT THE CUT/);
      expect(p100).toMatch(/MIME THE MASTER TRACK EXACTLY/);
      expect(p1).toMatch(/MIME THE MASTER TRACK EXACTLY/);
    });

    if (song.beklenenDunya) {
      it(`${song.ad}: set kilidi ${song.beklenenDunya} olarak sabitlenir ve celisen mekan yazilmaz`, () => {
        expect(dunya?.key).toBe(song.beklenenDunya);
        const shot = composeShotPrompt(
          sahneKlibi(song.sozler[0]!, 1) as Parameters<typeof composeShotPrompt>[0],
          8,
          undefined,
          dunya,
          hero
        );
        expect(shot).toMatch(/SET \(locked for the WHOLE song\)/);
        expect(shot).toMatch(/NEVER show:/);
      });
    }

    if (song.beklenenHero) {
      it(`${song.ad}: kahraman nesne ${song.beklenenHero} her klipte on planda`, () => {
        expect(hero?.label).toBe(song.beklenenHero);
        for (const index of [1, 2, 3]) {
          const shot = composeShotPrompt(sahneKlibi(song.sozler[index - 1]!, index), 8, undefined, dunya, hero);
          expect(shot).toContain("HERO WITH LEAD");
          expect(shot.toUpperCase()).toContain(song.beklenenHero!.toUpperCase());
        }
      });
    }
  }

  it("prompt Flow limitine SIGAR — hicbir stilde kesilme olmaz", () => {
    // Kesilme olursa [STYLE] / gerceklik / dunya kilidi dusuyor ve Veo jenerik
    // cizgi filme donuyordu. Bu test o regresyonu bir daha yasatmaz.
    for (const style of ["pixar3d", "photorealistic", "cinematic", "documentary", "anime"]) {
      for (const song of SONGS) {
        const dunya = detectSongWorld(song.sozler.join("\n"));
        const hero = detectHeroSubject(song.sozler.join("\n"), song.ad);
        for (const index of [1, 2, song.sozler.length]) {
          const sozler = song.sozler[Math.min(index, song.sozler.length) - 1]!;
          const shot = composeShotPrompt(sahneKlibi(sozler, index), 8, undefined, dunya, hero);
          const { text, truncated } = finalizeFlowPrompt(
            buildClipPrompt(projeBaglami(index, sozler, shot, 8, style)),
            "Türkçe",
            FLOW_PROMPT_MAX
          );

          expect(text.length, `${style} / ${song.ad} klip ${index}: ${text.length} > ${FLOW_PROMPT_MAX}`).toBeLessThanOrEqual(
            FLOW_PROMPT_MAX
          );
          expect(truncated, `${style} / ${song.ad} klip ${index}: prompt kesildi`).toBe(false);
          expect(text).toContain("[STYLE]");
          expect(text).toContain("WORLD FAMILY LOCK");
          expect(text).toContain("[LIP SYNC]");
          expect(text).toContain(sozler);
        }
      }
    }
  });

  it("look pack promptta yalnizca BIR kez yazilir (tekrar = limit asimi)", () => {
    const song = SONGS[0]!;
    const dunya = detectSongWorld(song.sozler.join("\n"));
    const pack = resolveSongVarietyPack({ id: "proj-lookpack-tek" });
    const shot = composeShotPrompt(sahneKlibi(song.sozler[1]!, 2), 8, pack, dunya, null);
    // Sahne plani look pack YAZMAZ; onu yalnizca [STYLE] blogu yazar.
    expect(shot).not.toMatch(/LOOK PACK/);

    const ctx = projeBaglami(2, song.sozler[1]!, shot, 8) as Parameters<typeof buildClipPrompt>[0] & {
      project: { id?: string };
    };
    ctx.project.id = "proj-lookpack-tek";
    const prompt = stampNoOnscreenTextLock(buildClipPrompt(ctx));
    expect((prompt.match(/LOOK PACK/g) || []).length).toBe(1);
  });

  it("klip suresi degisse de zaman cizelgesi ona uyar", () => {
    for (const saniye of [4, 6, 8, 10]) {
      const shot = composeShotPrompt(sahneKlibi("Dom dom domates hopla", 3), saniye, undefined, null, null);
      expect(shot).toContain(`ACTION TIMELINE 0-${saniye}s`);
    }
  });
});
