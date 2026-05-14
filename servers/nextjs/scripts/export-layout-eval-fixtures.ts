/**
 * Writes PresentationLayoutModel JSON for evals by compiling each group's
 * app/presentation-templates/<group>/*.tsx (same as GET /api/template?group=...).
 *
 * Usage (from servers/nextjs): npm run export-layout-eval-fixtures
 * Optional: npm run export-layout-eval-fixtures -- standard,swift,general
 */
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

import { buildBuiltinTemplateLayoutPayload } from "@/lib/server-template-layouts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const nextRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(nextRoot, "..", "..");
const outDir = path.join(repoRoot, "evals", "schemas", "layouts");

async function main() {
  const arg = process.argv.slice(2).find((a) => !a.startsWith("-"));
  const groups = arg
    ? arg
        .split(",")
        .map((g) => g.trim())
        .filter(Boolean)
    : ["standard", "swift"];

  await fs.mkdir(outDir, { recursive: true });

  for (const group of groups) {
    const payload = await buildBuiltinTemplateLayoutPayload(group);
    if (!payload) {
      console.warn(`skip: no layouts for group "${group}"`);
      continue;
    }
    const outJson = path.join(outDir, `${group}.json`);
    await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + "\n", "utf8");

    const meta = {
      group,
      num_layouts: payload.slides.length,
      indices_by_id: Object.fromEntries(
        payload.slides.map((s, i) => [s.id, i]),
      ),
    };
    await fs.writeFile(
      path.join(outDir, `${group}.meta.json`),
      JSON.stringify(meta, null, 2) + "\n",
      "utf8",
    );
    console.log(
      `wrote ${path.relative(repoRoot, outJson)} (${meta.num_layouts} layouts)`,
    );
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
