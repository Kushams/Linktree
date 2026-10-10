# Batch 2: run the full email pipeline on new Linktree profiles (from DuckDuckGo exports).
# Usage: python3 -I batch2.py profiles.json out.json
import re, json, sys, urllib.request, urllib.parse, concurrent.futures as cf
profiles=json.load(open(sys.argv[1])); out=sys.argv[2]
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en'}
def fetch(u,t=20):
    for _ in range(2):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=HDR),timeout=t).read(2_500_000).decode('utf-8','replace')
        except Exception: pass
    return ''
epat=re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')
bad=re.compile(r'\.(png|jpe?g|gif|webp|svg|css|js|woff2?)$|sentry|wixpress|example|exemple|domain|noreply|no-reply|@2x|@3x|soundcloud|tiktok|youtube|google|bandcamp|facebook|instagram|mixcloud|spotify|apple\.com|cloudflare|schema\.org|u003e|yourname|email@|your@|xxx|linktr\.ee$',re.I)
def emails(h):
    h=urllib.parse.unquote(h.replace('\\u0040','@').replace('\\u002F','/').replace('\\u0026','&').replace('&#64;','@').replace('\\n',' ').replace('\\r',' ').replace('\\"',' '))
    return {m.strip('.').lower() for m in epat.findall(h) if not bad.search(m)}
skip=re.compile(r'(instagram|facebook|fb\.com|tiktok|youtube|youtu\.be|spotify|soundcloud|twitter|x\.com|bandcamp|apple\.com|deezer|beatport|mixcloud|linktr\.ee|ra\.co|residentadvisor|snapchat|twitch|discord|threads\.net|amazon|tidal|shazam|vimeo|patreon|paypal|wa\.me|whatsapp|t\.me|telegram|google\.com|nts\.live|hearthis|traxsource|juno|discogs|rinse\.fm|boilerroom|dice\.fm|wikipedia|pinterest|linkedin|bsky|ticketmaster|eventbrite|shotgun|songkick|bandsintown|ko-fi|buymeacoffee|sjv\.io|linksynergy|bit\.ly|lnk\.to|ffm\.to|smarturl|distrokid|hypeddit|toneden|genius|last\.fm|kick\.com|spoti\.fi|fanlink|song\.link)',re.I)
def lcs(a,b):
    best=0
    for i in range(len(a)):
        for j in range(i+best+1,len(a)+1):
            if a[i:j] in b: best=j-i
            else: break
    return best
norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
def page(u):
    h=fetch(u,30); m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',h,re.S)
    if not m: return h,[]
    pp=json.loads(m.group(1))['props']['pageProps']
    urls=[x.get('url') for x in pp.get('links',[]) if x.get('url')]+[x.get('url') for x in pp.get('socialLinks',[]) if x.get('url')]
    return h,[x for x in dict.fromkeys(urls) if x.startswith('http')]
def pick(urls):
    o=[]
    for x in urls:
        p=urllib.parse.urlparse(x); host=p.netloc.lower().replace('www.',''); s=[q for q in p.path.split('/') if q]
        if host=='soundcloud.com' and len(s)==1: o.append(x)
        elif host=='tiktok.com' and len(s)==1 and s[0].startswith('@'): o.append(x)
        elif host=='youtube.com' and s and (s[0].startswith('@') or s[0] in('c','channel','user')): o.append(x.rstrip('/')+('' if x.rstrip('/').endswith('about') else '/about'))
        elif host.endswith('bandcamp.com') and host!='bandcamp.com' and len(s)<=1: o.append(x)
        elif host=='mixcloud.com' and len(s)==1: o.append(x)
        elif host in('x.com','twitter.com') and len(s)==1: o.append(x)
    return list(dict.fromkeys(o))[:6]
def site(url,h):
    f=emails(h) if h else set()
    if not f and h:
        host=urllib.parse.urlparse(url).netloc
        c={urllib.parse.urljoin(url,p) for p in ['/contact','/booking','/about']}
        for href in re.findall(r'href=["\']([^"\']+)["\']',h):
            if re.search(r'contact|booking|about|mail',href,re.I) and not href.startswith(('mailto','javascript','#')): c.add(urllib.parse.urljoin(url,href))
        for cc in list(c)[:6]:
            if urllib.parse.urlparse(cc).netloc==host:
                f|=emails(fetch(cc,15))
            if f: break
    return f
def work(u):
    h,links=page(u); found={}
    for e in emails(h): found.setdefault(e,('linktree page',u))
    if not found:
        hd=norm(u.rsplit('/',1)[1])
        for l in [x for x in links if not skip.search(x)][:6]:
            stem=norm(urllib.parse.urlparse(l).netloc.lower().replace('www.','').rsplit('.',1)[0])
            if lcs(hd,stem)>=5:
                for e in site(l,fetch(l)): found.setdefault(e,('artist website',l))
        for l in pick(links):
            for e in emails(fetch(l)): found.setdefault(e,('artist page',l))
    return u,found
with cf.ThreadPoolExecutor(5) as ex: res=list(ex.map(work,profiles))
json.dump(res,open(out,'w'))
print(len(res),'profiles;',sum(1 for u,f in res if f),'with emails')
for u,f in res:
    print(u.rsplit('/',1)[1],'|',', '.join(f) if f else '-')
