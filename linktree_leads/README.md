# Linktree lead collector (gallery artist outreach)

Reads **public** Linktree pages and saves name, bio, country, listed emails/phones and
social links into a local SQLite DB (`leads.db`). Re-running only adds new artists and
refreshes existing ones, so it works as a recurring job.

```bash
# 1. put Linktree URLs or bare usernames in seeds.txt (one per line)
python3 linktree_leads/leads.py scrape seeds.txt --europe-only --delay 3
# 2. export people who list an email, not yet contacted
python3 linktree_leads/leads.py export outreach.csv --with-email --status new
# 3. record outcomes; do_not_contact permanently suppresses that address
python3 linktree_leads/leads.py mark dj@example.com contacted
python3 linktree_leads/leads.py mark dj@example.com do_not_contact
```

`--europe-only` uses the country the artist set on their Linktree. Pages with no country
are kept (flagged blank) so you can review them by hand.

## Finding Linktree URLs (the seed list)
Linktree has no public directory, so seeds come from elsewhere:
- Artist line-ups on Resident Advisor, Bandcamp, SoundCloud, Mixcloud, festival/club pages
- Instagram/TikTok bios of artists you already follow (the link in bio is usually a Linktree)
- Search: `site:linktr.ee DJ Berlin booking`, `site:linktr.ee producer Amsterdam` etc., per city/genre
- Your own gallery's existing artist contacts

## Compliance - please read before emailing at scale
- **GDPR / ePrivacy (EU/UK):** an email on a public page is still personal data. Contacting
  individual artists about a paid performance is typically defensible as B2B "legitimate
  interest", but you must: say who you are and where you got their address, make opt-out
  trivial and honour it (`do_not_contact`), keep only what you need, and delete on request.
  Some countries (e.g. Germany, Italy) are stricter on unsolicited email; a short personal
  message beats a mass blast. Get advice from someone who knows your jurisdiction.
- **Linktree ToS** restricts automated scraping. This tool is polite (identifying user agent,
  delay between requests, stops on HTTP 429) and is meant for modest batches, not bulk harvesting.
  Set a real contact address in `UA` at the top of `leads.py`.
- Prefer addresses artists list for **booking/management**. Don't scrape private/gated pages.
- `leads.db` and CSVs are git-ignored - they contain personal data.

## Shared "already scraped" ledger (multi-agent)
`data/seen.txt` is a sorted list of Linktree handles that have been scraped. It is committed,
so any agent/machine that pulls the repo skips them *before* fetching (no wasted requests, no
duplicate outreach). `.gitattributes` uses a union merge so parallel agents adding lines don't conflict.

`scrape --git-sync` pulls the ledger first and commits+pushes it afterwards. Use `--refresh` to re-scrape.

**Only handles are committed.** Emails/phones live in the git-ignored `leads.db`/CSVs. This repo is
public - never commit contact details here. If you want contact data shared across agents, make the
repo private first or use a private store (Supabase/Drive).
