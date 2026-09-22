const { PrismaClient } = require("@prisma/client");
const p = new PrismaClient();
(async () => {
  const id = "cmszwhe1s0000s670ruifw66f";
  const sides = await p.characterProfile.findMany({
    where: { projectId: id, role: "side" },
  });
  for (const s of sides) {
    console.log(s.id, s.name, s.gender, s.age, s.storyRole);
  }
  const keremPath =
    "C:\\Users\\oem\\Desktop\\FLOW HİKAYE BOT\\projects\\yasak-ask-5dk\\character\\reference-flow-kerem-2.png";
  const efePath =
    "C:\\Users\\oem\\Desktop\\FLOW HİKAYE BOT\\projects\\yasak-ask-5dk\\character\\reference-flow-efe-2.png";

  for (const s of sides) {
    const n = s.name.toLowerCase();
    const role = (s.storyRole || "").toLowerCase();
    if (n.includes("kerem") || role.includes("gizli") || role.includes("işyer") || role.includes("isyer")) {
      await p.characterProfile.update({
        where: { id: s.id },
        data: { referenceImagePath: keremPath, flowCharacterReference: "@Kerem", imageApproved: true },
      });
      console.log("ATTACH Kerem ->", s.name);
    } else if (n.includes("mert") || role.includes("eşi") || role.includes("esi") || role.includes("koca")) {
      await p.characterProfile.update({
        where: { id: s.id },
        data: { referenceImagePath: efePath, flowCharacterReference: "@Efe", imageApproved: true },
      });
      console.log("ATTACH Efe/husband ->", s.name);
    }
  }
  await p.$disconnect();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
