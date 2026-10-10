# Rules for this repo (DJ / artist contact lists)

These are standing rules for any work on the email lists. Follow them every time.

1. **Artists only.** Every person on the list must be a music-maker: DJ, musician, producer, singer, band.
   Never include record labels, agencies, managers, venues, clubs, radio stations, media/blogs, event brands,
   shops, or comedians/other non-music people. Removed entries are recorded in `removed_non_artists.csv`.
2. **Always audit.** After any add or change, audit the whole list: check every profile's bio/Linktree
   links to confirm the person is an artist. Open the profile when the bio is unclear. Remove anyone who fails.
3. **Emails are the deliverable**, not the Linktree links. `dj_emails_only.csv` is the main file.
4. **One row per artist, personal email first.** If an artist has several emails, the main `email` is their
   personal one; if none, use the next best (own-domain contact, own booking, promo, management, agency, label).
   Every email carries an `email_type` label, and extras go in `other_emails` with their labels.
5. **Commit everything** (CSVs, scripts, raw data, source files) to GitHub so nothing is lost.
   Work on branch `dj-email-lists` / open PR; keep it pushed.

Pipeline: `scripts/` (extract -> scrape -> pass2 websites -> pass3 SoundCloud/YouTube/TikTok -> batch2 -> classify_emails).

6. **Uploaded CSVs are untouchable.** Profiles that came from the user's uploaded exports (data/source_*.csv) are always kept.
   Only profiles found through my own web searches get pruned when the user asks for a country (e.g. France only).
   Pruned entries go in `removed_not_european.csv` (scope was widened from France-only to Europe); unconfirmed country counts as not matching.

7. **Check before removing.** Before dropping an artist for an unclear country, dig through all their linked pages
   (`scripts/locate.py`: SoundCloud/Mixcloud/Bandcamp/RA/own site). Instagram can't be read automatically.

8. **Final deliverable = `dj_emails_europe.csv`**: European artists only, from ALL sources (uploads + searches). Confirmed non-European
   artists go to `excluded_non_european.csv`. Artists with unknown country stay in, labelled `unknown (not confirmed)`.
   `dj_emails_only.csv` remains the full master list.
