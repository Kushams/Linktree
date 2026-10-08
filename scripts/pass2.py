import json, re, urllib.parse, urllib.request, concurrent.futures as cf
res=json.load(open('linktree_results.json'))
noem=[u for u,n,e,l in res if e is not None and not e]
skip=re.compile(r'(instagram|facebook|fb\.com|tiktok|youtube|youtu\.be|spotify|soundcloud|twitter|x\.com|bandcamp|apple\.com|deezer|beatport|mixcloud|linktr\.ee|ra\.co|residentadvisor|snapchat|twitch|discord|threads\.net|amazon|tidal|shazam|vimeo|patreon|paypal|wa\.me|whatsapp|t\.me|telegram|google\.com|nts\.live|hearthis|traxsource|juno|discogs|rinse\.fm|boilerroom|dice\.fm|wikipedia|pinterest|linkedin|bsky|ticketmaster|eventbrite|shotgun|weezevent|billetweb|songkick|bandsintown|ko-fi|buymeacoffee|sjv\.io|linksynergy|tinyurl|bit\.ly|lnk\.to|ffm\.to|smarturl|onerpm|distrokid|hypeddit|toneden|open\.spotify|music\.apple|genius|last\.fm|kick\.com|rumble|goo\.gl|spoti\.fi|orcd\.co|fanlink|song\.link|hoo\.be)',re.I)
epat=re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')
bad=re.compile(r'\.(png|jpe?g|gif|webp|svg|css|js|woff2?)$|sentry|wixpress|example\.|domain\.com|@2x|@3x|noreply|no-reply|yourname|email@|your@|user@|name@|test@|godaddy|cloudflare|schema\.org',re.I)
def fetch(u,t=20):
    try:
        req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
        r=urllib.request.urlopen(req,timeout=t)
        if 'html' not in (r.headers.get('Content-Type') or 'html'): return None
        return r.read(1_500_000).decode('utf-8','replace')
    except Exception: return None
def emails(h):
    h=urllib.parse.unquote(h.replace('&#64;','@').replace('&commat;','@').replace('[at]','@').replace('\\n',' '))
    return {m.strip('.').lower() for m in epat.findall(h) if not bad.search(m)}
def profile_links(u):
    h=fetch(u,30)
    if not h: return []
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',h,re.S)
    if not m: return []
    d=json.loads(m.group(1)); pp=d['props']['pageProps']
    urls=[x.get('url') for x in pp.get('links',[]) if x.get('url')]
    urls+=[x.get('url') for x in pp.get('socialLinks',[]) if x.get('url')]
    return [x for x in dict.fromkeys(urls) if x.startswith('http') and not skip.search(x)]
def site_emails(url):
    found=set(); h=fetch(url)
    if not h: return found
    found|=emails(h)
    if not found:
        base=url
        cands=set(urllib.parse.urljoin(base,p) for p in ['/contact','/contact-us','/booking','/bookings','/about'])
        for href in re.findall(r'href=["\']([^"\']+)["\']',h):
            if re.search(r'contact|booking|about|mail',href,re.I) and not href.startswith(('mailto','javascript','#')):
                cands.add(urllib.parse.urljoin(base,href))
        host=urllib.parse.urlparse(base).netloc
        for c in list(cands)[:6]:
            if urllib.parse.urlparse(c).netloc!=host: continue
            hh=fetch(c,15)
            if hh: found|=emails(hh)
            if found: break
    return found
def work(u):
    links=profile_links(u)[:6]; out={}
    for l in links:
        for e in site_emails(l): out.setdefault(e,l)
    return u,links,out
with cf.ThreadPoolExecutor(8) as ex: r2=list(ex.map(work,noem))
json.dump(r2,open('pass2_results.json','w'))
hits=[(u,o) for u,l,o in r2 if o]
print(len(noem),'profiles;',sum(1 for u,l,o in r2 if l),'had external sites;',len(hits),'yielded emails')
for u,o in hits:
    for e,s in o.items(): print(e,'|',u,'|',s)
