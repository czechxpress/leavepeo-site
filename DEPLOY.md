# Deploy and automation guide

This document is the operating manual for the leavepeo-site repo. It covers the one-time setup, the day-to-day push flow, and how Claude pushes for you in future sessions without exposing your token in chat.

## What this gives you

1. A GitHub repo with a clean commit history
2. A CI workflow that runs on every push and blocks any commit that breaks the rules from the audit (em dashes in titles, missing GA, broken sitemap, etc.)
3. Netlify auto-deploys to leavepeo.com on every successful push to main
4. A documented way for Claude to push directly using a scoped, short-lived token that never lives in chat

## One-time setup

Do these steps on your laptop today. They take about ten minutes.

### Step 1: Create the GitHub repo

1. Open https://github.com/new
2. Repository name: `leavepeo-site`
3. Owner: your account
4. Visibility: Private (recommended)
5. Do NOT check "Add a README", "Add .gitignore", or "Choose a license". This repo already has its own commit history.
6. Click "Create repository"
7. Copy the SSH URL it gives you, looks like `git@github.com:YOUR_USER/leavepeo-site.git`

### Step 2: Generate a fine-grained Personal Access Token

This is the key security step. Use a fine-grained PAT, not a classic one. Fine-grained tokens can be locked to one repo with one permission, which limits the blast radius if anything goes wrong.

1. Open https://github.com/settings/personal-access-tokens/new
2. Token name: `leavepeo-deploy-claude`
3. Expiration: 90 days (the maximum for a low-friction rotation cadence)
4. Description: `Used by Claude Cowork mode for automated deploys to leavepeo-site`
5. Repository access: "Only select repositories" -> pick `leavepeo-site`
6. Permissions -> Repository permissions:
   - Contents: Read and write
   - Metadata: Read-only (auto-selected)
   - Pull requests: Read and write (only if you want me to open PRs instead of pushing direct)
   - Everything else: leave at "No access"
7. Click "Generate token"
8. Copy the token immediately. GitHub only shows it once.

### Step 3: Save the token in a file (NOT in chat)

Create a plain text file on your computer at a path you'll remember. The token file should NOT be inside the leavepeo-site repo folder, and should NOT be tracked by git.

Suggested path on Windows:
```
C:\Users\Sustr\.secrets\leavepeo-gh-token
```

Suggested path on Mac/Linux:
```
~/.secrets/leavepeo-gh-token
```

The file contents should be just the token, no quotes, no extra whitespace, e.g.:
```
github_pat_11ABCD...VeryLongString...EndsHere
```

Set restrictive permissions on Mac/Linux:
```bash
mkdir -p ~/.secrets
chmod 700 ~/.secrets
chmod 600 ~/.secrets/leavepeo-gh-token
```

### Step 4: Push the initial commit

Unzip the latest delivered archive (`leavepeo-site-updated-with-git.zip`) somewhere convenient, then from inside the `leavepeo` folder it creates:

```bash
cd /path/to/leavepeo
git remote add origin git@github.com:YOUR_USER/leavepeo-site.git
git push -u origin main
```

Or if you prefer HTTPS with the token:
```bash
cd /path/to/leavepeo
TOKEN=$(cat ~/.secrets/leavepeo-gh-token)
git remote add origin https://x-access-token:${TOKEN}@github.com/YOUR_USER/leavepeo-site.git
git push -u origin main
```

After this, check the Actions tab on GitHub. The "Validate site" workflow should run and pass.

### Step 5: Connect Netlify (if you haven't already)

1. https://app.netlify.com -> Sites -> "Add new site" -> "Import an existing project"
2. Connect to GitHub, pick `leavepeo-site`
3. Branch: `main`. Publish directory: `.` (root). Build command: leave blank.
4. Deploy. After it succeeds, set your custom domain `leavepeo.com` in Site settings -> Domain management.

Netlify will now auto-deploy on every push to main.

## How Claude pushes for you in future sessions

When you start a new Cowork session and want me to push, do this:

1. Copy your token file into the workspace folder Cowork is connected to. Pick a name that's gitignored, like `.gh_token` or `.secrets/gh_token`. The path needs to be inside the workspace I can read.
2. In the chat, tell me: "the token is in `.gh_token`"
3. I will push using a method that never prints the token contents into chat or logs. Specifically, I'll use git's credential helper or `git push https://x-access-token:$(cat .gh_token)@github.com/...` where the shell substitution happens before the token reaches my output.

What I will NOT do:
- Print the token into chat or logs
- Echo the token contents
- Commit the token file to the repo (it'll be in .gitignore)

The .gitignore in this repo already excludes `.gh_token`, `.secrets/`, and `*.token`.

## Token rotation

Every 90 days when GitHub expires the token:
1. Repeat Step 2 above (generate new token)
2. Replace the contents of your token file
3. That's it. Nothing else changes.

If the token ever leaks (e.g. accidentally pasted somewhere it shouldn't have been), revoke it immediately at https://github.com/settings/personal-access-tokens and generate a new one. Revocation takes effect within seconds.

## What CI catches (and why)

The validator at `scripts/validate_site.py` runs on every push and fails the build if:

- Any HTML file is missing closing tags or has more than one DOCTYPE (catches the duplicate-document bug)
- Any HTML file is missing the GA ID `G-F51MZYJYMK`, or has the placeholder `G-XXXXXXXXXX`, or fires GA more than once
- Any title tag contains an em dash (your style rule)
- Any canonical tag is missing, has `.html`, or points to a non-leavepeo domain
- The phone number 303-570-7309 is missing from any page
- Any `target="_blank"` link is missing `rel="noopener"`
- Any HTML file has more than one H1
- The sitemap references a URL that doesn't have a matching file
- Any HTML file is missing from the sitemap
- Any blog file is missing a card on /blog
- `_redirects` is missing a pretty-URL entry for any HTML page
- `_redirects` is missing the catch-all 404

When CI fails, Netlify still deploys (because Netlify and GitHub Actions are independent). To make CI gate the deploy, add a Netlify build plugin or use the "Deploy via GitHub Actions" option in Netlify. For now, the workflow runs in parallel and you'll see a red X on the commit if anything breaks.

## What CI does NOT catch (yet)

- Copy quality, tone, or factual accuracy
- Whether the savings numbers match across pages
- Image optimization (no images on the site currently)
- Lighthouse performance scores
- Accessibility violations beyond what HTML tidy reports

These are review-by-human jobs. The split between auto-pushable and review-required content stays intentional: plumbing is auto, copy is human.

## Files in this repo

- `scripts/validate_site.py` - the validator. Run locally with `python3 scripts/validate_site.py`
- `.github/workflows/validate.yml` - GitHub Actions config that runs the validator
- `.github/workflows/deploy-trigger.yml` - notes on Netlify deploy hook (no active workflow)
- `_redirects` - Netlify pretty-URL rules
- `netlify.toml` - Netlify build config (publish dir only)
- `sitemap.xml` - 28 URLs, regenerate when adding new pages
- `robots.txt` - basic, allows all
