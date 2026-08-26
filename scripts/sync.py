#!/usr/local/bin/python3.11
"""Sync sermons from ~/vault into this repo's content/ folder for the Quartz site.

Copies ONLY notes with type: sermon, dated today or earlier, with a real body
(not a bare lectionary stub). Nothing else in the vault is ever read into
content/ -- board emails, funerals, pastoral notes stay in the vault.

Usage: sync.py [--write]   (default = dry-run report only)
"""
import os, sys, re, json, glob
from datetime import date
import yaml

VAULT = os.path.expanduser("~/vault")
SITE = os.path.expanduser("~/sermons-site")
CONTENT = os.path.join(SITE, "content")
MIN_WORDS = 100
MIN_PROSE_WORDS = 60

# Notes that are entirely borrowed source material (song lyrics, etc.) with
# no scripture citation markup for the structural filter to catch and no
# sermon prose at all. Hand-confirmed, not auto-detected.
MANUAL_EXCLUDE = {
    "ministry/bee-creek-umc/Sermons/2021/Easter 2021- Works of Love/Mal Love writes a letter and sends it to Hate.md",
}

FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
CITATION_RE = re.compile(
    r'^[⁠-⁤​﻿‎‏‹⁸]*'
    r'[“"\'‘]?\s*[1-3]?\s*[A-Z][a-zA-Z ]+\s+\d+[:–—,\d\- ]*\s*'
    r'(NRSVUE|NRSV|NIV|ESV|CEB|KJV|NASB)?[”"\'’]*[⁠-⁤​]*$'
)
URL_RE = re.compile(r'^https?://\S+$')

def strip_invisible(line):
    return re.sub(r'[⁠-⁤​﻿‎‏‹⁸]', '', line)

def read_note(path):
    text = open(path, encoding="utf-8").read()
    m = FM_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(2)

