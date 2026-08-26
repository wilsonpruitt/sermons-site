# sermons.wilsonpruitt.com — plan

Public, read-only web copy of the **sermons in `~/vault`** so Wilson can search and read old sermons from his phone. Replaces the Obsidian Sync/Publish subscription for this one purpose. No login.

Written 2026-08-26 (Fable). **Decisions 2, 3, 4 ratified by Wilson 2026-08-26 — nothing left to decide; execute in order.** Meant to be executed by a cheaper session (Sonnet is fine for all of it; the tag batch runs on whatever `sermon-tag-batch-2.js` already uses).

## What exists (verified 2026-08-26)

- Vault `~/vault` (git, private GitHub `wilsonpruitt/vault`, 228 MB incl. 87 MB `attachments/`). 2,046 notes. Contains board emails, funerals, pastoral notes — **most of the vault must never be published.**
- **361 notes with `type: sermon`**: Bee Creek 182 · Covenant 2023 25 · 2024 51 · 2025 52 · 2026 50 · 2027 1.
- Faceted frontmatter on the tagged ones: `title date type church series liturgical scripture[] themes[] illustrations[] summary tags`. Vocabulary: 877 scripture refs, **479 canonical themes** (+ `_indexes/themes.csv` with categories), 2,083 illustrations.
- `~/vault/_indexes/` — Scripture / Theme / Series / Illustration index pages already built as markdown with `[[wikilinks]]` (`build_indexes.py`).
- Toolchain `~/ulysses-migration/`: `sermon-tag-batch-2.js` (fan-out tagger, schema output) → `apply_tags.py` (JSON → frontmatter) → `consolidate_themes.py` + `mapping-flat.json` (theme canon) → `build_indexes.py`.
- Untagged-but-preached since the June 15 batch: **July 5, 12, 19, 26; Aug 2, 9, 16, 23** (themes `[]`) and **Aug 30** (no frontmatter at all — written fresh in Obsidian). Sept 6 → Nov 22 and 2027 "Baptism of the Lord" are **lectionary stubs** (400–800 words of readings, future-dated).
- Site: `wilsonpruitt.com` = Next.js 16 at `~/Documents/Personal/Websites/wilsonpruitt-next`, Vercel team `wilson-pruitts-projects`, DNS at Cloudflare (DNS-only records).

## Decisions

1. **Separate repo, privacy by construction.** `~/sermons-site` is its own repo (private). A sync script *copies* only sermon notes + `_indexes/` out of the vault into it. Nothing else can leak because nothing else is in the repo Vercel builds. (Rejected: building from inside the vault repo with a filter — one bad glob publishes board emails.)
2. **Generator: Quartz 4** (Obsidian → static site). It already does what the vault needs: wikilinks, `#tags`, full-text search, backlinks, mobile layout, dark mode, and it renders the existing `_indexes/*.md` pages as-is. Near-zero custom code. If Wilson later wants it to look like part of wilsonpruitt.com or wants real facet pages (Scripture by book → chapter), swap the generator for Astro + Pagefind; the sync script and content are unchanged.
3. **Hosting:** Vercel project `sermons` on the `wilson-pruitts-projects` team (same as wilsonpruitt.com). Cloudflare CNAME `sermons` → `cname.vercel-dns.com`, DNS-only. Commit author must be `littleeachdayapp@gmail.com` (team rule).
4. **No password; `noindex` on.** Anyone with the link can read; search engines don't crawl. One meta tag, flip it later if wanted. (Default I'd choose — Wilson can say otherwise.)
5. **What's a "sermon" for the site:** `type: sermon` AND `date <= today` AND body > ~100 words (excludes true title-only stubs; keeps short-but-real sermons like a 218-word "Fragments"). That excludes the lectionary stubs automatically and the stubs become sermons the week they're written — no manual step.
6. **Update flow = one command.** `~/bin/sermons-sync`: copy → report untagged preached sermons → `git commit` → `git push` → Vercel auto-deploys. Wilson runs it after Sunday. Pushing to this repo's `main` is the deploy; it's a low-stakes personal site, so no per-push OK needed *after* the first one.

## Content mapping (sync script, Python 3.11, `~/sermons-site/scripts/sync.py`)

