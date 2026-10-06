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
    try:
        c.execute("ALTER TABLE leads ADD COLUMN batch INTEGER")
    except sqlite3.OperationalError:
        pass
    return c


def load_seen():
    return set(SEEN.read_text().split()) if SEEN.exists() else set()


def save_seen(names):
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text("\n".join(sorted(names | load_seen())) + "\n")


def git(*args):
    return subprocess.run(["git", "-C", str(SEEN.parent), *args], capture_output=True, text=True)


_ROBOTS = {}


def robots_ok(url):
    """Honour robots.txt for the host (unreachable robots.txt = allowed)."""
    from urllib.robotparser import RobotFileParser
    pu = urlparse(url)
    host = f"{pu.scheme}://{pu.netloc}"
    if host not in _ROBOTS:
        rp = RobotFileParser()
        try:
            req = urllib.request.Request(host + "/robots.txt", headers={"User-Agent": UA})
            rp.parse(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace").splitlines())
        except Exception:
            rp.parse([])
        _ROBOTS[host] = rp
    return _ROBOTS[host].can_fetch(UA, url)


def fetch(url):
    if not robots_ok(url):
        raise PermissionError(f"blocked by robots.txt: {url}")
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
    phones = {p for p in phones if len(re.sub(r"\D", "", p)) >= 8}
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


COLS = "username name country emails phones socials bio source_url status first_seen".split()


def cmd_batch(a):
    """Write full batches of --size email leads (Europe/unknown country) not yet exported."""
    c = db()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    n = (c.execute("SELECT COALESCE(MAX(batch),0) FROM leads").fetchone()[0])
    made = 0
    while True:
        rows = c.execute(f"SELECT {','.join(COLS)} FROM leads WHERE batch IS NULL AND emails!='' "
                         "ORDER BY first_seen LIMIT ?", (a.size,)).fetchall()
        if len(rows) < a.size and not (a.flush and rows and not made):
            break
        n += 1; made += 1
        path = out / f"batch_{n:03d}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(COLS); w.writerows(rows)
        c.executemany("UPDATE leads SET batch=? WHERE username=?", [(n, r[0]) for r in rows]); c.commit()
        print(f"wrote {path} ({len(rows)} leads)")
    pend = c.execute("SELECT COUNT(*) FROM leads WHERE batch IS NULL AND emails!=''").fetchone()[0]
    print(f"{made} batch(es) written; {pend} email leads waiting for the next batch of {a.size}")


# ---------------------------------------------------------------- Mixcloud crawler
EU_NAMES = {"Albania": "AL", "Austria": "AT", "Belarus": "BY", "Belgium": "BE", "Bosnia and Herzegovina": "BA",
            "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY", "Czech Republic": "CZ", "Czechia": "CZ", "Denmark": "DK",
            "Estonia": "EE", "Finland": "FI", "France": "FR", "Germany": "DE", "Greece": "GR", "Hungary": "HU",
            "Iceland": "IS", "Ireland": "IE", "Italy": "IT", "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU",
            "Malta": "MT", "Moldova": "MD", "Montenegro": "ME", "Netherlands": "NL", "North Macedonia": "MK",
            "Norway": "NO", "Poland": "PL", "Portugal": "PT", "Romania": "RO", "Serbia": "RS", "Slovakia": "SK",
            "Slovenia": "SI", "Spain": "ES", "Sweden": "SE", "Switzerland": "CH", "Ukraine": "UA",
            "United Kingdom": "GB", "Kosovo": "XK"}
GENRES = ["techno", "house", "deep house", "tech house", "minimal", "trance", "drum and bass", "jungle", "dubstep",
          "garage", "breaks", "ambient", "electro", "disco", "hip hop", "afrobeats", "jazz", "funk soul", "reggae dub",
          "hard techno", "melodic techno", "dj set", "producer", "live act", "radio show", "vinyl"]
CITIES = ["Berlin", "London", "Amsterdam", "Paris", "Madrid", "Barcelona", "Lisbon", "Rome", "Milan", "Warsaw",
          "Prague", "Vienna", "Brussels", "Stockholm", "Copenhagen", "Dublin", "Manchester", "Glasgow", "Hamburg",
          "Munich", "Cologne", "Frankfurt", "Leipzig", "Rotterdam", "Budapest", "Athens", "Helsinki", "Oslo", "Zurich",
          "Bristol", "Leeds", "Ibiza", "Porto", "Lyon", "Marseille", "Belgrade", "Zagreb", "Bucharest", "Sofia", "Riga"]
MXDONE = SEEN.with_name("mixcloud_queries_done.txt")


POS_RE = re.compile(r"(?<![a-z])(dj|d\.j\.|producer|musician|composer|band|singer|songwriter|rapper|mc|vocalist|"
                    r"beatmaker|guitarist|pianist|drummer|violinist|live act|live performer|artist|selector)(?![a-z])", re.I)
NEG_RE = re.compile(r"ticket|agency|agentur|promotion|booking (platform|service)|plateforme|platform|marketplace|"
                    r"festival|venue|radio station|community radio|\bstore\b|\bshop\b|rental|courses?\b|\bschool\b|"
                    r"lessons|equipment|wedding (planner|service)|\bnetwork\b|\bpromo\b", re.I)


def is_artist(name, bio):
    """Heuristic: performer wording present and no agency/shop/venue wording."""
    text = f"{name or ''} {bio or ''}"
    return bool(POS_RE.search(text) or re.search(r"(?<![a-z])dj", (name or "").lower())) and not NEG_RE.search(text)


MX_RESERVED = {"signup", "login", "premium", "genres", "trending", "community", "plans", "developers", "discover",
               "search", "live", "upload", "about", "pro", "jobs", "terms", "privacy", "tag", "popular", "help",
               "settings", "notifications", "dashboard", "select", "go-pro", "creators", "blog", "press", "contact"}


def mx_users(q, page):
    import urllib.parse
    h = fetch("https://www.mixcloud.com/search/?" + urllib.parse.urlencode(
        {"mixcloud_query": q, "type": "user", "page": page}))
    return [u for u in dict.fromkeys(re.findall(r'href="/([A-Za-z0-9_\-]+)/"', h)) if u.lower() not in MX_RESERVED]


def mx_profile(user):
    h = fetch(f"https://www.mixcloud.com/{user}/")
    t = re.search(r"<title>(.*?)</title>", h, re.S)
    name = re.sub(r"\s*\|\s*Mixcloud\s*$", "", t.group(1)).strip() if t else user
    m = re.search(r'"description":"((?:[^"\\]|\\.)*)"', h)
    try:
        bio = json.loads('"' + m.group(1) + '"') if m else ""
    except Exception:
        bio = m.group(1) if m else ""
    c = re.search(r"<!-- -->, <!-- -->([^<>]+)</p>", h)
    return dict(name=name, bio=bio.replace("\n", " "), country=(c.group(1).strip() if c else ""),
                url=f"https://www.mixcloud.com/{user}/")


def cmd_mixcloud(a):
    """Discover Mixcloud artists via www.mixcloud.com search pages (allowed by robots.txt)."""
    import random
    c = db()
    if a.git_sync:
        git("pull", "--rebase", "--autostash")
    ledger = load_seen()
    done = set(MXDONE.read_text().splitlines()) if MXDONE.exists() else set()
    queries = [f"{g} {ci}" for ci in CITIES for g in GENRES] + GENRES
    random.Random(7).shuffle(queries)
    queries = [q for q in queries if q not in done][: a.queries]
    sup = {r[0] for r in c.execute("SELECT email FROM suppressed")}
    new_names, saved, checked = set(), 0, 0
    for q in queries:
        for page in range(1, a.pages + 1):
            try:
                users = mx_users(q, page)
            except Exception as e:
                print(f"search {q!r}: {e}", file=sys.stderr); break
            if not users:
                break
            for user in users:
                key = "mixcloud:" + user.lower()
                if key in ledger or key in new_names:
                    continue
                time.sleep(a.delay)
                try:
                    p = mx_profile(user)
                except Exception as e:
                    print(f"{user}: {e}", file=sys.stderr); continue
                checked += 1; new_names.add(key)
                iso = EU_NAMES.get(p["country"], "")
                if not iso:
                    continue
                emails = sorted({e.lower() for e in EMAIL_RE.findall(p["bio"])
                                 if not e.lower().endswith(BAD_EMAIL_SUFFIX) and "mixcloud.com" not in e.lower()} - sup)
                if not emails or not is_artist(p["name"], p["bio"]):
                    continue
                phones = sorted({re.sub(r"[^\d+]", "", x) for x in PHONE_RE.findall(p["bio"])})
                links = sorted(set(re.findall(r"linktr\.ee/[\w.]+", p["bio"])))  # recorded only; linktr.ee disallows crawlers
                c.execute("INSERT OR REPLACE INTO leads(username,name,bio,country,source_url,emails,phones,socials,first_seen,last_seen,status)"
                          " VALUES(?,?,?,?,?,?,?,?,COALESCE((SELECT first_seen FROM leads WHERE username=?),?),?,"
                          "COALESCE((SELECT status FROM leads WHERE username=?),'new'))",
                          (key, p["name"], p["bio"][:300], iso, p["url"], ";".join(emails), ";".join(phones),
                           ";".join([p["url"]] + ["https://" + l for l in links]), key, now(), now(), key))
                c.commit(); saved += 1
                print(f"{key:34} {iso} {emails[0]}  | {p['bio'][:50]}")
        done.add(q)
        MXDONE.parent.mkdir(exist_ok=True); MXDONE.write_text("\n".join(sorted(done)) + "\n")
        save_seen(new_names)
    if a.git_sync:
        git("add", "data"); git("commit", "-m", f"Mixcloud run: +{len(new_names)} handles")
        r = git("push"); print("pushed" if r.returncode == 0 else f"push failed: {r.stderr.strip()}")
    print(f"mixcloud: {len(queries)} queries, {checked} profiles checked, {saved} artist leads with email saved")


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
    x = s.add_parser("batch"); x.add_argument("outdir"); x.add_argument("--size", type=int, default=500)
    x.add_argument("--flush", action="store_true", help="also write a partial batch"); x.set_defaults(f=cmd_batch)
    x = s.add_parser("mixcloud"); x.add_argument("--queries", type=int, default=20); x.add_argument("--pages", type=int, default=2)
    x.add_argument("--delay", type=float, default=0.4); x.add_argument("--europe-only", action="store_true", default=True)
    x.add_argument("--git-sync", action="store_true");
    x.set_defaults(f=cmd_mixcloud)
    x = s.add_parser("mark"); x.add_argument("email"); x.add_argument("status", choices=["new", "contacted", "replied", "declined", "do_not_contact"]); x.set_defaults(f=cmd_mark)
    a = p.parse_args(); a.f(a)
