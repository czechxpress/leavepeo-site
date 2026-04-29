#!/usr/bin/env python3
"""
Brand palette migration: main palette -> refined alt palette + navy CTAs.
Idempotent: safe to re-run.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# Files to migrate from main palette
MAIN_PALETTE_FILES = [
    'about.html', 'blog-peo-ertc-fine-print.html', 'contact.html', 'faq.html',
    'index.html',
    'exit-adp-totalsource.html', 'exit-coadvantage.html', 'exit-engage.html',
    'exit-extensishr.html', 'exit-ga-partners.html', 'exit-insperity.html',
    'exit-justworks.html', 'exit-paychex.html', 'exit-rippling.html',
    'exit-trinet.html',
]

# Alt-palette blog files: add navy CTA variables, update primary buttons only
ALT_PALETTE_FILES = [
    'blog-401k-transition.html', 'blog-cost-of-staying.html',
    'blog-funding-options.html', 'blog-insperity-problems.html',
    'blog-leave-adp-totalsource.html',
    'blog-multi-state-tax-registration-sequence.html',
    'blog-peo-exit-checklist.html', 'blog-peo-tax-credits.html',
    'blog-q4-renewal-trap.html', 'blog-workers-comp-epli.html',
]

# Hex value substitutions for main palette files
# Order matters: longer/more specific patterns first
HEX_SUBS = [
    # Color variables (inside :root and direct usages)
    ('#FAF7F2', '#F5F0EB'),    # cream
    ('#F0EBE3', '#EFE8DB'),    # cream-dark
    ('#E5DFD5', '#DCD5C9'),    # warm-gray
    ('#EDE9E1', '#ECE5D9'),    # warm-gray-light
    ('#2D6A4F', '#5B7B6A'),    # sage
    ('#40916C', '#739987'),    # sage-light
    ('#1A1A2E', '#2C2C2C'),    # charcoal
    ('#2C2C3A', '#2C2C2C'),    # dark-text
    ('#5A5A6E', '#4B5563'),    # mid-text
    ('#8A8A9A', '#6B7280'),    # light-text
    ('#C45B3A', '#B85C3A'),    # rust
    ('#C9982E', '#C9A96E'),    # gold
    ('#B8891F', '#B89A52'),    # gold:hover
    # rgba sage references (for shadows, backgrounds)
    ('rgba(45,106,79,0.06)', 'rgba(91,123,106,0.08)'),
    ('rgba(45,106,79,0.08)', 'rgba(91,123,106,0.10)'),
    ('rgba(45,106,79,0.10)', 'rgba(91,123,106,0.12)'),
    ('rgba(45,106,79,0.15)', 'rgba(91,123,106,0.18)'),
    ('rgba(45,106,79,0.04)', 'rgba(91,123,106,0.06)'),
    ('rgba(45,106,79,0.05)', 'rgba(91,123,106,0.07)'),
    ('rgba(45,106,79,0.12)', 'rgba(91,123,106,0.15)'),
    # rgba gold references
    ('rgba(201,152,46,0.35)', 'rgba(31,45,61,0.25)'),  # btn-primary hover shadow -> navy shadow
    ('rgba(201,152,46,0.04)', 'rgba(201,169,110,0.05)'),
    # Direct cream rgba (for nav backdrop)
    ('rgba(250,247,242,0.92)', 'rgba(245,240,235,0.94)'),
    # Favicon SVG fill colors (URL-encoded)
    ("fill=%27%232D6A4F%27", "fill=%27%235B7B6A%27"),
    ("fill=%27%23FAF7F2%27", "fill=%27%23F5F0EB%27"),
    ("fill=%27%23C9982E%27", "fill=%27%23C9A96E%27"),
]

# Font and Fonts URL changes
FONT_SUBS = [
    ("font-family:'Outfit',sans-serif",
     "font-family:'Inter',-apple-system,sans-serif"),
    ("font-family: 'Outfit', sans-serif",
     "font-family: 'Inter', -apple-system, sans-serif"),
    ("font-family:'Outfit'",
     "font-family:'Inter'"),
    # Google Fonts: replace any Outfit-bearing URL with the Inter version
]

OLD_FONTS_URL_RE = re.compile(
    r'https://fonts\.googleapis\.com/css2\?family=Source\+Serif\+4[^"\']*Outfit[^"\']*display=swap'
)
NEW_FONTS_URL = (
    'https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700;800'
    '&family=Inter:wght@400;500;600;700&display=swap'
)

# Inject these new vars into :root if missing
NEW_VARS = """  --navy: #1F2D3D;
  --navy-hover: #2A3D52;
  --gold-hover: #B89A52;
