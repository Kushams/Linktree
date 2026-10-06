#!/usr/bin/env python3
"""Collect publicly listed booking contacts from Linktree pages.

Usage:
  python leads.py scrape seeds.txt [--europe-only] [--delay 3]
  python leads.py export leads.csv [--status new] [--with-email]
  python leads.py mark someone@example.com contacted|replied|declined|do_not_contact

Stdlib only. State lives in leads.db so repeat runs only add/refresh.
"""
import argparse, csv, json, re, sqlite3, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

DB = Path(__file__).with_name("leads.db")
# Committed to git so every agent/machine shares it. Handles only - no contact details.
SEEN = Path(__file__).resolve().parent.parent / "data" / "seen.txt"
UA = "GalleryOutreachBot/1.0 (+contact: set-your-email-here)"
EUROPE = set("""AL AD AT BY BE BA BG HR CY CZ DK EE FI FR DE GR HU IS IE IT XK LV LI LT LU MT
MD MC ME NL MK NO PL PT RO SM RS SK SI ES SE CH UA GB VA""".split())
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)\+\d[\d\s().\-]{7,16}\d")
NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
SOCIALS = ("instagram.com", "soundcloud.com", "spotify.com", "bandcamp.com",
           "ra.co", "residentadvisor.net", "mixcloud.com", "youtube.com", "tiktok.com")
BAD_EMAIL_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp")
now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")