def slugify(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "untitled"

def word_count(body):
    return len(re.findall(r"\S+", body))

def prose_word_count(body):
    """Word count excluding headings, citation lines, bare URLs, and any
    paragraph that is itself a wrapped scripture quotation (starts with a
    quote mark or asterisk and runs long). Distinguishes a real sermon from
    a note that is just the lectionary readings with no reflection written in."""
    total = 0
    for line in body.split("\n"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        clean = strip_invisible(s)
        if CITATION_RE.match(clean) or URL_RE.match(clean):
            continue
        if clean.startswith(("*", '"', '“')) and len(clean) > 40:
            continue
        total += len(re.findall(r"\S+", clean))
    return total

def find_sermons():
    pattern = os.path.join(VAULT, "ministry", "*", "Sermons*", "**", "*.md")
    today = date.today()
    found = []
    for path in glob.glob(pattern, recursive=True):
        fm, body = read_note(path)
        if fm.get("type") != "sermon":
            continue
        if os.path.relpath(path, VAULT) in MANUAL_EXCLUDE:
            continue
        d = fm.get("date")
        if isinstance(d, date):
            pass
        elif isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except ValueError:
                d = None
        else:
            d = None
        if d and d > today:
            continue  # future lectionary stub
        if word_count(body) < MIN_WORDS:
            continue  # stub, no real content yet
        if prose_word_count(body) < MIN_PROSE_WORDS:
            continue  # nothing but the readings -- no sermon actually written
        found.append((path, fm, body, d))
    return found

def build_mapping(sermons):
    """path -> (new_content_relpath_without_ext, title)"""
    mapping = {}
    seen_slugs = {}
    for path, fm, body, d in sermons:
        rel = os.path.relpath(path, VAULT)
        parts = rel.split(os.sep)
        church = fm.get("church") or (parts[1] if len(parts) > 1 else "unknown")
        year = str(d.year) if d else "undated"
        title = fm.get("title") or os.path.splitext(os.path.basename(path))[0]
        slug = slugify(title)
        key = (church, year, slug)
        n = seen_slugs.get(key, 0)
        seen_slugs[key] = n + 1
        if n:
            slug = f"{slug}-{n+1}"
        new_rel = f"{church}/{year}/{slug}"
        mapping[rel[:-3]] = (new_rel, title)
    return mapping

def render_note(fm, body, title):
    L = ["---"]
    L.append(f'title: {json.dumps(title)}')
    if fm.get("date"):
        L.append(f'date: {fm["date"]}')
    if fm.get("church"):
        L.append(f'church: {fm["church"]}')
    if fm.get("series"):
        L.append(f'series: {json.dumps(fm["series"])}')
    if fm.get("liturgical"):
        L.append(f'liturgical: {json.dumps(fm["liturgical"])}')
    tags = ["sermon"] + [f"theme/{t}" for t in (fm.get("themes") or [])]
    L.append("tags:")
    L += [f"  - {t}" for t in tags]
    if fm.get("description") or fm.get("summary"):
        L.append(f'description: {json.dumps(fm.get("summary") or fm.get("description"))}')
    L.append("---\n")

    header = []
    scripture = fm.get("scripture") or []
    if scripture:
        header.append("**Scripture:** " + "; ".join(scripture))
    if fm.get("series"):
        header.append(f'**Series:** {fm["series"]}')
    if fm.get("summary"):
        header.append(f'\n> {fm["summary"]}')
    illustrations = fm.get("illustrations") or []
    if illustrations:
        names = illustrations if isinstance(illustrations[0], str) else [i.get("name", i) for i in illustrations]
        header.append("\n**Illustrations:** " + ", ".join(names))

    header_block = "\n".join(header)
    return "\n".join(L) + (header_block + "\n\n---\n\n" if header_block else "") + body.lstrip("\n")

def rewrite_wikilinks(text, mapping):
    """[[vault/relpath|Display]] or [[vault/relpath]] -> resolved new path, else plain text."""
    def repl(m):
        target, display = m.group(1), m.group(2)
        display = display or os.path.basename(target)
        hit = mapping.get(target)
        if hit:
            return f"[[{hit[0]}|{display}]]"
        return display
    return re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", repl, text)

def copy_indexes(mapping, write):
    src_dir = os.path.join(VAULT, "_indexes")
    dst_dir = os.path.join(CONTENT, "indexes")
    for name in ("Scripture Index.md", "Series Index.md", "Theme Index.md", "Illustration Index.md"):
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            continue
        text = open(src, encoding="utf-8").read()
        new_text = rewrite_wikilinks(text, mapping)
        if write:
            os.makedirs(dst_dir, exist_ok=True)
            with open(os.path.join(dst_dir, name), "w", encoding="utf-8") as f:
                f.write(f'---\ntitle: "{name[:-3]}"\n---\n\n' + new_text)

def write_landing(sermons, mapping, write):
    by_date = sorted(sermons, key=lambda x: x[3] or date.min, reverse=True)
    L = ["---", 'title: "Sermons"', "---", ""]
    L.append("## Latest")
    for path, fm, body, d in by_date[:10]:
        rel = os.path.relpath(path, VAULT)[:-3]
        new_rel, title = mapping[rel]
        L.append(f"- [[{new_rel}|{title}]] ({d})" if d else f"- [[{new_rel}|{title}]]")
    L.append("\n## Indexes")
    for name in ("Scripture", "Series", "Theme", "Illustration"):
        L.append(f"- [[indexes/{name} Index|{name} Index]]")
    L.append("\n## By church and year")
    by_church_year = {}
    for path, fm, body, d in sermons:
        rel = os.path.relpath(path, VAULT)[:-3]
        new_rel, title = mapping[rel]
        church = fm.get("church", "unknown")
        year = str(d.year) if d else "undated"
        by_church_year.setdefault((church, year), []).append((new_rel, title, d))
    for (church, year) in sorted(by_church_year, key=lambda k: (k[0], k[1])):
        L.append(f"\n### {church} — {year}")
        for new_rel, title, d in sorted(by_church_year[(church, year)], key=lambda x: x[2] or date.min):
            L.append(f"- [[{new_rel}|{title}]]")
    text = "\n".join(L) + "\n"
    if write:
        os.makedirs(CONTENT, exist_ok=True)
        with open(os.path.join(CONTENT, "index.md"), "w", encoding="utf-8") as f:
            f.write(text)

def main():
    write = "--write" in sys.argv
    sermons = find_sermons()
    mapping = build_mapping(sermons)

    print(f"{'WRITING' if write else 'DRY-RUN'}: {len(sermons)} sermons match the publish rule\n")

    untagged = [ (p, fm) for p, fm, body, d in sermons if not fm.get("themes") ]
    if untagged:
        print(f"⚠ {len(untagged)} preached sermons have NO themes (tag these before next sync):")
        for p, fm in untagged:
            print(f"   {os.path.relpath(p, VAULT)}")
        print()

    if write:
        for f in glob.glob(os.path.join(CONTENT, "*")):
            if os.path.basename(f) in ("index.md",):
                os.remove(f)
        import shutil
        for sub in ("indexes",):
            shutil.rmtree(os.path.join(CONTENT, sub), ignore_errors=True)
        for church_dir in glob.glob(os.path.join(CONTENT, "*")):
            if os.path.isdir(church_dir) and os.path.basename(church_dir) not in ("indexes",):
                shutil.rmtree(church_dir)

    print("Copying (title -> new path):")
    for path, fm, body, d in sermons:
        rel = os.path.relpath(path, VAULT)[:-3]
        new_rel, title = mapping[rel]
        print(f"  {title}  ->  content/{new_rel}.md")
        if write:
            dst = os.path.join(CONTENT, new_rel + ".md")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(render_note(fm, body, title))

    copy_indexes(mapping, write)
    write_landing(sermons, mapping, write)

    print(f"\n{'APPLIED' if write else 'DRY-RUN'}: {len(sermons)} sermons synced to content/")

if __name__ == "__main__":
    main()