"""

def add_navy_vars_to_root(s):
    """Find first :root{...} block and inject --navy vars before its closing brace."""
    if '--navy:' in s:
        return s  # already has it
    m = re.search(r'(:root\s*\{)([^}]*)(\})', s, re.DOTALL)
    if not m:
        return s
    head, body, tail = m.group(1), m.group(2), m.group(3)
    # Append before closing brace, preserving indentation
    new_block = head + body.rstrip() + '\n' + NEW_VARS + tail
    return s[:m.start()] + new_block + s[m.end():]


def update_btn_primary_main(s):
    """Update .btn-primary in main-palette files: gold -> navy."""
    # Match .btn-primary { background:var(--gold); color:var(--charcoal); }
    s = re.sub(
        r'\.btn-primary\s*\{\s*background:\s*var\(--gold\)\s*;\s*color:\s*var\(--charcoal\)\s*;\s*\}',
        '.btn-primary { background:var(--navy); color:var(--white); }',
        s
    )
    # Match its hover: .btn-primary:hover { background:#B89A52; transform:translateY(-2px); ... }
    # We already substituted #B8891F -> #B89A52 earlier. Now overwrite the hover bg with var(--navy-hover).
    s = re.sub(
        r'\.btn-primary:hover\s*\{\s*background:\s*#B89A52\s*;',
        '.btn-primary:hover { background:var(--navy-hover);',
        s
    )
    return s


def update_btn_primary_alt(s):
    """For alt-palette files: nav-cta and any --gold primary CTA -> navy."""
    # Common pattern: .nav-cta { background: var(--gold) !important; color: var(--charcoal) !important; ... }
    s = re.sub(
        r'\.nav-cta\s*\{\s*background:\s*var\(--gold\)\s*!important;\s*color:\s*var\(--charcoal\)\s*!important;',
        '.nav-cta { background: var(--navy) !important; color: var(--white) !important;',
        s
    )
    s = re.sub(
        r'\.nav-cta:hover\s*\{\s*background:\s*var\(--gold-hover\)\s*!important;\s*\}',
        '.nav-cta:hover { background: var(--navy-hover) !important; }',
        s
    )
    # mid-cta a (the inline CTA buttons in articles)
    s = re.sub(
        r'(\.mid-cta\s+a\s*\{[^}]*?)background:\s*var\(--gold\);\s*color:\s*var\(--charcoal\);',
        r'\1background: var(--navy); color: var(--white);',
        s
    )
    s = re.sub(
        r'(\.mid-cta\s+a:hover\s*\{[^}]*?)background:\s*var\(--gold-hover\);',
        r'\1background: var(--navy-hover);',
        s
    )
    return s


def migrate_main(fn):
    with open(fn, 'r', encoding='utf-8') as f:
        s = f.read()
    orig = s

    # 1. Hex substitutions sitewide (these are deliberately one-to-one)
    for a, b in HEX_SUBS:
        s = s.replace(a, b)

    # 2. Font family substitutions
    for a, b in FONT_SUBS:
        s = s.replace(a, b)

    # 3. Google Fonts URL
    s = OLD_FONTS_URL_RE.sub(NEW_FONTS_URL, s)

    # 4. Inject navy vars
    s = add_navy_vars_to_root(s)

    # 5. Update .btn-primary
    s = update_btn_primary_main(s)

    if s != orig:
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(s)
        return True
    return False


def migrate_alt(fn):
    with open(fn, 'r', encoding='utf-8') as f:
        s = f.read()
    orig = s

    s = add_navy_vars_to_root(s)
    s = update_btn_primary_alt(s)

    if s != orig:
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(s)
        return True
    return False


def main():
    os.chdir(ROOT)
    main_changed = 0
    for fn in MAIN_PALETTE_FILES:
        path = os.path.join(ROOT, fn)
        if os.path.exists(path):
            if migrate_main(path):
                main_changed += 1
                print(f'  main: {fn}')
    print(f'Main-palette files migrated: {main_changed}/{len(MAIN_PALETTE_FILES)}')

    alt_changed = 0
    for fn in ALT_PALETTE_FILES:
        path = os.path.join(ROOT, fn)
        if os.path.exists(path):
            if migrate_alt(path):
                alt_changed += 1
                print(f'  alt: {fn}')
    print(f'Alt-palette files updated: {alt_changed}/{len(ALT_PALETTE_FILES)}')


if __name__ == '__main__':
    main()
