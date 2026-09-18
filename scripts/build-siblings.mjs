/**
 * Reading-layer contract (~/open-corpus/PLAN.md §4, Sermons entry): plain-text
 * and JSON siblings per sermon. Run AFTER `npx quartz build` (needs public/ to
 * exist), never before — it walks the already-built HTML to find each
 * sermon's real output slug rather than reimplementing Quartz's slugifier,
 * since content/*.md filenames (written by scripts/sync.py) already match
 * Quartz's output path 1:1 (verified: no further transformation happens).
 *
 * Run: node scripts/build-siblings.mjs (from repo root)
 */
import fs from "fs";
import path from "path";
import YAML from "yaml";

const ROOT = path.resolve(new URL(".", import.meta.url).pathname, "..");
const CONTENT = path.join(ROOT, "content");
const PUBLIC = path.join(ROOT, "public");
const SITE_URL = "https://sermons.wilsonpruitt.com";

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    if (fs.statSync(p).isDirectory()) walk(p, out);
    else if (name.endsWith(".md")) out.push(p);
  }
  return out;
}

function parseNote(raw) {
  const m = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!m) return { frontmatter: {}, body: raw };
  return { frontmatter: YAML.parse(m[1]) ?? {}, body: m[2] };
}

const mdFiles = walk(CONTENT).filter((f) => {
  const rel = path.relative(CONTENT, f);
  return rel !== "index.md" && !rel.startsWith("indexes" + path.sep) && rel !== "rights.md";
});

let written = 0;
for (const mdPath of mdFiles) {
  const rel = path.relative(CONTENT, mdPath).replace(/\.md$/, "");
  const raw = fs.readFileSync(mdPath, "utf-8");
  const { frontmatter, body } = parseNote(raw);
  const tags = frontmatter.tags ?? [];
  if (!tags.includes("sermon")) continue;

  const htmlPath = path.join(PUBLIC, rel + ".html");
  if (!fs.existsSync(htmlPath)) {
    console.warn(`⚠ no built HTML for ${rel} — skipping siblings`);
    continue;
  }

  const slug = rel.split(path.sep).join("/");
  const url = `${SITE_URL}/${slug}/`;
  const themes = tags.filter((t) => t.startsWith("theme/")).map((t) => t.slice("theme/".length));

  const txtHeader = [
    `Title: ${frontmatter.title ?? ""}`,
    `Author: Wilson Pruitt`,
    `Date: ${frontmatter.date ?? ""}`,
    `Church: ${frontmatter.church ?? ""}`,
    `Licence: CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/`,
    `Canonical URL: ${url}`,
    "",
    "---",
    "",
  ].join("\n");
  fs.writeFileSync(path.join(PUBLIC, rel + ".txt"), txtHeader + body.trim() + "\n");

  const scriptureMatch = body.match(/^\*\*Scripture:\*\*\s*(.+)$/m);

  const record = {
    id: slug,
    url,
    site: "sermons",
    title: frontmatter.title ?? "",
    author: "Wilson Pruitt",
    date: frontmatter.date ?? null,
    church: frontmatter.church ?? null,
    series: frontmatter.series ?? null,
    themes,
    scripture: scriptureMatch ? scriptureMatch[1].trim() : null,
    description: frontmatter.description ?? null,
    text: body.trim(),
    provenance: { method: "authored, not translated" },
    license: "CC BY-NC 4.0",
    generated: new Date().toISOString().slice(0, 10),
  };
  fs.writeFileSync(path.join(PUBLIC, rel + ".json"), JSON.stringify(record, null, 2));
  written++;
}

console.log(`Built siblings for ${written} sermons.`);
