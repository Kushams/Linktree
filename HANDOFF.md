# HANDOFF — Europe music leads (Linktree repo)

## What this is
Outreach lead research for a **UK art gallery exhibition**: Europe-based DJs, producers, musicians and artists who could travel to the UK to perform. Owner: Manuchim. Results live in this repo (`Kushams/Linktree`).

## Rules (do not break)
- Europe-based artists ONLY.
- Each lead: artist name or full name + a **publicly published** email. Never guess or construct an email. No emails from third-party aggregator/scraper sites.
- Record the exact source page where the email is visible, plus role, city, country, and genre if published.
- Dedupe by lowercased email and by artist name.
- Do NOT copy phone numbers into this repo, even when a source page shows one.
- Instagram and SoundCloud accounts used for sourcing are **read/research only** — no DMs, follows, likes, comments, posts, or any engagement. No outreach is sent from this research.
- Never commit any password or credential. The SoundCloud login lives only in the owner's Secure Vault.

## Status (2026-11-13)
- Wave 1 + 1B (search-index pass) DONE: 88 queries, **2 verified leads** — see `leads.md` / `leads.json`.
- Search-index limits found: no results returned for any `site:linktr.ee` or `site:soundcloud.com` query; Linktree pages cannot be verified from fetched text. Linktree therefore needs a **live-browser pass**.
- Live-browser Linktree pass RUNNING (Paris, Berlin, London test batch, then Amsterdam, Barcelona, Madrid, Milan; public SoundCloud profile checks included, no login).
- SoundCloud login test: the saved password was **rejected** ("password is incorrect"). A passwordless sign-in attempt was requested by the owner and is in progress; if it needs an emailed link/code, that inbox is not accessible to the agent, so the owner may need to complete that step.
- Next after the live-browser pass: merge + dedupe its leads into `leads.json` / `leads.md`, update this file, commit and push, and report the commit hash. Never claim a save unless the push succeeded.
