/**
 * Bulk export: one JSONL line per sermon (Appendix E schema,
 * ~/open-corpus/PLAN.md), gzipped. Run BEFORE `npx quartz build` — it also
 * (re)writes content/export.md with the manifest, which quartz build then
 * renders. Hosting is the shared Cloudflare R2 bucket `wroot-corpus-export`,
 * prefix `sermons/`, per PLAN.md item 8 — not committed (export/ is
 * gitignored).
 *
 * Run: node scripts/build-export.mjs (from repo root)
 */
import fs from "fs";
import path from "path";
import zlib from "zlib";
import YAML from "yaml";

const ROOT = path.resolve(new URL(".", import.meta.url).pathname, "..");
const CONTENT = path.join(ROOT, "content");
const EXPORT_DIR = path.join(ROOT, "export");
const SITE_URL = "https://sermons.wilsonpruitt.com";
const today = new Date().toISOString().slice(0, 10);

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
  return rel !== "index.md" && !rel.startsWith("indexes" + path.sep) && rel !== "rights.md" && rel !== "export.md";
});

const records = [];
for (const mdPath of mdFiles) {
  const rel = path.relative(CONTENT, mdPath).replace(/\.md$/, "");
  const raw = fs.readFileSync(mdPath, "utf-8");
  const { frontmatter, body } = parseNote(raw);
  const tags = frontmatter.tags ?? [];
  if (!tags.includes("sermon")) continue;

  const slug = rel.split(path.sep).join("/");
  const themes = tags.filter((t) => t.startsWith("theme/")).map((t) => t.slice("theme/".length));
  const scriptureMatch = body.match(/^\*\*Scripture:\*\*\s*(.+)$/m);

  records.push({
    id: slug,
    url: `${SITE_URL}/${slug}/`,
    site: "sermons",
    title: frontmatter.title ?? "",
    author: "Wilson Pruitt",
    date: frontmatter.date ?? null,
    church: frontmatter.church ?? null,
    series: frontmatter.series ?? null,
    themes,
    scripture: scriptureMatch ? scriptureMatch[1].trim() : null,
    description: frontmatter.description ?? null,
    languages: ["en"],
    text: body.trim(),
    provenance: { method: "authored, not translated", corrected_against_scan: null, verified_on: null },
    license_source: null,
    license_translation: null,
    license_apparatus: "CC BY-NC 4.0",
    credits: [],
    generated: today,
    version: 1,
  });
}

fs.mkdirSync(EXPORT_DIR, { recursive: true });
const fileName = `sermons-${today}.jsonl.gz`;
const jsonl = records.map((r) => JSON.stringify(r)).join("\n") + "\n";
const gz = zlib.gzipSync(Buffer.from(jsonl, "utf-8"));
fs.writeFileSync(path.join(EXPORT_DIR, fileName), gz);

const readme = `# Sermons (Wilson Pruitt) — bulk export

Generated ${today}. ${records.length} sermons, one JSON line each (Appendix E
schema, ~/open-corpus/PLAN.md), gzipped.

## Files

- \`${fileName}\` — full text of every sermon, one JSON object per line:
  title, date, church, series, themes, scripture, description, full text,
  provenance. This is authored prose, not a translation — there is no
  source_text/source_edition pair the way the shop's other exports have one.

## License

CC BY-NC 4.0, attribution "Wilson Pruitt, sermons.wilsonpruitt.com". Machine-learning
training and retrieval are explicitly permitted under those terms. Full terms:
https://sermons.wilsonpruitt.com/rights

## Hosting

Served from the shared Cloudflare R2 bucket \`wroot-corpus-export\`
(prefix \`sermons/\`), not baked into any deploy — see \`~/open-corpus/PLAN.md\`
item 8.
`;
fs.writeFileSync(path.join(EXPORT_DIR, "README.md"), readme);

const manifest = {
  generated: today,
  sermons: records.length,
  files: [
    {
      name: fileName,
      description: "Every sermon, one JSON line each (gzipped).",
      size_bytes: fs.statSync(path.join(EXPORT_DIR, fileName)).size,
    },
    {
      name: "README.md",
      description: "Schema, license, and changelog.",
      size_bytes: fs.statSync(path.join(EXPORT_DIR, "README.md")).size,
    },
  ],
};
fs.writeFileSync(path.join(EXPORT_DIR, "manifest.json"), JSON.stringify(manifest, null, 2));

// Placeholder — the shared wroot-corpus-export R2 bucket has not been
// provisioned yet (~/open-corpus/PLAN.md item 8).
const EXPORT_R2_BASE_URL = "https://pending-r2-bucket.example/sermons";

const exportPage = `---
title: "Export"
---

The whole corpus, one JSON line per sermon, gzipped.

Generated ${today}. ${records.length} sermons.

- [${fileName}](${EXPORT_R2_BASE_URL}/${fileName}) (${(manifest.files[0].size_bytes / 1024).toFixed(0)} KB)
  — every sermon's full text, one JSON object per line
- [README.md](${EXPORT_R2_BASE_URL}/README.md) — schema, license, changelog

Licensed [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — see
[/rights](/rights) for the Machine Use terms.
`;
fs.writeFileSync(path.join(CONTENT, "export.md"), exportPage);

console.log(`Built export: ${records.length} sermons -> ${EXPORT_DIR}`);
