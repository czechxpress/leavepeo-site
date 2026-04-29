#!/usr/bin/env python3
"""
Site validator. Catches every class of bug we hit in the audit.
Exits non-zero if anything is wrong.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_GA = "G-F51MZYJYMK"
EXPECTED_PHONE = "303-570-7309"
EXPECTED_PHONE_TEL = "tel:+13035707309"
EM_DASH = "\u2014"

MINIMAL_PAGES = {"404.html"}                # fewer requirements
NO_CANONICAL_OK = {"404.html", "blog.html"} # blog.html historically had none in source

errors = []
warnings = []


def fail(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_file(path):
    fn = path.name
    s = path.read_text(encoding="utf-8")

    # 1. Single, well-formed document
    if s.count("<!DOCTYPE") != 1:
        fail(f"{fn}: DOCTYPE count = {s.count('<!DOCTYPE')} (must be 1)")
    if s.count("<html") != 1:
        fail(f"{fn}: <html count = {s.count('<html')} (must be 1)")
    if "</html>" not in s.lower():
        fail(f"{fn}: missing </html>")
    if "</body>" not in s.lower():
        fail(f"{fn}: missing </body>")

    # 2. Single <title>
    titles = re.findall(r"<title>([^<]+)</title>", s)
    if len(titles) != 1:
        fail(f"{fn}: title count = {len(titles)}")
        return
    title = titles[0]

    # 3. No em dash in title
    if EM_DASH in title:
        fail(f"{fn}: em dash in title: {title!r}")

    # 4. Title contains brand
    if "LeavePEO" not in title:
        warn(f"{fn}: title missing 'LeavePEO': {title!r}")

    # 5. GA present and correct
    if EXPECTED_GA not in s:
        fail(f"{fn}: missing GA id {EXPECTED_GA}")
    if "G-XXXXXXXXXX" in s:
        fail(f"{fn}: still has GA placeholder G-XXXXXXXXXX")
    # Detect any other G-tag IDs that aren't ours
    ga_ids = set(re.findall(r"G-[A-Z0-9]{6,}", s))
    bogus = ga_ids - {EXPECTED_GA}
    if bogus:
        fail(f"{fn}: stray GA ids found: {bogus}")
    # Single GA config (catches double-fire)
    cfg_count = s.count(f"gtag('config', '{EXPECTED_GA}')") + s.count(f"gtag('config','{EXPECTED_GA}')")
    if cfg_count > 1:
        fail(f"{fn}: GA config fires {cfg_count}x (must be 1)")

    # 6. Canonical
    if fn not in NO_CANONICAL_OK:
        canons = re.findall(r'rel="canonical"\s+href="([^"]+)"', s)
        if len(canons) == 0:
            fail(f"{fn}: missing canonical")
        elif len(canons) > 1:
            fail(f"{fn}: multiple canonicals")
        else:
            url = canons[0]
            if url.endswith(".html"):
                fail(f"{fn}: canonical has .html: {url}")
            if not url.startswith("https://leavepeo.com"):
                fail(f"{fn}: canonical not on leavepeo.com: {url}")

    # 7. Phone in footer (every page)
    if EXPECTED_PHONE not in s:
        fail(f"{fn}: phone {EXPECTED_PHONE} missing")
    if EXPECTED_PHONE_TEL not in s:
        fail(f"{fn}: phone link {EXPECTED_PHONE_TEL} missing")

    # 8. target=_blank safety
    for m in re.finditer(r"<a\b[^>]*target=\"_blank\"[^>]*>", s):
        if "rel=" not in m.group(0):
            fail(f"{fn}: target=_blank without rel: {m.group(0)[:120]}")

    # 9. Single H1 (except blog.html historical exception is fixed now, expect 1)
    h1_count = len(re.findall(r"<h1\b", s))
    if h1_count != 1:
        fail(f"{fn}: H1 count = {h1_count} (must be 1)")


def check_sitemap():
    sm = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    if not urls:
        fail("sitemap.xml has no <loc> entries")
    for url in urls:
        slug = url.replace("https://leavepeo.com", "").strip("/")
        target = "index.html" if not slug else slug + ".html"
        if not (ROOT / target).exists():
            fail(f"sitemap.xml: {url} -> {target} does not exist")
        if url.endswith(".html"):
            fail(f"sitemap.xml: URL has .html extension: {url}")

    # Every public HTML file should be in the sitemap
    public = sorted(p.name for p in ROOT.glob("*.html") if p.name not in {"404.html"})
    sitemap_slugs = set()
    for url in urls:
        slug = url.replace("https://leavepeo.com", "").strip("/")
        sitemap_slugs.add("index.html" if not slug else slug + ".html")
    missing = [f for f in public if f not in sitemap_slugs]
    if missing:
        fail(f"sitemap.xml missing pages: {missing}")


def check_redirects():
    rd = (ROOT / "_redirects").read_text(encoding="utf-8")
    public = sorted(
        p.name for p in ROOT.glob("*.html")
        if p.name not in {"404.html", "index.html"}
    )
    for f in public:
        slug = f.replace(".html", "")
        if not re.search(r"^/" + re.escape(slug) + r"\b", rd, re.MULTILINE):
            fail(f"_redirects missing entry for /{slug}")
    if "/*" not in rd:
        fail("_redirects missing catch-all 404")


def check_blog_index():
    blog = (ROOT / "blog.html").read_text(encoding="utf-8")
    # Expect a card linking to every blog file
    blog_files = sorted(
        p.name for p in ROOT.glob("blog-*.html")
    ) + ["peo-invoice-audit.html"]
    for f in blog_files:
        slug = f.replace(".html", "")
        # Card hrefs may be /slug or https://leavepeo.com/slug or, historically, /blog/peo-invoice-audit
        patterns = [f'href="/{slug}"', f'href="https://leavepeo.com/{slug}"']
        if slug == "peo-invoice-audit":
            patterns.extend(["/blog/peo-invoice-audit"])
        if not any(p in blog for p in patterns):
            fail(f"blog.html missing card linking to {slug}")


def main():
    html_files = sorted(ROOT.glob("*.html"))
    if not html_files:
        fail("No HTML files found in repo root")
        return _exit()

    for p in html_files:
        check_file(p)

    check_sitemap()
    check_redirects()
    check_blog_index()

    return _exit()


def _exit():
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
        print()

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"OK: {len(list(ROOT.glob('*.html')))} HTML files validated.")
    sys.exit(0)


if __name__ == "__main__":
    main()
