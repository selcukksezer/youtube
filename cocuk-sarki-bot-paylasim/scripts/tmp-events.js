const { PrismaClient } = require("@prisma/client");
const fs = require("fs");
const p = new PrismaClient();
(async () => {
  const id = "cmszwhe1s0000s670ruifw66f";
  const clips = await p.clip.findMany({
    where: { projectId: id, index: { in: [1, 2, 3] } },
    orderBy: { index: "asc" },
    select: { index: true, shotType: true, dialogue: true, prompt: true },
  });
  for (const c of clips) {
    const pr = c.prompt || "";
    const markers = ["[AUDIO", "[AUDIO AND SPEECH]", "says exactly", "voice-over", c.dialogue.slice(0, 30), "[SHOT]", "[STORY WORD"];
    console.log("==== CLIP", c.index, c.shotType, "len", pr.length);
    for (const m of markers) {
      console.log(" has", JSON.stringify(m).slice(0, 40), pr.includes(m));
    }
    const idx = pr.search(/\[AUDIO/i);
    console.log(" AUDIO_IDX", idx);
    const shot = pr.search(/\[SHOT/i);
    console.log(" SHOT_IDX", shot);
    fs.writeFileSync(`scripts/tmp-prompt-${c.index}.txt`, pr, "utf8");
  }
  await p.$disconnect();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
