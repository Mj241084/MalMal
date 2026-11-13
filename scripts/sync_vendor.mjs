import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const copies = [
  [
    "node_modules/@fontsource/inter/files/inter-latin-400-normal.woff2",
    "static/fonts/inter/Inter-Regular-latin.woff2",
  ],
  [
    "node_modules/@fontsource/inter/files/inter-latin-500-normal.woff2",
    "static/fonts/inter/Inter-Medium-latin.woff2",
  ],
  [
    "node_modules/htmx.org/dist/htmx.min.js",
    "static/js/htmx.min.js",
  ],
];

for (const [srcRel, dstRel] of copies) {
  const src = resolve(root, srcRel);
  const dst = resolve(root, dstRel);
  mkdirSync(dirname(dst), { recursive: true });
  copyFileSync(src, dst);
  console.log(`copied ${dstRel}`);
}