- Source globs: `ministry/*/Sermons*/**/*.md` + `_indexes/*.md`. Filter by rule 5.
- Notes **without frontmatter** (the Aug 30 case): derive `title` from first `#` heading, `date` from filename ("August 30, 2026"), `church` + `liturgical` from folder path, `type: sermon`, `tags: [sermon]`. Write that frontmatter **back into the vault note too** so the vault stays the source of truth (that's what `apply_tags.py`'s derive step already does — reuse it).
- Output path: `content/{church}/{year}/{slug}.md`. Add `themes` into Quartz `tags` (`theme/<slug>`) so every theme is a clickable tag page; keep `scripture`/`illustrations`/`summary` as frontmatter Quartz shows in the page header via a small component (or just render them at the top of the body during sync — simpler, do that).
- Attachments: copy only images referenced by copied sermons (`![[...]]`) into `content/attachments/`. Expect a handful, not 87 MB.
- Rewrite `[[wikilinks]]` that point outside the copied set to plain text (Quartz would otherwise render dead links).
- Never copy: `Funerals/`, `Devotionals/`, anything not `type: sermon`. Memorials/weddings that were mistakenly tagged `type: sermon` (memory: "Pet Blessing", "March 8 2026" etc.) — the sync prints the list of copied titles on first run; Wilson strikes any that aren't sermons and we fix the `type` in the vault.

## Steps

**A. Tag the nine preached sermons** (do first; it's what makes the site useful for this summer)
1. `cd ~/ulysses-migration`, copy `sermon-tag-batch-2.js` → `sermon-tag-batch-3.js`, NOTES = the 9 paths above (Aug 30 needs frontmatter derived first — `apply_tags.py` derive step).
2. Run it (9 agents; small — well under any burn threshold). Output `batch-3.json`.
3. `apply_tags.py batch-3.json` → frontmatter. `consolidate_themes.py` with `mapping-flat.json`; new themes that don't map: add to `mapping.json` by hand (expect 5–15), keep the canon at ~480, don't let it sprawl.
4. `build_indexes.py` over ALL result JSONs (pilot + recovered + batch-2 + batch-3). Commit vault: "Tag Jul–Aug 2026 sermons; rebuild indexes".
5. Also fix the cosmetic `series: "2022"` artifacts and retype the non-sermons found in the memory's OPEN cleanup note while in there.

**B. Site skeleton**
1. `npx quartz create` in `~/sermons-site` (empty content, "copy" mode not used — content is generated). Config: `pageTitle: "Sermons · Wilson Pruitt"`, `baseUrl: sermons.wilsonpruitt.com`, enable Search, TagPage, Backlinks, FolderPage; disable Graph (noise at 361 nodes on a phone), disable RSS/sitemap while noindex.
2. `<meta name="robots" content="noindex">` in the head component.
3. Landing page (`content/index.md`, generated by sync): "Latest" (last 10 by date), then links to Scripture / Theme / Series / Illustration indexes, then years by church.
4. `git init`, private GitHub repo `wilsonpruitt/sermons-site` (created via `gh` — Wilson's OK on the repo name).

**C. Sync script + first run** — per the mapping above; `~/bin/sermons-sync` wrapper. Review the copied-title list with Wilson (the only judgment call in the whole build).

**D. Deploy**
1. `npx vercel link` → new project `sermons` on `wilson-pruitts-projects`; build command `npx quartz build`, output `public`.
2. Cloudflare: CNAME `sermons` → `cname.vercel-dns.com`, DNS only. `npx vercel domains add sermons.wilsonpruitt.com`.
3. First production push — **ask Wilson before this one push** (it's the moment the sermons go public). After that, `sermons-sync` is routine.

**E. Check on the phone**: search "billboard on 71" → should find *Fragments* (Bee Creek 2021). Open a theme tag page, a scripture index entry, one 2026 sermon with images.

## Later, only if wanted
- Astro + Pagefind rebuild with wilsonpruitt.com's look and real Scripture book→chapter navigation.
- Auto-tagging inside `sermons-sync` via a direct API call (Sonnet, existing schema) so untagged sermons never accumulate — removes the Claude Code step from the weekly loop.
- Devotionals (424, still untagged) as a second section.

## Estimated effort
Step A ≈ 30 min (mostly agent wait). B+C+D ≈ one Sonnet session, 2–3 hours. Token burn is small: 9 tagging agents + normal coding.

## Progress log
- 2026-08-26: Step A launched as a background Workflow (`sermon-tag-batch-3.js`, 9 sermons). Quartz cloned into this directory as the site scaffold (Step B.1 underway) — this repo's git history currently belongs to upstream Quartz and must be reset to a fresh history before creating `wilsonpruitt/sermons-site`.