def db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS leads(
      username TEXT PRIMARY KEY, name TEXT, bio TEXT, country TEXT, source_url TEXT,
      emails TEXT, phones TEXT, socials TEXT, first_seen TEXT, last_seen TEXT,
      status TEXT DEFAULT 'new');
    CREATE TABLE IF NOT EXISTS suppressed(email TEXT PRIMARY KEY, added TEXT);
    """)
    return c


def load_seen():
    return set(SEEN.read_text().split()) if SEEN.exists() else set()


def save_seen(names):
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text("\n".join(sorted(names | load_seen())) + "\n")


def git(*args):
    return subprocess.run(["git", "-C", str(SEEN.parent), *args], capture_output=True, text=True)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def norm_url(s):
    s = s.strip()
    if not s or s.startswith("#"):
        return None
    if "linktr.ee" not in s:
        s = f"https://linktr.ee/{s.lstrip('@/')}"
    p = urlparse(s if "://" in s else "https://" + s)
    user = p.path.strip("/").split("/")[0]
    return f"https://linktr.ee/{user}" if user else None


def parse(html, url):
    m = NEXT_RE.search(html)
    if not m:
        return None
    pp = json.loads(m.group(1))["props"]["pageProps"]
    acct = pp.get("account") or {}
    links = [l for l in (pp.get("links") or []) + (pp.get("socialLinks") or []) if l]
    hrefs = [l.get("url") or "" for l in links]
    texts = [pp.get("description") or "", pp.get("pageTitle") or ""] + [l.get("title") or "" for l in links]
    emails, phones, socials = set(), set(), {}
    for h in hrefs:
        if h.lower().startswith("mailto:"):
            emails.update(EMAIL_RE.findall(unquote(h[7:])))
        elif h.lower().startswith("tel:"):
            phones.add(re.sub(r"[^\d+]", "", unquote(h[4:])))
        elif "wa.me/" in h:
            phones.add("+" + re.sub(r"\D", "", h.split("wa.me/")[1]))
        elif any(s in urlparse(h).netloc for s in SOCIALS):
            socials.setdefault(next(k for k in SOCIALS if k in urlparse(h).netloc), h)
    for t in texts:
        emails.update(EMAIL_RE.findall(t))
        phones.update(re.sub(r"[^\d+]", "", p) for p in PHONE_RE.findall(t))
    emails = {e.lower() for e in emails if not e.lower().endswith(BAD_EMAIL_SUFFIX)}
    return dict(username=pp.get("username") or acct.get("username"), name=pp.get("pageTitle"),
                bio=(pp.get("description") or "").replace("\n", " "), country=(acct.get("country") or "").upper(),
                source_url=url, emails=sorted(emails), phones=sorted(phones), socials=sorted(socials.values()))


def cmd_scrape(a):
    c = db()
    if a.git_sync:
        git("pull", "--rebase", "--autostash")
    ledger = load_seen()
    urls = [u for u in (norm_url(l) for l in Path(a.seeds).read_text().splitlines()) if u]
    todo = [u for u in dict.fromkeys(urls) if a.refresh or u.rsplit("/", 1)[1].lower() not in ledger]
    print(f"{len(urls) - len(todo)} already scraped (skipped), {len(todo)} to fetch")
    seen = skipped = 0
    new_names = set()
    for i, u in enumerate(todo):
        if i:
            time.sleep(a.delay)
        try:
            d = parse(fetch(u), u)
        except urllib.error.HTTPError as e:
            print(f"{u}: HTTP {e.code}", file=sys.stderr)
            if e.code == 429:
                print("rate limited - stopping; raise --delay", file=sys.stderr); break
            continue
        except Exception as e:
            print(f"{u}: {e}", file=sys.stderr); continue
        if not d or not d["username"]:
            continue
        if a.europe_only and d["country"] and d["country"] not in EUROPE:
            skipped += 1; new_names.add(u.rsplit("/", 1)[1].lower()); continue
        sup = {r[0] for r in c.execute("SELECT email FROM suppressed")}
        d["emails"] = [e for e in d["emails"] if e not in sup]
        row = c.execute("SELECT 1 FROM leads WHERE username=?", (d["username"],)).fetchone()
        vals = (d["name"], d["bio"], d["country"], u, ";".join(d["emails"]), ";".join(d["phones"]),
                ";".join(d["socials"]), now())
        if row:
            c.execute("UPDATE leads SET name=?,bio=?,country=?,source_url=?,emails=?,phones=?,socials=?,last_seen=? WHERE username=?",
                      vals + (d["username"],))
        else:
            c.execute("INSERT INTO leads(name,bio,country,source_url,emails,phones,socials,last_seen,username,first_seen) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      vals + (d["username"], now()))
        c.commit(); seen += 1
        new_names.add(u.rsplit("/", 1)[1].lower())
        print(f"{d['username']:30} {d['country'] or '--':3} emails={len(d['emails'])} phones={len(d['phones'])}")
    save_seen(new_names)
    if a.git_sync and new_names:
        git("add", str(SEEN)); git("commit", "-m", f"Ledger: +{len(new_names)} scraped handles")
        r = git("push"); print("ledger pushed" if r.returncode == 0 else f"push failed: {r.stderr.strip()}")
    print(f"done: {seen} saved, {skipped} skipped (non-Europe)")


def cmd_export(a):
    q, args = "SELECT username,name,country,emails,phones,socials,bio,source_url,status,first_seen FROM leads WHERE 1=1", []
    if a.status:
        q += " AND status=?"; args.append(a.status)
    if a.with_email:
        q += " AND emails!=''"
    rows = db().execute(q, args).fetchall()
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow("username name country emails phones socials bio source_url status first_seen".split())
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {a.out}")


def cmd_mark(a):
    c = db()
    c.execute("UPDATE leads SET status=? WHERE ';'||emails||';' LIKE ?", (a.status, f"%;{a.email.lower()};%"))
    if a.status == "do_not_contact":
        c.execute("INSERT OR IGNORE INTO suppressed VALUES(?,?)", (a.email.lower(), now()))
    c.commit(); print("ok")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); s = p.add_subparsers(required=True)
    x = s.add_parser("scrape"); x.add_argument("seeds"); x.add_argument("--europe-only", action="store_true")
    x.add_argument("--delay", type=float, default=3.0)
    x.add_argument("--refresh", action="store_true", help="re-scrape handles already in the ledger")
    x.add_argument("--git-sync", action="store_true", help="pull ledger first, commit+push it after"); x.set_defaults(f=cmd_scrape)
    x = s.add_parser("export"); x.add_argument("out"); x.add_argument("--status"); x.add_argument("--with-email", action="store_true"); x.set_defaults(f=cmd_export)
    x = s.add_parser("mark"); x.add_argument("email"); x.add_argument("status", choices=["new", "contacted", "replied", "declined", "do_not_contact"]); x.set_defaults(f=cmd_mark)
    a = p.parse_args(); a.f(a)
